from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from apps.treatments.models import Condition


class ConditionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = ['id', 'name', 'slug']


@extend_schema(tags=['Mobile intake'], summary='Known disease/category dropdown (staff manage options in admin)')
class ConditionChoicesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConditionChoiceSerializer
    queryset = Condition.objects.filter(is_active=True)