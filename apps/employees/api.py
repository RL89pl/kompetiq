from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.assessments.forms_config import suggest_periodic_form
from apps.institutions.models import Role
from apps.institutions.scoping import InstitutionScopedMixin

from .models import Employee, JobDescription


def employees_visible_to(qs, user, m):
    if m.sees_all_employees:
        return qs
    q = Q(supervisor=user)
    if m.role == Role.UNIT_HEAD:
        q |= Q(org_unit__head=user)
    return qs.filter(q)


class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ['id', 'employee', 'symbol', 'purpose', 'main_duties', 'responsibilities', 'requirements', 'subordinates',
                  'manages_people', 'soft_competencies', 'source_name', 'valid_from', 'created_at']
        read_only_fields = ['created_at', 'source_name']


class EmployeeSerializer(serializers.ModelSerializer):
    org_unit_name = serializers.CharField(source='org_unit.name', default='', read_only=True)
    supervisor_name = serializers.SerializerMethodField()
    suggested_form = serializers.SerializerMethodField()
    latest_job_description = serializers.SerializerMethodField()
    active_assessment = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'first_name', 'last_name', 'full_name', 'position', 'form_of_address', 'org_unit', 'org_unit_name',
                  'supervisor', 'supervisor_name', 'employment_date', 'contract_end_date', 'is_civil_servant',
                  'service_grade', 'appointment_year', 'service_grade_date', 'is_managerial', 'is_office_head', 'is_active', 'suggested_form',
                  'latest_job_description', 'active_assessment']

    def get_supervisor_name(self, obj) -> str:
        return obj.supervisor.get_full_name() if obj.supervisor else ''

    def get_suggested_form(self, obj) -> str:
        return suggest_periodic_form(obj)

    @extend_schema_field(JobDescriptionSerializer(allow_null=True))
    def get_latest_job_description(self, obj):
        jd = obj.job_descriptions.first()
        return JobDescriptionSerializer(jd).data if jd else None

    def get_active_assessment(self, obj) -> dict | None:
        a = obj.assessments.exclude(status__in=['ACKNOWLEDGED', 'CANCELLED']).first()
        return {'id': a.id, 'status': a.status, 'form_type': a.form_type} if a else None


class EmployeeViewSet(InstitutionScopedMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('org_unit', 'supervisor').prefetch_related('job_descriptions')
    serializer_class = EmployeeSerializer
    pagination_class = None

    def get_queryset(self):
        qs = employees_visible_to(super().get_queryset(), self.request.user, self.get_membership())
        if self.request.query_params.get('active', '1') == '1':
            qs = qs.filter(is_active=True)
        return qs

    def _require_hr(self):
        if self.get_membership().role not in (Role.HR, Role.ADMIN):
            raise PermissionDenied('Dane pracowników zmienia kadra (HR) lub administrator.')

    def perform_create(self, serializer):
        self._require_hr()
        serializer.save(institution=self.get_institution())

    def perform_update(self, serializer):
        self._require_hr()
        serializer.save()

    def perform_destroy(self, instance):
        self._require_hr()
        instance.is_active = False
        instance.save()


class JobDescriptionViewSet(InstitutionScopedMixin, viewsets.ModelViewSet):
    queryset = JobDescription.objects.select_related('employee')
    serializer_class = JobDescriptionSerializer
    institution_lookup = 'employee__institution'
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        visible = employees_visible_to(Employee.objects.filter(institution=self.get_institution()),
                                       self.request.user, self.get_membership())
        qs = qs.filter(employee__in=visible)
        if emp := self.request.query_params.get('employee'):
            qs = qs.filter(employee_id=emp)
        return qs

    def perform_create(self, serializer):
        emp = serializer.validated_data['employee']
        visible = employees_visible_to(Employee.objects.filter(institution=self.get_institution()),
                                       self.request.user, self.get_membership())
        if not visible.filter(pk=emp.pk).exists():
            raise PermissionDenied('Brak dostępu do pracownika.')
        serializer.save()

    @action(detail=False, methods=['post'], url_path='import-osp', parser_classes=[MultiPartParser])
    def import_osp(self, request):
        """Wczytuje opis stanowiska pracy z pliku .docx (OSP) dla wskazanego pracownika."""
        from apps.competencies.models import CompetencyModel
        from .osp import map_competencies, parse_osp
        f = request.FILES.get('file')
        if f is None or not f.name.lower().endswith('.docx'):
            raise ValidationError('Wybierz plik .docx z opisem stanowiska pracy.')
        if f.size > 5 * 1024 * 1024:
            raise ValidationError('Plik jest zbyt duży (maks. 5 MB).')
        visible = employees_visible_to(Employee.objects.filter(institution=self.get_institution()),
                                       self.request.user, self.get_membership())
        emp = visible.filter(pk=request.data.get('employee')).first()
        if emp is None:
            raise PermissionDenied('Brak dostępu do pracownika.')
        try:
            osp = parse_osp(f.read())
        except Exception as e:  # noqa: BLE001 — błąd formatu pliku
            raise ValidationError(f'Nie udało się odczytać pliku: {e}')
        if not osp.tasks:
            raise ValidationError('Nie znaleziono sekcji „Główne zadania realizowane na stanowisku pracy”.')
        model = CompetencyModel.active_for(self.get_institution())
        jd = JobDescription.objects.create(
            employee=emp, symbol=osp.symbol, purpose=osp.purpose, main_duties='\n'.join(osp.tasks),
            responsibilities='\n'.join(osp.authorizations), subordinates=osp.subordinates,
            manages_people=osp.manages_people, source_name=f.name[:255],
            soft_competencies=map_competencies(osp.soft_competencies, model) if model else [],
            requirements=('Kompetencje miękkie: ' + ', '.join(osp.soft_competencies)) if osp.soft_competencies else '',
        )
        return Response(JobDescriptionSerializer(jd).data, status=status.HTTP_201_CREATED)
