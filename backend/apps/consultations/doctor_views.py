from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.views import NoStoreResponseMixin
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from .models import Consultation, PrescriptionItem
from .serializers import ConsultationRecordWriteSerializer, DoctorConsultationSerializer

RECORD_WRITABLE_APPOINTMENT_STATUSES = {Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED}

RECORD_REQUEST_EXAMPLE = {
    'diagnosis': 'Acute pharyngitis',
    'prescriptions': [
        {
            'medicine_name': 'Azithromycin 500mg', 'dosage': '1 tablet', 'timings': ['morning'],
            'food_relation': 'after_food', 'duration_days': 5, 'instructions': '',
        },
        {
            'medicine_name': 'Cough syrup', 'dosage': '10 ml', 'timings': ['morning', 'night'],
            'food_relation': 'after_food', 'duration_days': 7, 'instructions': 'Shake well before use',
        },
    ],
    'doctor_notes': 'Drink warm fluids and take rest.',
    'follow_up_date': '2026-02-19',
    'follow_up_notes': 'Follow up after 1 week if symptoms persist.',
    'mark_completed': True,
}
DOCTOR_CONSULTATION_EXAMPLE = {
    'id': 41, 'appointment_id': 18, 'scheduled_at': '2026-02-12T10:30:00+05:30', 'status': 'completed',
    'appointment_status': 'completed',
    'doctor': {'id': 7, 'name': 'Dr. Ananya Sharma', 'specialization': 'General Physician'},
    'patient': {
        'name': 'Rahul Sharma', 'age': 35, 'gender': 'male', 'relation': 'self', 'relation_label': 'You',
        'is_self': True, 'family_member_id': None,
    },
    'mode': 'video', 'mode_display': 'Video', 'mode_label': 'Online', 'has_clinical_record': True,
    'condition_name': 'Throat infection', 'chief_complaint': 'Throat infection',
    'condition_details': 'Fever and sore throat', 'symptoms': 'Fever and sore throat', 'duration_value': 3,
    'duration_unit': 'days', 'ongoing_medication': False, 'treatment_details': '',
    'diagnosis': 'Acute pharyngitis',
    'prescriptions': [{
        'id': 1, 'medicine_name': 'Azithromycin 500mg', 'dosage': '1 tablet', 'timings': ['morning'],
        'timing_labels': ['Morning'], 'food_relation': 'after_food', 'food_relation_label': 'After food',
        'duration_days': 5, 'instructions': '',
    }],
    'doctor_notes': 'Drink warm fluids and take rest.', 'follow_up_date': '2026-02-19',
    'follow_up_notes': 'Follow up after 1 week if symptoms persist.',
    'record_updated_at': '2026-02-12T11:05:00+05:30', 'documents': [],
}


def is_verified_doctor(user):
    if not user.is_authenticated or not user.is_active or user.role != 'doctor':
        return False
    return DoctorProfile.objects.filter(
        user=user, is_active=True, verification_status=DoctorProfile.VerificationStatus.VERIFIED,
    ).exists()


class IsVerifiedDoctor(BasePermission):
    message = 'A verified, active doctor account is required.'

    def has_permission(self, request, view):
        return is_verified_doctor(request.user)


def doctor_consultations(user):
    return (
        Consultation.objects.filter(doctor=user, appointment__doctor=user)
        .exclude(status=Consultation.Status.DRAFT)
        .select_related('appointment', 'condition', 'doctor__doctor_profile')
        .prefetch_related('prescription_items', 'documents')
        .order_by('-appointment__slot_time')
    )


class DoctorConsultationListView(NoStoreResponseMixin, generics.ListAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = DoctorConsultationSerializer

    def get_queryset(self):
        queryset = doctor_consultations(self.request.user)
        cancelled = Q(status=Consultation.Status.CANCELLED) | Q(appointment__status=Appointment.Status.CANCELLED)
        completed = Q(status=Consultation.Status.COMPLETED) | Q(appointment__status=Appointment.Status.COMPLETED)
        wanted = self.request.query_params.get('status')
        if wanted == 'cancelled':
            queryset = queryset.filter(cancelled)
        elif wanted == 'completed':
            queryset = queryset.filter(completed).exclude(cancelled)
        elif wanted == 'upcoming':
            queryset = queryset.exclude(cancelled).exclude(completed)
        return queryset

    @extend_schema(
        tags=['Doctor consultation records'], summary='List consultations assigned to you',
        description='For verified doctors. Sign in with POST /api/v1/auth/token/ using the doctor account.',
        parameters=[OpenApiParameter('status', str, enum=['upcoming', 'completed', 'cancelled'], required=False)],
        examples=[OpenApiExample('Assigned consultations', response_only=True, value={
            'count': 1, 'next': None, 'previous': None, 'results': [DOCTOR_CONSULTATION_EXAMPLE],
        })],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DoctorConsultationRecordView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = ConsultationRecordWriteSerializer

    def consultation(self, consultation_id, lock=False):
        queryset = doctor_consultations(self.request.user)
        if lock:
            queryset = queryset.select_for_update(of=('self',))
        return get_object_or_404(queryset, pk=consultation_id)

    @extend_schema(
        tags=['Doctor consultation records'], summary='View the patient intake and current record',
        responses=DoctorConsultationSerializer,
        examples=[OpenApiExample('Consultation', value=DOCTOR_CONSULTATION_EXAMPLE, response_only=True)],
    )
    def get(self, request, consultation_id):
        consultation = self.consultation(consultation_id)
        return Response(DoctorConsultationSerializer(consultation, context={'request': request}).data)

    @extend_schema(
        tags=['Doctor consultation records'], summary='Write diagnosis, prescription, notes and follow-up',
        description=(
            'Replaces the whole record: the prescriptions list sent here replaces all previous items. '
            'Allowed for the assigned doctor once the appointment is confirmed. '
            'mark_completed=true completes the consultation and appointment and publishes the record to the patient app. '
            'A completed record can still be corrected; it cannot be reopened.'
        ),
        responses=DoctorConsultationSerializer,
        examples=[
            OpenApiExample('Complete with prescription', value=RECORD_REQUEST_EXAMPLE, request_only=True),
            OpenApiExample('Save draft without completing', request_only=True, value={
                'diagnosis': 'Suspected viral fever', 'prescriptions': [], 'doctor_notes': 'Awaiting blood report.',
                'follow_up_date': None, 'follow_up_notes': '', 'mark_completed': False,
            }),
            OpenApiExample('Saved record', value=DOCTOR_CONSULTATION_EXAMPLE, response_only=True),
        ],
    )
    @transaction.atomic
    def put(self, request, consultation_id):
        consultation = self.consultation(consultation_id, lock=True)
        appointment = Appointment.objects.select_for_update().get(consultation=consultation)
        if consultation.status == Consultation.Status.CANCELLED or appointment.status not in RECORD_WRITABLE_APPOINTMENT_STATUSES:
            raise serializers.ValidationError({'detail': 'Records can be written only for confirmed or completed appointments.'})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        consultation.diagnosis = data['diagnosis']
        consultation.doctor_notes = data['doctor_notes']
        consultation.follow_up_date = data['follow_up_date']
        consultation.follow_up_notes = data['follow_up_notes']
        consultation.record_updated_at = timezone.now()
        if data['mark_completed']:
            consultation.status = Consultation.Status.COMPLETED
        consultation.save(update_fields=[
            'diagnosis', 'doctor_notes', 'follow_up_date', 'follow_up_notes', 'record_updated_at', 'status',
        ])
        if data['mark_completed'] and appointment.status != Appointment.Status.COMPLETED:
            from apps.notifications.models import Notification
            from apps.notifications.service import notify_appointment

            appointment.save(update_fields=appointment.set_status(Appointment.Status.COMPLETED))
            notify_appointment(appointment, Notification.Kind.CONSULTATION_COMPLETED)

        consultation.prescription_items.all().delete()
        PrescriptionItem.objects.bulk_create([
            PrescriptionItem(consultation=consultation, display_order=index, **item)
            for index, item in enumerate(data['prescriptions'])
        ])
        consultation = self.consultation(consultation_id)
        return Response(DoctorConsultationSerializer(consultation, context={'request': request}).data)
