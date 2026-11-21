from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.institutions.permissions import membership

from .models import LEVELS, BehavioralIndicator, Competency, CompetencyModel


class LevelField(serializers.Serializer):
    level = serializers.IntegerField()
    text = serializers.CharField()


class IndicatorSerializer(serializers.ModelSerializer):
    levels = LevelField(many=True, read_only=True)

    class Meta:
        model = BehavioralIndicator
        fields = ['id', 'text', 'order', 'levels']


class CompetencySerializer(serializers.ModelSerializer):
    indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = Competency
        fields = ['id', 'code', 'name', 'order', 'indicators']


class CompetencyModelSerializer(serializers.ModelSerializer):
    competencies = CompetencySerializer(many=True, read_only=True)
    level_labels = serializers.SerializerMethodField()

    class Meta:
        model = CompetencyModel
        fields = ['id', 'name', 'version', 'guidance', 'competencies', 'level_labels']

    def get_level_labels(self, obj):
        return [{'level': lv, 'label': label} for lv, label in LEVELS]


class CompetencyModelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompetencyModelSerializer
    pagination_class = None

    def get_queryset(self):
        inst = membership(self.request).institution
        from django.db.models import Q
        return CompetencyModel.objects.filter(Q(institution=inst) | Q(institution__isnull=True)).prefetch_related(
            'competencies__indicators__levels')

    @action(detail=False)
    def active(self, request):
        model = CompetencyModel.active_for(membership(request).institution)
        if model is None:
            return Response({'detail': 'Brak modelu kompetencji.'}, status=404)
        model = self.get_queryset().get(pk=model.pk)
        return Response(self.get_serializer(model).data)
