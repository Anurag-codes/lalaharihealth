from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from apps.treatments.models import Condition, ConditionType, ConditionVariant


class ConditionVariantChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionVariant
        fields = ['id', 'name']


class ConditionTypeChoiceSerializer(serializers.ModelSerializer):
    variants = ConditionVariantChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = ConditionType
        fields = ['id', 'name', 'variants']


class ConditionChoiceSerializer(serializers.ModelSerializer):
    type_label = serializers.SerializerMethodField(help_text='Label for the second dropdown')
    types = ConditionTypeChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Condition
        fields = ['id', 'name', 'slug', 'type_label', 'types']

    def get_type_label(self, obj) -> str:
        return obj.type_label or f'Specific {obj.name} Type'


CONDITIONS_EXAMPLE = {
    'count': 1, 'next': None, 'previous': None,
    'results': [{
        'id': 3, 'name': 'Headache', 'slug': 'headache', 'type_label': 'Specific Headache Type',
        'types': [
            {'id': 7, 'name': 'Cluster Headache', 'variants': [{'id': 15, 'name': 'Chronic'}, {'id': 16, 'name': 'Episodic'}]},
            {'id': 8, 'name': 'Migraine', 'variants': [{'id': 17, 'name': 'With aura'}, {'id': 18, 'name': 'Without aura'}]},
        ],
    }],
}


@extend_schema(
    tags=['Mobile intake'], summary='Symptoms dropdowns: known disease -> specific type -> sub-condition/variant',
    description=(
        'Staff manage options in Django admin. Show the second dropdown using type_label when the selected disease '
        'has types, and the "Sub-condition / Variant for {type}" dropdown when the selected type has variants. '
        'The list is paginated (20 per page); follow next for more.'
    ),
    examples=[OpenApiExample('Disease tree', value=CONDITIONS_EXAMPLE, response_only=True)],
)
class ConditionChoicesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConditionChoiceSerializer

    def get_queryset(self):
        variants = ConditionVariant.objects.filter(is_active=True)
        types = ConditionType.objects.filter(is_active=True).prefetch_related(Prefetch('variants', queryset=variants))
        return Condition.objects.filter(is_active=True).prefetch_related(Prefetch('types', queryset=types))
