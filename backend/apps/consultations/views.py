from django.http import FileResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Consultation, ConsultationDocument
from .serializers import (
	ConsultationSerializer, DocumentSerializer, DocumentUploadSerializer,
	HistorySerializer, PatientDetailsSerializer,
)


def owned_consultation(request, consultation_id, editable=False):
	queryset = Consultation.objects.select_for_update() if editable else Consultation.objects.all()
	consultation = get_object_or_404(queryset, pk=consultation_id, patient=request.user)
	if editable and consultation.status != Consultation.Status.DRAFT:
		raise serializers.ValidationError('Booked consultations cannot be edited.')
	return consultation


class ConsultationListCreateView(generics.GenericAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = PatientDetailsSerializer

	@extend_schema(tags=['Mobile intake'], summary='Step 1: save patient details and create a draft', responses={201: ConsultationSerializer})
	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		consultation = serializer.save(patient=request.user)
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

	@extend_schema(tags=['Mobile intake'], summary='Step 2: save condition, duration and medication history', responses=ConsultationSerializer)
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
		consultation = owned_consultation(request, consultation_id)
		document = get_object_or_404(ConsultationDocument, consultation=consultation, pk=document_id)
		return FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_name)
