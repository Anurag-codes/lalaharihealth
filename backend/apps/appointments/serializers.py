from django.utils import timezone
from rest_framework import serializers

from .availability import BOOKING_WINDOW_DAYS, DAY_START, LAST_SLOT_START, SLOT_MINUTES, display_date, display_time
from .models import Appointment, AppointmentSlot


class SlotQuerySerializer(serializers.Serializer):
    date = serializers.DateField(help_text='Local India date, YYYY-MM-DD')


SPECIALITY_QUERY_HELP = 'Speciality of the booking (Book Specialist). Omit for a general physician.'


class PatientSlotQuerySerializer(SlotQuerySerializer):
    speciality_id = serializers.IntegerField(min_value=1, required=False, help_text=SPECIALITY_QUERY_HELP)


class SlotDatesQuerySerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=BOOKING_WINDOW_DAYS, default=7, required=False)
    speciality_id = serializers.IntegerField(min_value=1, required=False, help_text=SPECIALITY_QUERY_HELP)


class AppointmentSlotSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='Send this as slot_id when submitting the case')
    starts_at = serializers.DateTimeField()
    time_display = serializers.SerializerMethodField(help_text='e.g. 07:00 PM')
    remaining_capacity = serializers.IntegerField(help_text='Number of doctors still free at this time')

    def get_time_display(self, obj) -> str:
        return display_time(obj['starts_at'])


class SlotDateSerializer(serializers.Serializer):
    date = serializers.DateField()
    day_label = serializers.CharField(help_text='"Today" or a short weekday such as "Mon"')
    day_number = serializers.IntegerField()
    available_slot_count = serializers.IntegerField()


class AppointmentRequestSerializer(serializers.Serializer):
    consultation_id = serializers.IntegerField(min_value=1)
    slot_id = serializers.IntegerField(min_value=1)
    information_confirmed = serializers.BooleanField(
        help_text='The "I confirm the information provided above is correct." tick on Case Preview. Must be true.',
    )

    def validate_information_confirmed(self, value):
        if not value:
            raise serializers.ValidationError('Please confirm the information is correct.')
        return value


class DoctorAssignmentSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField(min_value=1)


class AppointmentSerializer(serializers.ModelSerializer):
    appointment_number = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='consultation.fee_charged', read_only=True, help_text='Whole currency units')
    currency = serializers.CharField(source='consultation.currency', read_only=True)
    payment_status = serializers.SerializerMethodField()
    schedule_date = serializers.SerializerMethodField(help_text='YYYY-MM-DD in India time')
    schedule_time = serializers.SerializerMethodField(help_text='e.g. 10:00 AM')
    patient_name = serializers.CharField(source='consultation.patient_name', read_only=True)
    chief_complaint = serializers.SerializerMethodField()
    consultation_title = serializers.CharField(
        source='consultation.title', read_only=True, help_text='"General Consultation" or the speciality title, e.g. "Skin Consultation"',
    )
    speciality = serializers.SerializerMethodField()
    mode_label = serializers.SerializerMethodField(help_text='Always "Online"')
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    doctor_name = serializers.SerializerMethodField()
    doctor_specialization = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_number', 'consultation', 'slot', 'slot_time', 'schedule_date', 'schedule_time',
            'status', 'status_label', 'patient_name', 'consultation_title', 'speciality', 'chief_complaint', 'mode_label',
            'doctor', 'doctor_name', 'doctor_specialization',
            'amount', 'currency', 'payment_status', 'created_at',
        ]
        read_only_fields = fields

    def get_appointment_number(self, obj) -> str:
        return f'APT-{obj.pk:05d}'

    def get_payment_status(self, obj) -> str:
        payment = getattr(obj.consultation, 'payment', None)
        return payment.status if payment else 'not_started'

    def get_schedule_date(self, obj) -> str:
        return timezone.localtime(obj.slot_time).date().isoformat()

    def get_schedule_time(self, obj) -> str:
        return display_time(obj.slot_time)

    def get_chief_complaint(self, obj) -> str:
        return obj.consultation.chief_complaint or obj.consultation.title

    def get_speciality(self, obj) -> str | None:
        speciality = obj.consultation.speciality
        return speciality.name if speciality else None

    def get_mode_label(self, obj) -> str:
        return 'Online'

    def _confirmed_doctor(self, obj):
        if obj.status in {Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED}:
            return obj.doctor
        return None

    def get_doctor_name(self, obj) -> str | None:
        doctor = self._confirmed_doctor(obj)
        return f'Dr. {doctor.get_full_name() or doctor.username}' if doctor else None

    def get_doctor_specialization(self, obj) -> str | None:
        doctor = self._confirmed_doctor(obj)
        profile = getattr(doctor, 'doctor_profile', None) if doctor else None
        return profile.specialization if profile else None


class DoctorSlotSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    time_display = serializers.SerializerMethodField()
    is_booked = serializers.SerializerMethodField()
    appointment_id = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = ['id', 'starts_at', 'date', 'time_display', 'is_active', 'is_booked', 'appointment_id']
        read_only_fields = fields

    def _appointment(self, obj):
        return next((item for item in obj.appointments.all() if item.status != Appointment.Status.CANCELLED), None)

    def get_date(self, obj) -> str:
        return timezone.localtime(obj.starts_at).date().isoformat()

    def get_time_display(self, obj) -> str:
        return display_time(obj.starts_at)

    def get_is_booked(self, obj) -> bool:
        return self._appointment(obj) is not None

    def get_appointment_id(self, obj) -> int | None:
        appointment = self._appointment(obj)
        return appointment.pk if appointment else None


class DoctorAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField(help_text='India date, YYYY-MM-DD; today or within the next 30 days')
    start_time = serializers.TimeField(
        format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'],
        help_text='First slot shown to patients, HH:MM in 15-minute steps, from 08:00',
    )
    end_time = serializers.TimeField(
        format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'], required=False, allow_null=True, default=None,
        help_text='Optional. When availability ends (last slot starts 15 minutes earlier). Default: the day ends at 23:59.',
    )

    def validate(self, attrs):
        today = timezone.localdate()
        day, start, end = attrs['date'], attrs['start_time'], attrs['end_time']
        if day < today or (day - today).days > BOOKING_WINDOW_DAYS:
            raise serializers.ValidationError({'date': f'Choose today or a date within the next {BOOKING_WINDOW_DAYS} days.'})
        if start.minute % SLOT_MINUTES or start.second or start < DAY_START or start > LAST_SLOT_START:
            raise serializers.ValidationError({'start_time': 'Use a 15-minute time between 08:00 and 23:45.'})
        if end is not None:
            if end.minute % SLOT_MINUTES or end.second:
                raise serializers.ValidationError({'end_time': 'Use a 15-minute time, e.g. 21:00.'})
            if end <= start:
                raise serializers.ValidationError({'end_time': 'End time must be after the start time.'})
        return attrs


class DoctorAvailabilityResultSerializer(serializers.Serializer):
    created_count = serializers.IntegerField()
    slots = DoctorSlotSerializer(many=True)
