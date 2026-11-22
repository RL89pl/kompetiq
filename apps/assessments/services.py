from django.db import transaction

from apps.competencies.models import Competency, CompetencyModel
from apps.deadlines import rules

from .forms_config import FormType, get_form
from .models import Assessment, AssessmentCriterion


class AssessmentError(Exception):
    pass


def first_assessment_block(employee, today=None) -> str:
    """Powód, dla którego pierwsza ocena nie jest możliwa; pusty, gdy można ją rozpocząć.

    Pierwszą ocenę przeprowadza się wobec osoby podejmującej po raz pierwszy pracę w służbie cywilnej, przed
    końcem pierwszej umowy (art. 38 ust. 1 ustawy) — nie wobec pracownika z dłuższym stażem czy po ocenie okresowej.
    """
    from datetime import date
    today = today or date.today()
    other = employee.assessments.exclude(status='CANCELLED')
    if other.filter(form_type=FormType.FIRST).exists():
        return 'Pracownik ma już pierwszą ocenę — dokonuje się jej raz, w pierwszym okresie zatrudnienia.'
    if other.exclude(form_type=FormType.FIRST).exists():
        return 'Pracownik ma ocenę okresową — pierwsza ocena dotyczy tylko pierwszego okresu zatrudnienia w służbie cywilnej.'
    if employee.employment_date:
        end = rules.first_assessment_dates(employee.employment_date, employee.contract_end_date).window_to
        if end < today:
            return (f'Termin pierwszej oceny minął {end:%d.%m.%Y} (miesiąc przed końcem pierwszej umowy, art. 38 '
                    'ust. 1 ustawy). Pierwsza ocena dotyczy osób w pierwszym okresie zatrudnienia w służbie cywilnej.')
    return ''


@transaction.atomic
def create_assessment(*, institution, employee, evaluator, form_type, unit_head=None, **fields):
    model = CompetencyModel.active_for(institution)
    if model is None:
        raise AssessmentError('Brak aktywnego modelu kompetencji — zaimportuj model.')
    form = get_form(form_type)
    if form.is_first and employee.employment_date:
        d = rules.first_assessment_dates(employee.employment_date, employee.contract_end_date)
        fields.setdefault('report_deadline_from', d.report_from)
        fields.setdefault('report_deadline_to', d.report_to)
        fields.setdefault('window_from', d.window_from)
        fields.setdefault('window_to', d.window_to)
    if unit_head is None and employee.org_unit_id and employee.org_unit.head_id:
        unit_head = employee.org_unit.head
    a = Assessment.objects.create(
        institution=institution, employee=employee, evaluator=evaluator, unit_head=unit_head,
        competency_model=model, form_type=form_type, **fields,
    )
    for i, code in enumerate(form.mandatory):
        comp = Competency.objects.get(model=model, code=code)
        add_criterion(a, comp, is_mandatory=True, order=i)
    return a


def add_criterion(assessment, competency, *, is_mandatory, order=None):
    if competency.model_id != assessment.competency_model_id:
        raise AssessmentError('Kompetencja spoza modelu przypisanego do oceny.')
    if order is None:
        order = assessment.criteria.count()
    crit = AssessmentCriterion.objects.create(
        assessment=assessment, competency=competency, is_mandatory=is_mandatory, order=order,
    )
    crit.selected_indicators.set(competency.indicators.all())
    return crit


def set_additional_criteria(assessment, competencies):
    form = assessment.form
    if assessment.status != 'DRAFT':
        raise AssessmentError('Kryteria dodatkowe można zmieniać tylko przed ich ustaleniem.')
    if len(competencies) > form.max_additional:
        raise AssessmentError(f'Można wybrać najwyżej {form.max_additional} kryteria dodatkowe.')
    mandatory_codes = set(form.mandatory)
    for comp in competencies:
        if comp.code in mandatory_codes:
            raise AssessmentError(f'„{comp.name}” jest kryterium obowiązkowym.')
    with transaction.atomic():
        wanted = {c.id for c in competencies}
        assessment.criteria.filter(is_mandatory=False).exclude(competency_id__in=wanted).delete()
        have = set(assessment.criteria.values_list('competency_id', flat=True))
        for comp in competencies:
            if comp.id not in have:
                add_criterion(assessment, comp, is_mandatory=False)
