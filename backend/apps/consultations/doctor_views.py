from pathlib import Path

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.views import NoStoreResponseMixin
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from .models import Consultation, PrescriptionDocument, PrescriptionItem
from .serializers import (
    MAX_PRESCRIPTION_FILES, MAX_PRESCRIPTION_FILES_PER_REQUEST, ConsultationRecordWriteSerializer,
    DoctorConsultationSerializer, PrescriptionDocumentSerializer, PrescriptionUploadSerializer,
)

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
PRESCRIPTION_DOCUMENT_EXAMPLE = {
    'id': 3, 'original_name': 'prescription.jpg', 'uploaded_at': '2026-02-12T11:04:00+05:30',
    'download_url': 'https://api.lalaharihealth.com/api/v1/consultations/41/prescription-documents/3/download/',
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
    'prescription_documents': [PRESCRIPTION_DOCUMENT_EXAMPLE],
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
        .prefetch_related('prescription_items', 'prescription_documents', 'documents')
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
            'Every field is optional; a doctor may instead upload handwritten prescription photos with '
            'POST .../record/documents/ (those photos are not changed by this call). '
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
            from apps.appointments.completion import complete_appointment

            appointment.consultation = consultation
            complete_appointment(appointment)

        consultation.prescription_items.all().delete()
        PrescriptionItem.objects.bulk_create([
            PrescriptionItem(consultation=consultation, display_order=index, **item)
            for index, item in enumerate(data['prescriptions'])
        ])
        consultation = self.consultation(consultation_id)
        return Response(DoctorConsultationSerializer(consultation, context={'request': request}).data)


def writable_record(user, consultation_id):
    """Lock the assigned doctor's consultation and check that its record may change."""
    consultation = get_object_or_404(
        doctor_consultations(user).select_for_update(of=('self',)).prefetch_related(None), pk=consultation_id,
    )
    appointment = Appointment.objects.select_for_update().get(consultation=consultation)
    if consultation.status == Consultation.Status.CANCELLED or appointment.status not in RECORD_WRITABLE_APPOINTMENT_STATUSES:
        raise serializers.ValidationError({'detail': 'Records can be written only for confirmed or completed appointments.'})
    return consultation


def prescription_document_list(request, consultation):
    documents = PrescriptionDocument.objects.filter(consultation=consultation)
    return PrescriptionDocumentSerializer(documents, many=True, context={'request': request}).data


class DoctorPrescriptionDocumentsView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = PrescriptionUploadSerializer
    parser_classes = [MultiPartParser]
    pagination_class = None

    @extend_schema(
        tags=['Doctor consultation records'], summary='List uploaded prescription photos',
        responses=PrescriptionDocumentSerializer(many=True),
        examples=[OpenApiExample('Prescription photos', value=[PRESCRIPTION_DOCUMENT_EXAMPLE], response_only=True)],
    )
    def get(self, request, consultation_id):
        consultation = get_object_or_404(doctor_consultations(request.user), pk=consultation_id)
        return Response(prescription_document_list(request, consultation))

    @extend_schema(
        tags=['Doctor consultation records'], summary='Upload handwritten prescription photos',
        description=(
            'Optional alternative to typing the record. multipart/form-data: repeat the field `files` for each page '
            f'(JPG/PNG/PDF, up to 10 MB each, {MAX_PRESCRIPTION_FILES_PER_REQUEST} per request, '
            f'{MAX_PRESCRIPTION_FILES} per consultation). Allowed once the appointment is confirmed, also after '
            'completion for corrections. The patient sees the photos in the medical record after the consultation is completed. '
            'Returns all prescription photos of the consultation.'
        ),
        request={'multipart/form-data': PrescriptionUploadSerializer},
        responses={201: PrescriptionDocumentSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Two pages', request_only=True, media_type='multipart/form-data',
                value={'files': ['page-1.jpg', 'page-2.jpg']},
            ),
            OpenApiExample('Uploaded', value=[PRESCRIPTION_DOCUMENT_EXAMPLE], response_only=True, status_codes=['201']),
        ],
    )
    @transaction.atomic
    def post(self, request, consultation_id):
        consultation = writable_record(request.user, consultation_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = serializer.validated_data['files']
        if PrescriptionDocument.objects.filter(consultation=consultation).count() + len(files) > MAX_PRESCRIPTION_FILES:
            raise serializers.ValidationError(
                {'files': [f'A consultation can have at most {MAX_PRESCRIPTION_FILES} prescription files.']},
            )
        for uploaded in files:
            PrescriptionDocument.objects.create(
                consultation=consultation, uploaded_by=request.user, file=uploaded,
                original_name=Path(uploaded.name).name[:255],
            )
        consultation.record_updated_at = timezone.now()
        consultation.save(update_fields=['record_updated_at'])
        return Response(prescription_document_list(request, consultation), status=status.HTTP_201_CREATED)


class DoctorPrescriptionDocumentDetailView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = PrescriptionDocumentSerializer

    @extend_schema(
        tags=['Doctor consultation records'], summary='Delete an uploaded prescription photo', responses={204: None},
    )
    @transaction.atomic
    def delete(self, request, consultation_id, document_id):
        consultation = writable_record(request.user, consultation_id)
        document = get_object_or_404(PrescriptionDocument, consultation=consultation, pk=document_id)
        stored_file = document.file
        document.delete()
        transaction.on_commit(lambda: stored_file.delete(save=False))
        consultation.record_updated_at = timezone.now()
        consultation.save(update_fields=['record_updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
