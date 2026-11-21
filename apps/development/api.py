from datetime import date

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.assessments.api import assessments_visible_to
from apps.assessments.models import Assessment
from apps.institutions.models import Role
from apps.institutions.permissions import membership

from .models import DevelopmentAction, DevelopmentPlan, ProgressNote


class NoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ProgressNote
        fields = ['id', 'text', 'author_name', 'created_at']

    def get_author_name(self, obj) -> str:
        return obj.author.get_full_name() if obj.author else ''


class ActionSerializer(serializers.ModelSerializer):
    notes = NoteSerializer(many=True, read_only=True)
    competency_name = serializers.CharField(source='competency.name', default='', read_only=True)
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DevelopmentAction
        fields = ['id', 'plan', 'competency', 'competency_name', 'title', 'description', 'type', 'type_label',
                  'success_measure', 'owner', 'due_date', 'status', 'status_label', 'from_ai_suggestion', 'notes']


OPEN = (DevelopmentAction.Status.PLANNED, DevelopmentAction.Status.IN_PROGRESS)


def plan_stats(plan, today=None):
    """Podsumowanie planu z prefetchowanych działań (bez dodatkowych zapytań)."""
    today = today or date.today()
    acts = [a for a in plan.actions.all() if a.status != DevelopmentAction.Status.CANCELLED]
    open_ = [a for a in acts if a.status in OPEN]
    done = sum(a.status == DevelopmentAction.Status.DONE for a in acts)
    overdue = [a for a in open_ if a.due_date and a.due_date < today]
    upcoming = sorted((a for a in open_ if a.due_date), key=lambda a: a.due_date)
    notes = [n.created_at for a in plan.actions.all() for n in a.notes.all()]
    nxt = upcoming[0] if upcoming else None
    return {
        'total': len(acts), 'done': done, 'percent': round(100 * done / len(acts)) if acts else 0,
        'in_progress': sum(a.status == DevelopmentAction.Status.IN_PROGRESS for a in acts),
        'planned': sum(a.status == DevelopmentAction.Status.PLANNED for a in acts),
        'overdue': len(overdue),
        'next_action': {'title': nxt.title, 'due_date': nxt.due_date, 'overdue': nxt.due_date < today} if nxt else None,
        'last_activity': max(notes + [plan.updated_at]) if plan else None,
    }


class PlanEmployeeMixin(serializers.Serializer):
    employee_id = serializers.IntegerField(source='assessment.employee_id', read_only=True)
    employee_name = serializers.CharField(source='assessment.employee.full_name', read_only=True)
    position = serializers.CharField(source='assessment.employee.position', read_only=True)
    org_unit = serializers.CharField(source='assessment.employee.org_unit.name', default='', read_only=True)
    evaluator_name = serializers.SerializerMethodField()
    assessment_label = serializers.CharField(source='assessment.get_form_type_display', read_only=True)
    assessment_result = serializers.CharField(source='assessment.result', read_only=True)
    assessment_date = serializers.DateTimeField(source='assessment.finalized_at', read_only=True)

    def get_evaluator_name(self, obj) -> str:
        e = obj.assessment.evaluator
        return e.get_full_name() or e.username


class PlanListSerializer(PlanEmployeeMixin, serializers.ModelSerializer):
    stats = serializers.SerializerMethodField()

    class Meta:
        model = DevelopmentPlan
        fields = ['id', 'assessment', 'employee_id', 'employee_name', 'position', 'org_unit', 'evaluator_name',
                  'assessment_label', 'assessment_result', 'assessment_date', 'stats', 'updated_at']

    def get_stats(self, obj) -> dict:
        return plan_stats(obj)


class PlanSerializer(PlanEmployeeMixin, serializers.ModelSerializer):
    actions = ActionSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = DevelopmentPlan
        fields = ['id', 'assessment', 'employee_id', 'employee_name', 'position', 'org_unit', 'evaluator_name',
                  'assessment_label', 'assessment_result', 'assessment_date', 'summary', 'actions', 'progress',
                  'stats', 'history', 'can_edit', 'updated_at']
        read_only_fields = ['assessment']

    def get_progress(self, obj) -> dict:
        return obj.progress()

    def get_stats(self, obj) -> dict:
        return plan_stats(obj)

    def get_history(self, obj) -> list[dict]:
        """Wcześniejsze plany tego samego pracownika."""
        req = self.context.get('request')
        if req is None:
            return []
        older = DevelopmentPlan.objects.filter(
            assessment__in=visible_assessments(req), assessment__employee_id=obj.assessment.employee_id,
        ).exclude(pk=obj.pk).select_related('assessment').order_by('-assessment__created_at')
        return [{'id': p.id, 'label': p.assessment.get_form_type_display(), 'date': p.assessment.finalized_at or p.created_at,
                 'progress': p.progress()} for p in older]

    def get_can_edit(self, obj) -> bool:
        req = self.context.get('request')
        if req is None:
            return False
        m = membership(req)
        return m.role == Role.ADMIN or obj.assessment.evaluator_id == req.user.id


def visible_assessments(request):
    m = membership(request)
    return assessments_visible_to(Assessment.objects.filter(institution=m.institution), request.user, m)


def ensure_owner(request, assessment):
    m = membership(request)
    if m.role != Role.ADMIN and assessment.evaluator_id != request.user.id:
        raise PermissionDenied('Plan rozwoju prowadzi oceniający.')


class PlanViewSet(viewsets.ModelViewSet):
    """Lista: domyślnie aktualny plan każdego pracownika (z najnowszej oceny), lekkie podsumowania.
    ?all=1 — wszystkie plany (także wcześniejsze); ?assessment=<id> — plan danej oceny."""

    queryset = DevelopmentPlan.objects.none()  # tylko dla schematu OpenAPI; dane z get_queryset()
    pagination_class = None
    http_method_names = ['get', 'patch', 'post']

    def get_serializer_class(self):
        return PlanListSerializer if self.action == 'list' else PlanSerializer

    def get_queryset(self):
        qs = DevelopmentPlan.objects.filter(assessment__in=visible_assessments(self.request)).select_related(
            'assessment__employee__org_unit', 'assessment__evaluator').prefetch_related(
            'actions__notes__author', 'actions__competency')
        p = self.request.query_params
        if a := p.get('assessment'):
            return qs.filter(assessment_id=a)
        if self.action == 'list' and p.get('all') != '1':
            latest = {}
            for plan_id, emp_id in qs.order_by('assessment__employee_id', '-assessment__created_at').values_list(
                    'id', 'assessment__employee_id'):
                latest.setdefault(emp_id, plan_id)
            qs = qs.filter(id__in=latest.values())
        return qs.order_by('assessment__employee__last_name', 'assessment__employee__first_name')

    @action(detail=False, methods=['post'], url_path='for-assessment')
    def for_assessment(self, request):
        a = visible_assessments(request).filter(pk=request.data.get('assessment')).first()
        if a is None:
            raise ValidationError('Nieznana ocena.')
        plan, _ = DevelopmentPlan.objects.get_or_create(assessment=a)
        return Response(PlanSerializer(plan, context={'request': request}).data)

    def create(self, request, *a, **kw):
        return self.for_assessment(request)

    def perform_update(self, serializer):
        ensure_owner(self.request, serializer.instance.assessment)
        serializer.save()


class ActionViewSet(viewsets.ModelViewSet):
    queryset = DevelopmentAction.objects.none()  # tylko dla schematu OpenAPI; dane z get_queryset()
    serializer_class = ActionSerializer
    pagination_class = None

    def get_queryset(self):
        return DevelopmentAction.objects.filter(plan__assessment__in=visible_assessments(self.request))

    def perform_create(self, serializer):
        plan = serializer.validated_data['plan']
        if not visible_assessments(self.request).filter(pk=plan.assessment_id).exists():
            raise PermissionDenied()
        ensure_owner(self.request, plan.assessment)
        serializer.save()

    def perform_update(self, serializer):
        ensure_owner(self.request, serializer.instance.plan.assessment)
        serializer.save()

    def perform_destroy(self, instance):
        ensure_owner(self.request, instance.plan.assessment)
        instance.delete()

    @action(detail=True, methods=['post'])
    def notes(self, request, pk=None):
        act = self.get_object()
        ensure_owner(request, act.plan.assessment)
        text = (request.data.get('text') or '').strip()
        if not text:
            raise ValidationError('Pusta notatka.')
        ProgressNote.objects.create(action=act, text=text, author=request.user)
        return Response(ActionSerializer(act).data)
