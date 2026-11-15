from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import NoStoreResponseMixin
from .models import FreeConsultationOffer


def available_offers():
    now = timezone.now()
    return FreeConsultationOffer.objects.filter(
        is_active=True, doctor__is_active=True, doctor__role='doctor',
        doctor__doctor_profile__is_active=True, doctor__doctor_profile__verification_status='verified',
        doctor__doctor_profile__speciality__isnull=True,
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=now),
        Q(valid_until__isnull=True) | Q(valid_until__gt=now),
    )


class FreeConsultationSelectionSerializer(serializers.Serializer):
    coupon_code = serializers.RegexField(r'^[A-Z0-9_-]+$', max_length=40, required=False)
    doctor_id = serializers.IntegerField(min_value=1, required=False, help_text='Only for the free offer; not normal doctor selection.')

    def validate(self, attrs):
        if ('coupon_code' in attrs) != ('doctor_id' in attrs):
            raise serializers.ValidationError('Send coupon_code and doctor_id together for the free consultation offer.')
        return attrs


def selected_offer(consultation, selection, *, lock=False):
    if not selection.get('coupon_code'):
        return None
    if consultation.speciality_id is not None:
        raise serializers.ValidationError({'coupon_code': 'This offer is only for general consultations.'})
    queryset = available_offers()
    if lock:
        queryset = queryset.select_for_update(of=('self',))
    offer = queryset.filter(coupon_code=selection['coupon_code'], doctor_id=selection['doctor_id']).first()
    if offer is None:
        raise serializers.ValidationError({'coupon_code': 'This offer is unavailable, expired or not valid for the selected doctor.'})
    return offer


class FreeConsultationOfferSerializer(serializers.Serializer):
    coupon_code = serializers.CharField()
    doctor_id = serializers.IntegerField()
    doctor_name = serializers.CharField()
    category = serializers.CharField()
    fee = serializers.IntegerField()
    currency = serializers.CharField()
    valid_until = serializers.DateTimeField(allow_null=True)


class FreeConsultationOfferResponseSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    offer = FreeConsultationOfferSerializer(allow_null=True)


class FreeConsultationOfferView(NoStoreResponseMixin, generics.GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = FreeConsultationOfferResponseSerializer

    @extend_schema(
        tags=['Mobile scheduling'], summary='Current free general-consultation offer',
        description='Public, no login. No per-patient limit while active. Hide the promotion when available=false. '
        'Use the returned coupon_code and doctor_id in Case Preview and Submit Case. Booking revalidates eligibility; '
        'staff confirm this doctor and the final time. No payment or automatic doctor confirmation.',
        examples=[
            OpenApiExample('Active offer', response_only=True, value={
                'available': True, 'offer': {
                    'coupon_code': 'BANARSI_FREE', 'doctor_id': 7, 'doctor_name': 'Dr. Banarsi Das',
                    'category': 'general', 'fee': 0, 'currency': 'INR', 'valid_until': None,
                },
            }),
            OpenApiExample('No available offer', response_only=True, value={'available': False, 'offer': None}),
        ],
    )
    def get(self, request):
        offer = available_offers().select_related('doctor').first()
        payload = None
        if offer:
            payload = {
                'coupon_code': offer.coupon_code, 'doctor_id': offer.doctor_id,
                'doctor_name': f'Dr. {offer.doctor.get_full_name() or offer.doctor.username}',
                'category': 'general', 'fee': 0, 'currency': 'INR', 'valid_until': offer.valid_until,
            }
        return Response(self.get_serializer({'available': offer is not None, 'offer': payload}).data)
