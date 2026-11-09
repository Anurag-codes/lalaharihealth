from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_field
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from apps.doctors.models import Speciality
from apps.treatments.models import Condition, ConditionType, ConditionVariant, booking_speciality


class ConditionVariantChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionVariant
        fields = ['id', 'name']


class MappedSpecialitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True, help_text='Consultation title, e.g. "Skin Consultation"')
    fee = serializers.SerializerMethodField(help_text='Fixed INR fee that will be charged (same as GET /api/v1/pricing/consultation-fee/)')
    currency = serializers.SerializerMethodField()
    fee_display = serializers.SerializerMethodField(help_text='e.g. "\u20b9500"')

    class Meta:
        model = Speciality
        fields = ['id', 'name', 'slug', 'title', 'fee', 'currency', 'fee_display']
        read_only_fields = fields

    def _fee(self, obj):
        from apps.pricing.service import speciality_fee

        cache = self.context.setdefault('speciality_fees', {})
        if obj.pk not in cache:
            cache[obj.pk] = speciality_fee(obj)[0]
        return cache[obj.pk]

    def get_fee(self, obj) -> int:
        return self._fee(obj)

    def get_currency(self, obj) -> str:
        return 'INR'

    def get_fee_display(self, obj) -> str:
        from apps.pricing.service import format_amount

        return format_amount(self._fee(obj), '\u20b9')


SPECIALITY_HELP = (
    'Specialist booked automatically for this choice; null = General Physician (general fee from GET /api/v1/pricing/).'
)


class ConditionTypeChoiceSerializer(serializers.ModelSerializer):
    speciality = serializers.SerializerMethodField(help_text=SPECIALITY_HELP + ' Already resolved: this type\'s own speciality, else the disease\'s.')
    variants = ConditionVariantChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = ConditionType
        fields = ['id', 'name', 'speciality', 'variants']

    @extend_schema_field(MappedSpecialitySerializer(allow_null=True))
    def get_speciality(self, obj):
        speciality = booking_speciality(obj.condition, obj)
        return MappedSpecialitySerializer(speciality, context=self.context).data if speciality else None


class ConditionChoiceSerializer(serializers.ModelSerializer):
    type_label = serializers.SerializerMethodField(help_text='Label for the second dropdown')
    speciality = serializers.SerializerMethodField(help_text=SPECIALITY_HELP + ' When types exist, use the selected type\'s speciality.')
    types = ConditionTypeChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Condition
        fields = ['id', 'name', 'slug', 'type_label', 'speciality', 'types']

    def get_type_label(self, obj) -> str:
        return obj.type_label or f'Specific {obj.name} Type'

    @extend_schema_field(MappedSpecialitySerializer(allow_null=True))
    def get_speciality(self, obj):
        speciality = booking_speciality(obj)
        return MappedSpecialitySerializer(speciality, context=self.context).data if speciality else None


NEUROLOGY = {
    'id': 4, 'name': 'Neurology', 'slug': 'neurology', 'title': 'Neurology Consultation', 'fee': 600,
    'currency': 'INR', 'fee_display': '\u20b9600',
}
CONDITIONS_EXAMPLE = [
    {
        'id': 3, 'name': 'Headache', 'slug': 'headache', 'type_label': 'Specific Headache Type', 'speciality': None,
        'types': [
            {
                'id': 7, 'name': 'Cluster Headache', 'speciality': NEUROLOGY,
                'variants': [{'id': 15, 'name': 'Chronic'}, {'id': 16, 'name': 'Episodic'}],
            },
            {
                'id': 8, 'name': 'Tension Headache', 'speciality': None,
                'variants': [],
            },
        ],
    },
    {
        'id': 9, 'name': 'Skin Rash', 'slug': 'skin-rash', 'type_label': 'Specific Skin Rash Type',
        'speciality': {
            'id': 2, 'name': 'Dermatology', 'slug': 'dermatology', 'title': 'Skin Consultation', 'fee': 500,
            'currency': 'INR', 'fee_display': '\u20b9500',
        },
        'types': [],
    },
]


@extend_schema(
    tags=['Mobile intake'], summary='Symptoms dropdowns: known disease -> specific type -> sub-condition/variant',
    description=(
        'Staff manage options in Django admin. Show the second dropdown using type_label when the selected disease '
        'has types, and the "Sub-condition / Variant for {type}" dropdown when the selected type has variants. '
        'Returns the whole tree at once as a plain array (no pagination, no page parameter).\n\n'
        'Specialist mapping: the patient never picks a speciality. Saving the Symptoms step '
        '(`PUT /api/v1/consultations/{id}/history/`) sets it from the chosen disease/type, and that decides the fee '
        'and which doctors staff can assign. `speciality` on a type is already resolved (the type\'s own, else the '
        'disease\'s), so show the selected type\'s value when the disease has types, otherwise the disease\'s. '
        'null = General Physician at the general fee from `GET /api/v1/pricing/`. Staff set the mapping in Django '
        'admin (Conditions / Condition types).'
    ),
    examples=[OpenApiExample('Disease tree', value=CONDITIONS_EXAMPLE, response_only=True)],
)
class ConditionChoicesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConditionChoiceSerializer
    pagination_class = None

    def get_queryset(self):
        variants = ConditionVariant.objects.filter(is_active=True)
        types = (
            ConditionType.objects.filter(is_active=True).select_related('speciality', 'condition__speciality')
            .prefetch_related(Prefetch('variants', queryset=variants))
        )
        return (
            Condition.objects.filter(is_active=True).select_related('speciality')
            .prefetch_related(Prefetch('types', queryset=types))
        )
