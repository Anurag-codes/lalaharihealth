from decimal import Decimal

from django.db import transaction
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.response import Response

from apps.accounts.views import IsPatient, NoStoreResponseMixin
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from apps.patients.access import accessible_consultations
from .models import Consultation, ConsultationReview


class ReviewWriteSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5, help_text='1 to 5 stars')
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=1000, default='', help_text='Optional, up to 1000 characters')

    def validate(self, attrs):
        unsupported = set(self.initial_data) - set(self.fields)
        if unsupported:
            raise serializers.ValidationError({field: 'Unknown field.' for field in sorted(unsupported)})
        return attrs


class ReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField()
    feedback = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ReviewStatusSerializer(serializers.Serializer):
    consultation_id = serializers.IntegerField()
    can_review = serializers.BooleanField(help_text='true: show the rating form (create, or edit your own rating)')
    reason = serializers.CharField(help_text='Why can_review is false; empty when true')
    review = ReviewSerializer(allow_null=True, help_text='Your rating, or null if you have not rated')


REVIEW_EXAMPLE = {'rating': 5, 'feedback': 'Doctor listened patiently and explained clearly.',
                  'created_at': '2026-11-15T11:05:00+05:30', 'updated_at': '2026-11-15T11:05:00+05:30'}


def review_reason(consultation, user):
    appointment = getattr(consultation, 'appointment', None)
    if consultation.status == Consultation.Status.CANCELLED or appointment is None or appointment.status != Appointment.Status.COMPLETED:
        return 'You can rate after the doctor marks the consultation completed.'
    if appointment.doctor_id is None:
        return 'No doctor was assigned to this consultation.'
    review = getattr(consultation, 'review', None)
    if review is not None and review.reviewer_id != user.pk:
        return 'This consultation was already rated from another account.'
    return ''


def review_status(consultation, user):
    reason = review_reason(consultation, user)
    review = getattr(consultation, 'review', None)
    own = review if review is not None and review.reviewer_id == user.pk else None
    return {
        'consultation_id': consultation.pk, 'can_review': not reason, 'reason': reason,
        'review': ReviewSerializer(own).data if own else None,
    }


def refresh_doctor_rating(doctor_id):
    profile = DoctorProfile.objects.select_for_update().filter(user_id=doctor_id).first()
    if profile is None:
        return
    average = ConsultationReview.objects.filter(doctor_id=doctor_id).aggregate(value=Avg('rating'))['value'] or 0
    profile.average_rating = Decimal(str(average)).quantize(Decimal('0.01'))
    profile.save(update_fields=['average_rating'])


class ConsultationReviewView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [IsPatient]
    serializer_class = ReviewWriteSerializer

    def consultation(self, consultation_id, lock=False):
        consultation = get_object_or_404(accessible_consultations(self.request.user).distinct(), pk=consultation_id)
        queryset = Consultation.objects.select_related('appointment', 'review')
        if lock:
            # Lock by primary key: the access query uses outer joins, which cannot be locked on PostgreSQL.
            queryset = queryset.select_for_update(of=('self',))
        return queryset.get(pk=consultation.pk)

    @extend_schema(
        tags=['Patient consultation rating'], summary='Rating status for a consultation',
        description=(
            'Call on the consultation/case screen after the call. Show the star form while `can_review` is true; '
            '`review` is your saved rating (pre-fill it to edit). The booking account and the family member who '
            'received the consultation can see it; only the first account to rate can rate or edit.'
        ),
        responses=ReviewStatusSerializer,
        examples=[
            OpenApiExample('Not rated yet', response_only=True, value={'consultation_id': 41, 'can_review': True, 'reason': '', 'review': None}),
            OpenApiExample('Rated', response_only=True, value={'consultation_id': 41, 'can_review': True, 'reason': '', 'review': REVIEW_EXAMPLE}),
            OpenApiExample('Not completed yet', response_only=True, value={
                'consultation_id': 41, 'can_review': False,
                'reason': 'You can rate after the doctor marks the consultation completed.', 'review': None,
            }),
        ],
    )
    def get(self, request, consultation_id):
        return Response(review_status(self.consultation(consultation_id), request.user))

    @extend_schema(
        tags=['Patient consultation rating'], summary='Rate a completed consultation (create or edit)',
        description=(
            'Send `rating` 1-5 and optional `feedback`. Allowed once the doctor has marked the consultation completed. '
            'Sending again edits your rating; one rating per consultation. Returns the same shape as GET.'
        ),
        request=ReviewWriteSerializer, responses=ReviewStatusSerializer,
        examples=[
            OpenApiExample('Rate with feedback', request_only=True, value={'rating': 5, 'feedback': REVIEW_EXAMPLE['feedback']}),
            OpenApiExample('Rate only', request_only=True, value={'rating': 4}),
            OpenApiExample('Saved', response_only=True, value={'consultation_id': 41, 'can_review': True, 'reason': '', 'review': REVIEW_EXAMPLE}),
        ],
    )
    @transaction.atomic
    def put(self, request, consultation_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consultation = self.consultation(consultation_id, lock=True)
        reason = review_reason(consultation, request.user)
        if reason:
            raise serializers.ValidationError({'detail': reason})
        data = serializer.validated_data
        doctor_id = consultation.appointment.doctor_id
        ConsultationReview.objects.update_or_create(
            consultation=consultation,
            defaults={'reviewer': request.user, 'doctor_id': doctor_id, 'rating': data['rating'], 'feedback': data['feedback'].strip()},
        )
        refresh_doctor_rating(doctor_id)
        return Response(review_status(self.consultation(consultation_id), request.user))
