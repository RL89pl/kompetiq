"""Wyliczanie terminów dla zbioru ocen — wspólne dla widoku terminów, panelu HR i przypomnień."""
from datetime import date, timedelta

from apps.assessments.models import Status
from apps.development.models import DevelopmentAction

from . import rules

DONE = (Status.FINALIZED, Status.APPROVED, Status.ACKNOWLEDGED)


def deadlines_for(assessments, *, horizon_days=60, today=None, include_development=True):
    today = today or date.today()
    limit = today + timedelta(days=horizon_days)
    out = []

    def add(a, kind, label, d, basis):
        if d and d <= limit:
            out.append({'assessment': a.id, 'employee': a.employee.full_name, 'evaluator_id': a.evaluator_id,
                        'evaluator': a.evaluator.get_full_name() or a.evaluator.username, 'kind': kind,
                        'label': label, 'date': d, 'days_left': (d - today).days, 'overdue': d < today,
                        'basis': basis})

    for a in assessments:
        if a.status == Status.CANCELLED:
            continue
        if a.is_first:
            if a.status == Status.DRAFT and a.employee.employment_date and not a.criteria_interview_date:
                add(a, 'initial_interview', 'Rozmowa wstępna',
                    rules.first_assessment_dates(a.employee.employment_date).initial_interview_by, '§ 3 rozp. 2015')
            if a.status in (Status.DRAFT, Status.CRITERIA_SET):
                add(a, 'report', 'Termin sprawozdania', a.report_deadline_to, '§ 4 rozp. 2015')
            if a.status not in DONE:
                add(a, 'first_window', 'Koniec okresu na pierwszą ocenę', a.window_to, 'art. 38 ust. 1 ustawy')
            if a.status == Status.FINALIZED:
                add(a, 'approval', 'Potwierdzenie przez kierującego komórką', today, '§ 4 i arkusz pierwszej oceny')
        else:
            if a.status not in DONE:
                add(a, 'due', 'Termin sporządzenia oceny', a.due_date, 'art. 81 ust. 4 ustawy')
            if a.acknowledged_on and not a.objection_filed_on:
                d = rules.objection_deadline(a.acknowledged_on)
                if d >= today:
                    add(a, 'objection', 'Termin na sprzeciw', d, 'art. 83 ust. 1 ustawy')
            if a.status == Status.ACKNOWLEDGED and a.result == 'NEGATIVE' and a.acknowledged_on:
                add(a, 'reassessment', 'Ponowna ocena po negatywnej', rules.add_months(a.acknowledged_on, 6),
                    'art. 81 ust. 9 ustawy')
        if a.status == Status.FINALIZED and not a.is_first:
            add(a, 'acknowledge', 'Zapoznanie ocenianego z oceną', today, '§ 12 rozp. 2016')
    if include_development:
        acts = DevelopmentAction.objects.filter(
            plan__assessment__in=[a.id for a in assessments], status__in=['PLANNED', 'IN_PROGRESS'],
            due_date__isnull=False, due_date__lte=limit).select_related('plan__assessment__employee',
                                                                         'plan__assessment__evaluator')
        for act in acts:
            a = act.plan.assessment
            out.append({'assessment': a.id, 'employee': a.employee.full_name, 'evaluator_id': a.evaluator_id,
                        'evaluator': a.evaluator.get_full_name(), 'kind': 'development',
                        'label': f'Działanie rozwojowe: {act.title}', 'date': act.due_date,
                        'days_left': (act.due_date - today).days, 'overdue': act.due_date < today, 'basis': ''})
    out.sort(key=lambda r: r['date'])
    return out
