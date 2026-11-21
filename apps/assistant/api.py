from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assessments.api import get_visible_assessment
from apps.institutions.models import Role

from . import service
from .client import AssistantError
from .models import AIInteraction, Conversation, LegalChunk, Message

FEATURES = {
    'analyze-job-description': 'assessment',
    'guiding-questions': 'criterion',
    'analyze-evidence': 'criterion',
    'draft-justification': 'both',
    'interview-script': 'assessment',
    'development-suggestions': 'assessment',
}


def _payload(log, out):
    data = out.model_dump() if hasattr(out, 'model_dump') else out
    return {'interaction_id': log.id if log else None, 'ai_generated': True,
            'notice': 'Treść wygenerowana przez AI — wymaga weryfikacji. Decyzja o ocenie należy do przełożonego.',
            'result': data}


class AssistantFeatureView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'assistant'

    def post(self, request, pk, feature):
        if feature not in FEATURES:
            return Response({'detail': 'Nieznana funkcja asystenta.'}, status=404)
        a = get_visible_assessment(request, pk)
        m = request.membership
        if m.role != Role.ADMIN and a.evaluator_id != request.user.id:
            raise PermissionDenied('Z asystenta dla tej oceny korzysta oceniający.')
        crit = None
        if crit_id := request.data.get('criterion'):
            crit = get_object_or_404(a.criteria.all(), pk=crit_id)
        if FEATURES[feature] == 'criterion' and crit is None:
            raise ValidationError('Wskaż kryterium (criterion).')
        try:
            if feature == 'analyze-job-description':
                log, out = service.analyze_job_description(request, a)
            elif feature == 'guiding-questions':
                log, out = service.guiding_questions(request, crit)
            elif feature == 'analyze-evidence':
                log, out = service.analyze_evidence(request, crit)
            elif feature == 'draft-justification':
                log, out = service.draft_justification(request, a, crit)
            elif feature == 'interview-script':
                log, out = service.interview_script(request, a)
            else:
                log, out = service.development_suggestions(request, a)
        except AssistantError as e:
            msg = str(e) if e.args else e.public_message
            return Response({'detail': msg}, status=e.status)
        return Response(_payload(log, out))


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'citations', 'sources', 'grounded', 'interaction', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    mode_label = serializers.CharField(source='get_mode_display', read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'mode', 'mode_label', 'assessment', 'title', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['title']


class ConversationViewSet(viewsets.ModelViewSet):
    """Rozmowy z asystentem — każdy widzi wyłącznie własne rozmowy."""

    serializer_class = ConversationSerializer
    pagination_class = None
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        qs = Conversation.objects.filter(user=self.request.user, institution=self.request.membership.institution)
        p = self.request.query_params
        if a := p.get('assessment'):
            qs = qs.filter(assessment_id=a)
        elif p.get('assessment') == '' or 'general' in p:
            qs = qs.filter(assessment__isnull=True)
        if m := p.get('mode'):
            qs = qs.filter(mode=m)
        return qs.prefetch_related('messages')

    def perform_create(self, serializer):
        a = serializer.validated_data.get('assessment')
        if a is not None:
            a = get_visible_assessment(self.request, a.pk)
            m = self.request.membership
            if m.role != Role.ADMIN and a.evaluator_id != self.request.user.id:
                raise PermissionDenied('Z asystenta dla tej oceny korzysta oceniający.')
        if serializer.validated_data.get('mode') == Conversation.Mode.INTERVIEW and a is None:
            raise ValidationError('Tryb przygotowania do rozmowy wymaga wskazania oceny.')
        serializer.save(user=self.request.user, institution=self.request.membership.institution, assessment=a)

    @action(detail=True, methods=['post'], throttle_classes=[ScopedRateThrottle])
    def messages(self, request, pk=None):
        conv = self.get_object()
        text = (request.data.get('content') or '').strip()
        if not text or len(text) > 2000:
            raise ValidationError('Wpisz wiadomość (do 2000 znaków).')
        try:
            msg = service.chat(request, conv, text)
        except AssistantError as e:
            msg = str(e) if e.args else e.public_message
            return Response({'detail': msg}, status=e.status)
        return Response(MessageSerializer(msg).data)

    def get_throttles(self):
        if self.action == 'messages':
            self.throttle_scope = 'assistant'
        return super().get_throttles()


class AssistantStatusView(APIView):
    def get(self, request):
        from .client import provider_info
        info = provider_info()
        return Response({'enabled': info['enabled'], 'provider': info['provider'], 'model': info['model'],
                         'knowledge': {k: LegalChunk.objects.filter(kind=k).count() for k in LegalChunk.Kind.values}})


class InteractionOutcomeView(APIView):
    def post(self, request, pk):
        log = get_object_or_404(AIInteraction, pk=pk, user=request.user, institution=request.membership.institution)
        outcome = request.data.get('outcome')
        if outcome not in AIInteraction.Outcome.values:
            raise ValidationError('Nieprawidłowa wartość.')
        log.outcome = outcome
        log.save(update_fields=['outcome'])
        return Response(status=status.HTTP_204_NO_CONTENT)
