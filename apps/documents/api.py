from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.assessments.api import get_visible_assessment
from apps.development.models import DevelopmentPlan

from .export import assessment_doc, development_plan_doc, interview_plan_doc

CONTENT_TYPES = {
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pdf': 'application/pdf',
}


def _file(content, name, fmt):
    resp = HttpResponse(content, content_type=CONTENT_TYPES[fmt])
    resp['Content-Disposition'] = f'attachment; filename="{name}.{fmt}"'
    resp['Cache-Control'] = 'no-store'
    return resp


class ExportView(APIView):
    """Eksport dokumentów. ?fmt=pdf (domyślnie) albo ?fmt=docx (wersja edytowalna)."""

    @extend_schema(
        parameters=[OpenApiParameter('kind', str, OpenApiParameter.PATH, enum=['sheet', 'development-plan', 'interview']),
                    OpenApiParameter('fmt', str, enum=['pdf', 'docx'], description='Domyślnie pdf')],
        responses={(200, 'application/pdf'): OpenApiTypes.BINARY,
                   (200, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'): OpenApiTypes.BINARY},
        tags=['Dokumenty'], summary='Arkusz oceny, plan rozwoju lub scenariusz rozmowy jako PDF/DOCX')
    def get(self, request, pk, kind):
        fmt = request.query_params.get('fmt', 'pdf')
        if fmt not in CONTENT_TYPES:
            raise NotFound('Obsługiwane formaty: pdf, docx.')
        a = get_visible_assessment(request, pk)
        slug = f'{a.employee.last_name}_{a.id}'
        if kind == 'sheet':
            return _file(assessment_doc(a, fmt), f'arkusz_{a.form_type.lower()}_{slug}', fmt)
        if kind == 'development-plan':
            plan = DevelopmentPlan.objects.filter(assessment=a).first()
            if plan is None:
                raise NotFound('Brak planu rozwoju.')
            return _file(development_plan_doc(plan, fmt), f'plan_rozwoju_{slug}', fmt)
        if kind == 'interview':
            if not a.interview_plan:
                raise NotFound('Brak zapisanego scenariusza rozmowy.')
            return _file(interview_plan_doc(a, a.interview_plan, fmt), f'scenariusz_rozmowy_{slug}', fmt)
        raise NotFound()
