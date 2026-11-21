from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assessments.api import get_visible_assessment
from apps.institutions.models import Role
from apps.institutions.permissions import IsHROrAdmin

from kompetiq import openapi as o

from . import service
from .client import AssistantError
from .knowledge import ALLOWED_EXT, MAX_UPLOAD, KnowledgeFileError, index_document
from .models import AIInteraction, Conversation, KnowledgeDocument, LegalChunk, Message, visible_chunks

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

    @extend_schema(
        parameters=[OpenApiParameter('feature', str, OpenApiParameter.PATH, enum=list(FEATURES))],
        request=o.AssistantFeatureIn, responses={200: o.AssistantFeatureOut, 400: o.Detail, 503: o.Detail},
        tags=['Asystent AI'], summary='Funkcja asystenta dla oceny (sugestia — wymaga weryfikacji przełożonego)')
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
            log, out = service.run_feature(request, a, feature, crit)
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

    queryset = Conversation.objects.none()  # tylko dla schematu OpenAPI; dane z get_queryset()
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

    @extend_schema(request=o.ChatIn, responses={200: MessageSerializer, 400: o.Detail}, tags=['Asystent AI'],
                   summary='Kolejna wiadomość w rozmowie; odpowiedź z cytowaniami źródeł')
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
    @extend_schema(responses=o.AssistantStatusOut, tags=['Asystent AI'])
    def get(self, request):
        from .client import provider_info
        info = provider_info()
        return Response({'enabled': info['enabled'], 'provider': info['provider'], 'model': info['model'],
                         'knowledge': {k: visible_chunks(request.membership.institution).filter(kind=k).count()
                                       for k in LegalChunk.Kind.values}})


class InteractionOutcomeView(APIView):
    @extend_schema(request=o.OutcomeIn, responses={204: None}, tags=['Asystent AI'],
                   summary='Rejestr: czy przełożony przyjął, zredagował czy odrzucił sugestię AI')
    def post(self, request, pk):
        log = get_object_or_404(AIInteraction, pk=pk, user=request.user, institution=request.membership.institution)
        outcome = request.data.get('outcome')
        if outcome not in AIInteraction.Outcome.values:
            raise ValidationError('Nieprawidłowa wartość.')
        log.outcome = outcome
        log.save(update_fields=['outcome'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Baza wiedzy (panel administratora) ──────────────────────────────────────────────────────────
class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    shared = serializers.SerializerMethodField(help_text='true — źródło wspólne dla wszystkich urzędów')
    disabled_here = serializers.SerializerMethodField(help_text='Źródło wspólne wyłączone w tym urzędzie')
    chunk_count = serializers.IntegerField(read_only=True)
    replaces_title = serializers.CharField(source='replaces.title', read_only=True, default='')
    uploaded_by_name = serializers.SerializerMethodField()
    file = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = KnowledgeDocument
        fields = ['id', 'title', 'kind', 'kind_label', 'source', 'valid_from', 'note', 'is_active', 'builtin', 'shared',
                  'disabled_here', 'chunk_count', 'replaces', 'replaces_title', 'uploaded_by_name', 'created_at',
                  'updated_at', 'file']
        read_only_fields = ['source', 'builtin', 'created_at', 'updated_at']

    def get_shared(self, obj) -> bool:
        return obj.institution_id is None

    def get_disabled_here(self, obj) -> bool:
        return obj.institution_id is None and obj.id in self.context.get('disabled_ids', set())

    def get_uploaded_by_name(self, obj) -> str:
        return (obj.uploaded_by.get_full_name() or obj.uploaded_by.username) if obj.uploaded_by else ''

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:  # zmiana opisu — bez ponownego wgrywania pliku
            fields['file'].required = False
        return fields


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """Źródła bazy wiedzy asystenta. Podgląd: kadry i administrator; zmiany: administrator urzędu.

    Wspólnych źródeł (z docs_assets) urząd nie usuwa, ale może je u siebie wyłączyć, np. gdy przepis zastąpiono.
    """

    queryset = KnowledgeDocument.objects.none()  # tylko dla schematu OpenAPI; dane z get_queryset()
    serializer_class = KnowledgeDocumentSerializer
    pagination_class = None
    permission_classes = [IsHROrAdmin]
    parser_classes = [MultiPartParser, JSONParser]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        inst = self.request.membership.institution
        return (KnowledgeDocument.objects.filter(Q(institution__isnull=True) | Q(institution=inst))
                .select_related('replaces', 'uploaded_by').annotate(chunk_count=Count('chunks')))

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if getattr(self.request, 'membership', None) is not None:
            ctx['disabled_ids'] = set(self.request.membership.institution.disabled_knowledge.values_list('id', flat=True))
        return ctx

    def _require_admin(self):
        if self.request.membership.role != Role.ADMIN:
            raise PermissionDenied('Bazą wiedzy zarządza administrator instytucji.')

    def _own(self, doc):
        self._require_admin()
        if doc.institution_id != self.request.membership.institution_id:
            raise PermissionDenied('Źródło wspólne można tylko wyłączyć w urzędzie (akcja disable).')
        return doc

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        doc = self.get_queryset().get(pk=serializer.instance.pk)
        return Response(self.get_serializer(doc).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_create(self, serializer):
        self._require_admin()
        f = serializer.validated_data.pop('file')
        if not f.name.lower().endswith(ALLOWED_EXT):
            raise ValidationError('Obsługiwane formaty: PDF, DOCX, TXT, MD.')
        if f.size > MAX_UPLOAD:
            raise ValidationError('Plik jest zbyt duży (maks. 20 MB).')
        inst = self.request.membership.institution
        replaces = serializer.validated_data.get('replaces')
        if replaces is not None and replaces.institution_id not in (None, inst.id):
            raise ValidationError('Można zastąpić tylko źródło wspólne albo źródło tego urzędu.')
        data = f.read()
        # is_active=True: w formularzu multipart brak pola logicznego DRF odczytuje jako false
        doc = serializer.save(institution=inst, source=f.name[:255], uploaded_by=self.request.user, is_active=True)
        try:
            n = index_document(doc, data)
        except KnowledgeFileError as e:
            raise ValidationError(str(e))
        if n == 0:
            raise ValidationError('Nie znaleziono tekstu w pliku (np. skan bez warstwy tekstowej). '
                                  'Wgraj plik z tekstem albo po rozpoznaniu OCR.')
        f.seek(0)
        doc.file.save(f'{inst.id}/{f.name}', f, save=True)
        if replaces is not None:
            self._switch(replaces, inst, enabled=False)

    def perform_update(self, serializer):
        self._own(self.get_object())
        if serializer.validated_data.pop('file', None) is not None:
            raise ValidationError('Nowa wersja pliku: wgraj nowe źródło ze wskazaniem „zastępuje”.')
        doc = serializer.save()
        doc.chunks.update(title=doc.title, kind=doc.kind)  # źródło urzędu: tytuł fragmentu = tytuł źródła

    def perform_destroy(self, instance):
        self._own(instance)
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()

    @staticmethod
    def _switch(doc, inst, enabled):
        if doc.institution_id is None:
            (doc.disabled_for.remove if enabled else doc.disabled_for.add)(inst)
        else:
            doc.is_active = enabled
            doc.save(update_fields=['is_active', 'updated_at'])

    @extend_schema(request=None, responses=KnowledgeDocumentSerializer)
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Wyłącza źródło w tym urzędzie (asystent przestaje z niego korzystać)."""
        self._require_admin()
        self._switch(self.get_object(), request.membership.institution, enabled=False)
        return Response(self.get_serializer(self.get_queryset().get(pk=pk)).data)

    @extend_schema(request=None, responses=KnowledgeDocumentSerializer)
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Ponownie włącza źródło w tym urzędzie."""
        self._require_admin()
        self._switch(self.get_object(), request.membership.institution, enabled=True)
        return Response(self.get_serializer(self.get_queryset().get(pk=pk)).data)


# ── Przejrzystość AI: podgląd wysyłki ────────────────────────────────────────────────────────────
class PreviewView(APIView):
    """Dokładna treść, która zostałaby wysłana do modelu, z kontrolą danych osobowych.

    Nie wywołuje modelu i niczego nie zapisuje — działa także bez skonfigurowanego dostawcy AI.
    """

    @extend_schema(request=o.PreviewIn, responses={200: o.PreviewOut, 400: o.Detail}, tags=['Asystent AI'],
                   summary='Podgląd wysyłki do modelu AI (bez wywołania modelu)')
    def post(self, request):
        from .preview import FEATURE_LABELS, run_preview
        feature = request.data.get('feature')
        if feature not in FEATURE_LABELS:
            raise ValidationError('Nieznana funkcja asystenta.')
        a = crit = None
        if aid := request.data.get('assessment'):
            a = get_visible_assessment(request, aid)
            if request.membership.role != Role.ADMIN and a.evaluator_id != request.user.id:
                raise PermissionDenied('Z asystenta dla tej oceny korzysta oceniający.')
        if feature != 'chat-formal' and a is None:
            raise ValidationError('Wskaż ocenę (assessment).')
        if cid := request.data.get('criterion'):
            crit = get_object_or_404(a.criteria.all(), pk=cid) if a else None
        if FEATURES.get(feature) == 'criterion' and crit is None:
            raise ValidationError('Wskaż kryterium (criterion).')
        question = (request.data.get('question') or '').strip()
        if feature.startswith('chat-') and not question:
            raise ValidationError('Wpisz pytanie.')
        try:
            return Response(run_preview(request, feature, a, crit, question[:2000]))
        except AssistantError as e:
            msg = str(e) if e.args else e.public_message
            return Response({'detail': msg}, status=e.status)
