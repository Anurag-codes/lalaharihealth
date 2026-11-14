from datetime import datetime, timezone as datetime_timezone

from django.conf import settings
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.accounts.services import require_doctor, require_patient
from apps.accounts.views import IsPatient, NoStoreResponseMixin
from apps.consultations.doctor_views import IsVerifiedDoctor, is_verified_doctor
from apps.consultations.models import Consultation
from .doctor_app import join_opens_at
from .hms import AUTH_TOKEN_SECONDS, VideoServiceUnavailable, configured_roles, provision_room, signed_token, validate_template
from .models import Appointment, AppointmentCall, AppointmentVideoRoom


def eligible_appointment(user, appointment_id, participant_role):
    if participant_role == 'doctor':
        require_doctor(user)
        scope = {'doctor': user}
    else:
        require_patient(user)
        scope = {'patient': user}
    appointment = get_object_or_404(
        Appointment.objects.select_for_update(of=('self',)).select_related('consultation', 'doctor', 'patient'),
        pk=appointment_id, **scope,
    )
    if (
        appointment.status != Appointment.Status.CONFIRMED
        or appointment.consultation.mode != Consultation.Mode.VIDEO
        or appointment.consultation.status in (Consultation.Status.DRAFT, Consultation.Status.CANCELLED, Consultation.Status.COMPLETED)
    ):
        raise serializers.ValidationError('Only confirmed, unfinished video appointments can be joined.')
    if (
        not appointment.doctor_id or not is_verified_doctor(appointment.doctor)
        or appointment.consultation.doctor_id != appointment.doctor_id
        or not appointment.patient.is_active
    ):
        raise serializers.ValidationError('The appointment participants are not eligible to join.')
    require_patient(appointment.patient)
    require_doctor(appointment.doctor)
    if timezone.now() < join_opens_at(appointment):
        raise serializers.ValidationError('Joining opens five minutes before the appointment starts.')
    return appointment


def join_appointment(user, appointment_id, participant_role):
    if connection.vendor != 'postgresql' or not connection.features.has_select_for_update:
        raise VideoServiceUnavailable('Video calling requires a database with row-locking support (PostgreSQL).')
    # Persist the opaque provisioning name even if the subsequent provider call fails.
    with transaction.atomic():
        appointment = eligible_appointment(user, appointment_id, participant_role)
        roles = configured_roles()
        reservation, _ = AppointmentVideoRoom.objects.get_or_create(
            appointment=appointment, defaults={'template_id': settings.HMS_TEMPLATE_ID},
        )
    with transaction.atomic():
        appointment = eligible_appointment(user, appointment_id, participant_role)
        reservation = AppointmentVideoRoom.objects.select_for_update().get(pk=reservation.pk)
        validate_template(reservation.template_id, roles)
        room_id = provision_room(reservation)
        if reservation.room_id and room_id != reservation.room_id:
            raise VideoServiceUnavailable('100ms returned a different room. Contact support.')
        eligible_appointment(user, appointment_id, participant_role)
        call = (
            AppointmentCall.objects.select_for_update().get(pk=reservation.current_call_id)
            if reservation.current_call_id else None
        )
        if call is None or call.status in AppointmentCall.TERMINAL_STATUSES:
            call = AppointmentCall.objects.create(
                appointment=appointment, provider='100ms', external_call_id=room_id,
                mode=Consultation.Mode.VIDEO, created_by=user,
            )
        reservation.room_id, reservation.current_call = room_id, call
        reservation.save(update_fields=['room_id', 'current_call'])
        token, expires_at = signed_token(
            'app', AUTH_TOKEN_SECONDS, room_id=room_id, role=roles[participant_role], user_id=f'user-{user.pk}',
        )
    return {
        'provider': '100ms', 'appointment_id': appointment.pk, 'room_id': room_id,
        'role': roles[participant_role], 'user_id': f'user-{user.pk}', 'auth_token': token,
        'expires_in': AUTH_TOKEN_SECONDS, 'expires_at': datetime.fromtimestamp(expires_at, tz=datetime_timezone.utc),
        'call_id': call.pk, 'mode': 'video',
    }


class VideoJoinRequestSerializer(serializers.Serializer):
    def validate(self, attrs):
        if self.initial_data:
            raise serializers.ValidationError('Send an empty JSON object. Role, room and user identity are assigned by the server.')
        return attrs


class VideoJoinResponseSerializer(serializers.Serializer):
    provider = serializers.CharField()
    appointment_id = serializers.IntegerField()
    room_id = serializers.CharField()
    role = serializers.CharField()
    user_id = serializers.CharField()
    auth_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    expires_at = serializers.DateTimeField()
    call_id = serializers.IntegerField()
    mode = serializers.CharField()


JOIN_EXAMPLE = {
    'provider': '100ms', 'appointment_id': 18, 'room_id': 'room_example', 'role': 'doctor',
    'user_id': 'user-7', 'auth_token': '<short-lived-100ms-app-token>', 'expires_in': 300,
    'expires_at': '2026-11-14T23:35:00+05:30', 'call_id': 5, 'mode': 'video',
}
JOIN_DESCRIPTION = (
    'POST {} with your backend access JWT. Only the assigned active patient and verified doctor can join a confirmed, '
    'unfinished video appointment, from five minutes before its start until completion/cancellation. '
    'The server creates/reuses one private 100ms room under database row locks and assigns your role and user identity. '
    'The SDK auth token expires after 300 seconds; request a fresh token for joining again. Token expiry does not end '
    'an already connected SDK session. No management credentials are returned. A room/code/name is not authorization. '
    'Save call_id; the doctor PATCHes the existing call-details endpoint only after actual SDK connection/end events. '
    'Token issuance creates an unknown call placeholder, never an in_progress call. Both participants and reconnects reuse '
    'that placeholder; joining after a terminal call outcome creates a new attempt in the same room. '
    'No recording or transcription is requested. 503 means missing/unsafe configuration, unsupported database or provider '
    'failure; retry the same endpoint with backoff. Do not log or share auth_token.'
)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class VideoJoinView(NoStoreResponseMixin, generics.GenericAPIView):
    serializer_class = VideoJoinRequestSerializer

    def post(self, request, appointment_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = join_appointment(request.user, appointment_id, self.participant_role)
        return Response(VideoJoinResponseSerializer(result).data)


@extend_schema(
    tags=['Doctor app: appointments'], summary='Join your appointment with 100ms video',
    description=JOIN_DESCRIPTION, responses={200: VideoJoinResponseSerializer},
    examples=[
        OpenApiExample('Join', value={}, request_only=True),
        OpenApiExample('Doctor join', value=JOIN_EXAMPLE, response_only=True),
    ],
)
class DoctorVideoJoinView(VideoJoinView):
    permission_classes = [IsVerifiedDoctor]
    participant_role = 'doctor'


@extend_schema(
    tags=['Appointment booking'], summary='Join your appointment with 100ms video',
    description=JOIN_DESCRIPTION, responses={200: VideoJoinResponseSerializer},
    examples=[
        OpenApiExample('Join', value={}, request_only=True),
        OpenApiExample('Patient join', value={**JOIN_EXAMPLE, 'role': 'patient', 'user_id': 'user-8'}, response_only=True),
    ],
)
class PatientVideoJoinView(VideoJoinView):
    permission_classes = [IsPatient]
    participant_role = 'patient'
