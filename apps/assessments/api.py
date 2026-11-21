from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema_field
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.competencies.models import BehavioralIndicator, Competency
from apps.employees.api import employees_visible_to
from apps.employees.models import Employee
from apps.institutions.models import Role
from apps.institutions.permissions import membership
from apps.institutions.scoping import InstitutionScopedMixin

from . import workflow
from .checklist import build_checklist
from .forms_config import FORMS, FormType
from .models import Assessment, AssessmentCriterion, BehavioralEvidence, IndicatorRating, Status
from .scoring import suggest_points_from_indicator_levels
from .services import AssessmentError, create_assessment, set_additional_criteria


def forms_payload():
    return [
        {'form_type': ft.value, 'label': ft.label, 'short_name': cfg.short_name, 'mandatory': list(cfg.mandatory),
         'max_additional': cfg.max_additional, 'is_first': cfg.is_first,
         'scale': [{'points': p.points, 'label': p.label, 'model_levels': list(p.model_levels)} for p in cfg.scale]}
        for ft, cfg in FORMS.items()
    ]


def assessments_visible_to(qs, user, m):
    if m.sees_all_employees:
        return qs
    q = Q(evaluator=user) | Q(employee__supervisor=user)
    if m.role == Role.UNIT_HEAD:
        q |= Q(unit_head=user) | Q(employee__org_unit__head=user)
    return qs.filter(q).distinct()


def ensure_editable(assessment, request, *, allow_locked=False):
    m = membership(request)
    if m.role != Role.ADMIN and assessment.evaluator_id != request.user.id:
        raise PermissionDenied('Ocenę edytuje wyłącznie oceniający (bezpośredni przełożony).')
    if assessment.is_locked and not allow_locked:
        raise PermissionDenied('Ocena została sporządzona — edycja zablokowana (użyj „Otwórz ponownie”).')


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehavioralEvidence
        fields = ['id', 'criterion', 'indicator', 'situation', 'action', 'result', 'occurred_on', 'is_positive',
                  'created_at']
        read_only_fields = ['created_at']

    def validate(self, attrs):
        crit = attrs.get('criterion') or self.instance.criterion
        ind = attrs.get('indicator')
        if ind and ind.competency_id != crit.competency_id:
            raise ValidationError({'indicator': 'Wskaźnik nie należy do kompetencji tego kryterium.'})
        return attrs


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorRating
        fields = ['id', 'indicator', 'level', 'no_basis']


class CriterionSerializer(serializers.ModelSerializer):
    competency_code = serializers.CharField(source='competency.code', read_only=True)
    competency_name = serializers.CharField(source='competency.name', read_only=True)
    selected_indicators = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    evidence = EvidenceSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    suggested_points = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentCriterion
        fields = ['id', 'competency', 'competency_code', 'competency_name', 'is_mandatory', 'order',
                  'selected_indicators', 'score', 'justification', 'evidence', 'ratings', 'suggested_points']

    def get_suggested_points(self, obj) -> int | None:
        levels = [r.level for r in obj.ratings.all() if not r.no_basis]
        return suggest_points_from_indicator_levels(levels, obj.assessment.form)


class CriterionUpdateSerializer(serializers.ModelSerializer):
    selected_indicators = serializers.PrimaryKeyRelatedField(many=True, required=False,
                                                             queryset=BehavioralIndicator.objects.all())

    class Meta:
        model = AssessmentCriterion
        fields = ['score', 'justification', 'selected_indicators']

    def validate_score(self, v):
        if v is not None and v not in self.instance.assessment.form.allowed_points:
            raise ValidationError(f'Dozwolone wartości: {sorted(self.instance.assessment.form.allowed_points)}.')
        return v

    def validate_selected_indicators(self, inds):
        if any(i.competency_id != self.instance.competency_id for i in inds):
            raise ValidationError('Wskaźniki muszą należeć do kompetencji kryterium.')
        if self.instance.assessment.status != Status.DRAFT:
            raise ValidationError('Wskaźniki dobiera się przed ustaleniem kryteriów.')
        return inds


class AssessmentListSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_position = serializers.CharField(source='employee.position', read_only=True)
    evaluator_name = serializers.SerializerMethodField()
    form_label = serializers.CharField(source='get_form_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Assessment
        fields = ['id', 'employee', 'employee_name', 'employee_position', 'evaluator', 'evaluator_name',
                  'form_type', 'form_label', 'status', 'status_label', 'due_date', 'window_to', 'result',
                  'average', 'created_at', 'updated_at']

    def get_evaluator_name(self, obj) -> str:
        return obj.evaluator.get_full_name() or obj.evaluator.username


EDITABLE_FIELDS = [
    'unit_head', 'criteria_interview_date', 'due_date', 'expectations', 'goals', 'report_deadline_from',
    'report_deadline_to', 'window_from', 'window_to', 'report_text', 'report_on_time', 'prep_exam', 'period_from',
    'period_to', 'evaluation_interview_date', 'interview_notes', 'interview_plan', 'justification', 'development_conclusions',
    'previous_result', 'previous_level', 'previous_date', 'promotion_request', 'promotion_grade',
    'promotion_motivation', 'objection_filed_on',
]


class AssessmentDetailSerializer(AssessmentListSerializer):
    criteria = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()
    employee_detail = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta(AssessmentListSerializer.Meta):
        fields = AssessmentListSerializer.Meta.fields + EDITABLE_FIELDS + [
            'competency_model', 'level', 'finalized_at', 'approved_at', 'acknowledged_on', 'criteria', 'summary',
            'available_actions', 'employee_detail', 'can_edit']
        read_only_fields = ['employee', 'evaluator', 'form_type', 'status', 'competency_model', 'average', 'level',
                            'result', 'finalized_at', 'approved_at', 'acknowledged_on']

    @extend_schema_field(CriterionSerializer(many=True))
    def get_criteria(self, obj):
        qs = obj.criteria.select_related('competency', 'assessment').prefetch_related(
            'selected_indicators', 'evidence', 'ratings')
        return CriterionSerializer(qs, many=True).data

    def get_summary(self, obj) -> dict:
        return obj.summary().as_dict()

    def get_available_actions(self, obj) -> list[str]:
        req = self.context['request']
        return workflow.available_actions(obj, req.user, membership(req))

    def get_employee_detail(self, obj) -> dict:
        e = obj.employee
        return {'id': e.id, 'full_name': e.full_name, 'position': e.position, 'form_of_address': e.form_of_address,
                'org_unit': e.org_unit.name if e.org_unit else '', 'employment_date': e.employment_date,
                'is_civil_servant': e.is_civil_servant, 'service_grade': e.service_grade,
                'is_managerial': e.is_managerial}

    def get_can_edit(self, obj) -> bool:
        req = self.context['request']
        m = membership(req)
        return (m.role == Role.ADMIN or obj.evaluator_id == req.user.id) and not obj.is_locked

    def validate(self, attrs):
        if self.instance and self.instance.is_locked and set(attrs) - {'objection_filed_on'}:
            raise ValidationError('Ocena została sporządzona — edycja zablokowana.')
        return attrs


class AssessmentCreateSerializer(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    form_type = serializers.ChoiceField(choices=FormType.choices)


class AssessmentViewSet(InstitutionScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Assessment.objects.select_related('employee__org_unit', 'evaluator', 'unit_head')
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'list':
            return AssessmentListSerializer
        if self.action == 'create':
            return AssessmentCreateSerializer
        return AssessmentDetailSerializer

    def get_queryset(self):
        qs = assessments_visible_to(super().get_queryset(), self.request.user, self.get_membership())
        p = self.request.query_params
        if s := p.get('status'):
            qs = qs.filter(status__in=s.split(','))
        if e := p.get('employee'):
            qs = qs.filter(employee_id=e)
        if p.get('mine') == '1':
            qs = qs.filter(evaluator=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        ser = AssessmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        emp = ser.validated_data['employee']
        m = self.get_membership()
        visible = employees_visible_to(Employee.objects.filter(institution=m.institution), request.user, m)
        if not visible.filter(pk=emp.pk).exists():
            raise PermissionDenied('Brak dostępu do pracownika.')
        if m.role not in (Role.ADMIN,) and emp.supervisor_id != request.user.id:
            raise PermissionDenied('Ocenę rozpoczyna bezpośredni przełożony pracownika.')
        if emp.assessments.exclude(status__in=[Status.ACKNOWLEDGED, Status.CANCELLED]).exists():
            raise ValidationError('Pracownik ma już ocenę w toku.')
        try:
            a = create_assessment(institution=m.institution, employee=emp, evaluator=request.user,
                                  form_type=ser.validated_data['form_type'])
        except AssessmentError as e:
            raise ValidationError(str(e))
        return Response(AssessmentDetailSerializer(a, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        only_objection = set(serializer.validated_data) <= {'objection_filed_on'}
        ensure_editable(serializer.instance, self.request, allow_locked=only_objection)
        serializer.save()

    @action(detail=False)
    def forms(self, request):
        return Response(forms_payload())

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        a = self.get_object()
        try:
            workflow.perform(a, request.data.get('action'), user=request.user, membership=self.get_membership(),
                             data=self._transition_data(request.data))
        except workflow.TransitionError as e:
            return Response({'detail': 'Nie można wykonać akcji.', 'errors': e.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(AssessmentDetailSerializer(a, context={'request': request}).data)

    def _transition_data(self, data):
        out = {}
        if d := data.get('acknowledged_on'):
            out['acknowledged_on'] = serializers.DateField().to_internal_value(d)
        return out

    @action(detail=True)
    def checklist(self, request, pk=None):
        return Response(build_checklist(self.get_object()))

    @action(detail=True, methods=['put'], url_path='additional-criteria')
    def additional_criteria(self, request, pk=None):
        a = self.get_object()
        ensure_editable(a, request)
        ids = request.data.get('competency_ids', [])
        comps = list(Competency.objects.filter(model=a.competency_model, id__in=ids))
        if len(comps) != len(set(ids)):
            raise ValidationError('Nieznana kompetencja.')
        try:
            set_additional_criteria(a, comps)
        except AssessmentError as e:
            raise ValidationError(str(e))
        return Response(AssessmentDetailSerializer(a, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='fill-no-basis')
    def fill_no_basis(self, request, pk=None):
        """Oznacza wszystkie nieocenione wskaźniki jako „brak okazji do zaobserwowania” (świadoma decyzja
        oceniającego przy przejściu dalej). Nie zmienia wskaźników już ocenionych."""
        a = self.get_object()
        ensure_editable(a, request)
        filled = []
        for crit in a.criteria.prefetch_related('selected_indicators', 'ratings').select_related('competency'):
            rated = {r.indicator_id for r in crit.ratings.all()}
            for ind in crit.selected_indicators.all():
                if ind.id not in rated:
                    IndicatorRating.objects.create(criterion=crit, indicator=ind, level=None, no_basis=True)
                    filled.append({'criterion': crit.competency.name, 'indicator': ind.text})
        a.refresh_from_db()
        return Response({'filled': filled,
                         'assessment': AssessmentDetailSerializer(a, context={'request': request}).data})

    @action(detail=True)
    def history(self, request, pk=None):
        a = self.get_object()
        rows = []
        for h in a.history.select_related('history_user').order_by('-history_date')[:200]:
            rows.append({'date': h.history_date, 'user': h.history_user.get_full_name() if h.history_user else '',
                         'type': h.get_history_type_display(), 'status': h.status})
        return Response(rows)


class CriterionViewSet(mixins.UpdateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AssessmentCriterion.objects.none()  # tylko dla schematu OpenAPI; dane z get_queryset()
    serializer_class = CriterionUpdateSerializer

    def get_queryset(self):
        m = membership(self.request)
        visible = assessments_visible_to(Assessment.objects.filter(institution=m.institution), self.request.user, m)
        return AssessmentCriterion.objects.filter(assessment__in=visible).select_related('assessment', 'competency')

    def perform_update(self, serializer):
        ensure_editable(serializer.instance.assessment, self.request)
        serializer.save()

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        crit = self.get_object()
        return Response(CriterionSerializer(crit).data)

    @action(detail=True, methods=['put'])
    def rating(self, request, pk=None):
        crit = self.get_object()
        ensure_editable(crit.assessment, request)
        ind_id = request.data.get('indicator')
        if not crit.selected_indicators.filter(pk=ind_id).exists():
            raise ValidationError('Wskaźnik nie jest wybrany dla tego kryterium.')
        level = request.data.get('level')
        no_basis = bool(request.data.get('no_basis'))
        if level is not None and int(level) not in range(1, 6):
            raise ValidationError('Poziom 1–5.')
        if level is None and not no_basis:
            IndicatorRating.objects.filter(criterion=crit, indicator_id=ind_id).delete()
        else:
            IndicatorRating.objects.update_or_create(
                criterion=crit, indicator_id=ind_id,
                defaults={'level': None if no_basis else int(level), 'no_basis': no_basis})
        return Response(CriterionSerializer(crit).data)


class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = BehavioralEvidence.objects.none()  # tylko dla schematu OpenAPI; dane z get_queryset()
    serializer_class = EvidenceSerializer
    pagination_class = None

    def get_queryset(self):
        m = membership(self.request)
        visible = assessments_visible_to(Assessment.objects.filter(institution=m.institution), self.request.user, m)
        qs = BehavioralEvidence.objects.filter(criterion__assessment__in=visible)
        if c := self.request.query_params.get('criterion'):
            qs = qs.filter(criterion_id=c)
        return qs

    def perform_create(self, serializer):
        crit = serializer.validated_data['criterion']
        m = membership(self.request)
        if crit.assessment.institution_id != m.institution_id:
            raise PermissionDenied()
        ensure_editable(crit.assessment, self.request)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        ensure_editable(serializer.instance.criterion.assessment, self.request)
        if 'criterion' in serializer.validated_data and serializer.validated_data['criterion'] != serializer.instance.criterion:
            raise ValidationError('Nie można przenieść przykładu do innego kryterium.')
        serializer.save()

    def perform_destroy(self, instance):
        ensure_editable(instance.criterion.assessment, self.request)
        instance.delete()


def get_visible_assessment(request, pk):
    m = membership(request)
    qs = assessments_visible_to(Assessment.objects.filter(institution=m.institution), request.user, m)
    return get_object_or_404(qs, pk=pk)
