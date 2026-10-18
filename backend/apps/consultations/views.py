from django.http import FileResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Consultation, ConsultationDocument
from .serializers import (
	CasePreviewSerializer, ConsultationSerializer, DocumentSerializer, DocumentUploadSerializer,
	HistorySerializer, PatientDetailsSerializer, relation_label, remember_self_details,
)

STEP1_EXAMPLES = [
	OpenApiExample(
		'Logged-out flow: Patient Details form', request_only=True,
		description='Name, age, gender and phone typed on the Patient Details screen (sent after OTP login).',
		value={'patient_name': 'Rahul Sharma', 'patient_age': 25, 'patient_gender': 'male', 'patient_phone': '+919876543210', 'mode': 'video'},
	),
	OpenApiExample(
		'Select Patient: Myself', request_only=True,
		description='Details come from your profile / previous booking. A 400 listing missing fields means show the Patient Details form.',
		value={'family_member_id': None, 'mode': 'video'},
	),
	OpenApiExample('Select Patient: family member', request_only=True, value={'family_member_id': 3, 'mode': 'video'}),
	OpenApiExample(
		'Book Appointment from the USA', request_only=True,
		description='country_code from GET /api/v1/pricing/. Checkout then charges USD at the US general physician fee.',
		value={'family_member_id': None, 'country_code': 'US', 'mode': 'video'},
	),
	OpenApiExample(
		'Book Specialist: Myself with Dermatology', request_only=True,
		description='speciality id from GET /api/v1/doctors/specialities/. The fee and slots then follow that speciality.',
		value={'family_member_id': None, 'speciality': 2, 'mode': 'video'},
	),
]
HISTORY_EXAMPLES = [
	OpenApiExample(
		'Symptoms with headache type and variant', request_only=True,
		value={
			'condition': 1, 'condition_type': 3, 'condition_variant': 6,
			'condition_details': 'Pain behind the right eye, mostly at night',
			'symptoms': 'Severe one-sided headache', 'duration_value': 5, 'duration_unit': 'days',
			'ongoing_medication': True, 'treatment_details': 'Paracetamol 500mg when needed',
		},
	),
	OpenApiExample(
		'Disease without types', request_only=True,
		value={'condition': 5, 'duration_value': 2, 'duration_unit': 'weeks', 'ongoing_medication': False},
	),
]
CASE_PREVIEW_EXAMPLE = {
	'consultation_id': 42, 'consultation_title': 'General Consultation', 'speciality': None,
	'patient': {
		'name': 'Rahul Sharma', 'age': 25, 'gender': 'male', 'gender_label': 'Male', 'phone': '+919876543210',
		'relation': 'self', 'relation_label': 'You',
	},
	'chief_complaint': 'Headache - Cluster Headache - Chronic',
	'condition_details': 'Pain behind the right eye, mostly at night',
	'symptoms': 'Severe one-sided headache', 'duration_display': '5 Days', 'ongoing_medication': True,
	'treatment_details': 'Paracetamol 500mg when needed', 'mode': 'video',
	'schedule': {
		'slot_id': 318, 'starts_at': '2026-10-18T19:00:00+05:30', 'date_display': '18 Oct 2026',
		'time_display': '07:00 PM', 'is_available': True,
	},
	'documents': [{
		'id': 9, 'original_name': 'blood_report.pdf', 'download_url': 'http://127.0.0.1:8000/api/v1/consultations/42/documents/9/download/',
		'uploaded_at': '2026-10-16T18:05:00+05:30',
	}],
	'document_count': 1, 'fee': 200, 'currency': 'INR', 'ready_to_submit': True, 'missing_steps': [],
}


def owned_consultation(request, consultation_id, editable=False):
	queryset = Consultation.objects.select_for_update() if editable else Consultation.objects.all()
	consultation = get_object_or_404(queryset, pk=consultation_id, patient=request.user)
	if editable and consultation.status != Consultation.Status.DRAFT:
		raise serializers.ValidationError('Booked consultations cannot be edited.')
	return consultation


class ConsultationListCreateView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PatientDetailsSerializer

	@extend_schema(
		tags=['Mobile intake'], summary='Step 1: Select Patient / Patient Details - create a draft',
		description=(
			'Logged-out users fill Patient Details, log in with phone OTP (`/api/v1/auth/patient/phone/firebase/`), then call this. '
			'Logged-in users pick from `GET /api/v1/patients/booking-patients/` and send only `family_member_id` (null = Myself).'
		),
		responses={201: ConsultationSerializer}, examples=STEP1_EXAMPLES,
	)
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		with transaction.atomic():
			consultation = serializer.save(patient=request.user)
			remember_self_details(request.user, consultation)
		return Response(ConsultationSerializer(consultation, context={'request': request}).data, status=201)

	@extend_schema(tags=['Mobile intake'], summary='List your consultation drafts and bookings', responses=ConsultationSerializer(many=True))
	def get(self, request):
		queryset = Consultation.objects.filter(patient=request.user).order_by('-created_at')
		page = self.paginate_queryset(queryset)
		return self.get_paginated_response(ConsultationSerializer(page, many=True, context={'request': request}).data)


class ConsultationDetailView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PatientDetailsSerializer

	@extend_schema(tags=['Mobile intake'], responses=ConsultationSerializer)
	def get(self, request, consultation_id):
		consultation = owned_consultation(request, consultation_id)
		return Response(ConsultationSerializer(consultation, context={'request': request}).data)

	@extend_schema(tags=['Mobile intake'], summary='Update patient details before booking', responses=ConsultationSerializer)
	@transaction.atomic
	def patch(self, request, consultation_id):
		consultation = owned_consultation(request, consultation_id, editable=True)
		serializer = self.get_serializer(consultation, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(ConsultationSerializer(consultation, context={'request': request}).data)


class ConsultationHistoryView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = HistorySerializer

	@extend_schema(
		tags=['Mobile intake'], summary='Step 2: Symptoms - disease, type, variant, duration and medication',
		description='Use ids from `GET /api/v1/consultations/conditions/`. Type and variant are required when the chosen item has children.',
		responses=ConsultationSerializer, examples=HISTORY_EXAMPLES,
	)
	@transaction.atomic
	def put(self, request, consultation_id):
		consultation = owned_consultation(request, consultation_id, editable=True)
		serializer = self.get_serializer(consultation, data=request.data)
		serializer.is_valid(raise_exception=True)
		serializer.save(history_completed=True)
		return Response(ConsultationSerializer(consultation, context={'request': request}).data)


class ConsultationDocumentsView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = DocumentUploadSerializer
	parser_classes = [MultiPartParser]

	@extend_schema(tags=['Mobile documents'], summary='Step 3: optional upload, one PDF/PNG/JPG up to 10 MB per request', responses={201: DocumentSerializer})
	@transaction.atomic
	def post(self, request, consultation_id):
		consultation = owned_consultation(request, consultation_id, editable=True)
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		uploaded_file = serializer.validated_data['file']
		document = ConsultationDocument.objects.create(
			consultation=consultation, file=uploaded_file, original_name=uploaded_file.name,
		)
		return Response(DocumentSerializer(document, context={'request': request}).data, status=201)

	@extend_schema(tags=['Mobile documents'], responses=DocumentSerializer(many=True))
	def get(self, request, consultation_id):
		consultation = owned_consultation(request, consultation_id)
		return Response(DocumentSerializer(consultation.documents.all(), many=True, context={'request': request}).data)


class ConsultationDocumentDetailView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = DocumentSerializer

	@extend_schema(tags=['Mobile documents'], responses={204: None})
	@transaction.atomic
	def delete(self, request, consultation_id, document_id):
		consultation = owned_consultation(request, consultation_id, editable=True)
		document = get_object_or_404(ConsultationDocument, consultation=consultation, pk=document_id)
		document.file.delete(save=False)
		document.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class ConsultationDocumentDownloadView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = DocumentSerializer

	@extend_schema(tags=['Mobile documents'], summary='Download a private document with Bearer authentication', responses={(200, 'application/octet-stream'): OpenApiTypes.BINARY})
	def get(self, request, consultation_id, document_id):
		from .doctor_views import doctor_consultations, is_verified_doctor

		if is_verified_doctor(request.user):
			consultation = get_object_or_404(doctor_consultations(request.user), pk=consultation_id)
		else:
			consultation = owned_consultation(request, consultation_id)
		document = get_object_or_404(ConsultationDocument, consultation=consultation, pk=document_id)
		return FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_name)


class CasePreviewView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = CasePreviewSerializer

	@extend_schema(
		tags=['Mobile scheduling'], summary='Case Preview: everything entered, before "Submit Case"',
		description=(
			'Open after "Request Appointment" with the chosen `slot_id`. Nothing is reserved yet. '
			'`ready_to_submit` is false with `missing_steps` (patient_details, history, schedule) when something is incomplete '
			'or the time was taken. Submit with `POST /api/v1/appointments/` and `information_confirmed: true`.'
		),
		parameters=[OpenApiParameter('slot_id', int, description='Slot chosen on Schedule Appointment')],
		examples=[OpenApiExample('Case preview', response_only=True, value=CASE_PREVIEW_EXAMPLE)],
	)
	def get(self, request, consultation_id):
		from django.utils import timezone

		from apps.appointments.availability import display_date, display_time, free_slots_for_date
		from apps.appointments.models import AppointmentSlot

		consultation = owned_consultation(request, consultation_id)
		appointment = getattr(consultation, 'appointment', None)
		schedule = None
		slot_id = request.query_params.get('slot_id')
		if appointment is not None:
			schedule = {'slot_id': appointment.slot_id, 'starts_at': appointment.slot_time, 'is_available': True}
		elif slot_id:
			if not str(slot_id).isdigit():
				raise serializers.ValidationError({'slot_id': 'A valid integer is required.'})
			slot = get_object_or_404(AppointmentSlot, pk=int(slot_id))
			free = free_slots_for_date(timezone.localtime(slot.starts_at).date(), consultation.speciality_id)
			available = slot.is_active and any(item['starts_at'] == slot.starts_at for item in free)
			schedule = {'slot_id': slot.pk, 'starts_at': slot.starts_at, 'is_available': available}
		if schedule:
			schedule['date_display'] = display_date(schedule['starts_at'])
			schedule['time_display'] = display_time(schedule['starts_at'])
		missing = []
		if not all([consultation.patient_name, consultation.patient_age is not None, consultation.patient_gender, consultation.patient_phone]):
			missing.append('patient_details')
		if not consultation.history_completed:
			missing.append('history')
		if not schedule or not schedule['is_available']:
			missing.append('schedule')
		documents = list(consultation.documents.all())
		duration = ''
		if consultation.duration_value:
			duration = f'{consultation.duration_value} {consultation.get_duration_unit_display()}'
		data = {
			'consultation_id': consultation.pk, 'consultation_title': consultation.title,
			'speciality': consultation.speciality.name if consultation.speciality_id else None,
			'patient': {
				'name': consultation.patient_name, 'age': consultation.patient_age, 'gender': consultation.patient_gender,
				'gender_label': consultation.get_patient_gender_display() if consultation.patient_gender else '',
				'phone': consultation.patient_phone, 'relation': consultation.patient_relation,
				'relation_label': relation_label(consultation.patient_relation),
			},
			'chief_complaint': consultation.chief_complaint or consultation.title,
			'condition_details': consultation.condition_details, 'symptoms': consultation.symptoms,
			'duration_display': duration, 'ongoing_medication': consultation.ongoing_medication,
			'treatment_details': consultation.treatment_details, 'mode': consultation.mode,
			'schedule': schedule,
			'documents': DocumentSerializer(documents, many=True, context={'request': request}).data,
			'document_count': len(documents),
			'fee': consultation.fee_charged if appointment is not None else consultation.expected_fee,
			'currency': consultation.currency if appointment is not None else consultation.expected_currency,
			'ready_to_submit': appointment is None and consultation.status == Consultation.Status.DRAFT and not missing,
			'missing_steps': missing,
		}
		return Response(self.get_serializer(data).data)
