"""Maszyna stanów procesu oceny z walidacją wymogów formalnych przy przejściach."""
from django.db import transaction
from django.utils import timezone

from apps.institutions.models import Role

from .models import Result, Status


class TransitionError(Exception):
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, list) else [errors]
        super().__init__('; '.join(self.errors))


# akcja -> (stany źródłowe, stan docelowy)
TRANSITIONS = {
    'set_criteria': ((Status.DRAFT,), Status.CRITERIA_SET),
    'reopen_criteria': ((Status.CRITERIA_SET,), Status.DRAFT),
    'complete_interview': ((Status.CRITERIA_SET,), Status.INTERVIEW_DONE),
    'finalize': ((Status.INTERVIEW_DONE,), Status.FINALIZED),
    'reopen': ((Status.FINALIZED,), Status.INTERVIEW_DONE),
    'approve': ((Status.FINALIZED,), Status.APPROVED),
    'acknowledge': ((Status.FINALIZED, Status.APPROVED), Status.ACKNOWLEDGED),
    'cancel': ((Status.DRAFT, Status.CRITERIA_SET, Status.INTERVIEW_DONE), Status.CANCELLED),
}


def check_set_criteria(a):
    errors = []
    if not a.criteria_interview_date:
        errors.append('Podaj datę rozmowy wstępnej / rozmowy ustalającej kryteria.')
    n_add = a.criteria.filter(is_mandatory=False).count()
    if n_add > a.form.max_additional:
        errors.append(f'Za dużo kryteriów dodatkowych (maks. {a.form.max_additional}).')
    for c in a.criteria.all():
        if not c.selected_indicators.exists():
            errors.append(f'Kryterium „{c.competency.name}”: wybierz co najmniej jeden wskaźnik.')
    if a.is_first:
        if not (a.report_deadline_from and a.report_deadline_to):
            errors.append('Wyznacz termin na złożenie sprawozdania.')
        if not (a.window_from and a.window_to):
            errors.append('Podaj okres, w którym powinna zostać dokonana pierwsza ocena.')
    elif not a.due_date:
        errors.append('Podaj termin sporządzenia oceny na piśmie.')
    return errors


def check_complete_interview(a):
    errors = []
    if not a.evaluation_interview_date:
        errors.append('Podaj datę przeprowadzenia rozmowy oceniającej.')
    if not a.is_first and not (a.period_from and a.period_to):
        errors.append('Podaj okres, w którym oceniany podlegał ocenie.')
    return errors


def check_finalize(a):
    errors = []
    allowed = a.form.allowed_points
    for c in a.criteria.select_related('competency'):
        if c.score is None:
            errors.append(f'Brak oceny cząstkowej: {c.competency.name}.')
        elif c.score not in allowed:
            errors.append(f'Niedozwolona wartość punktowa dla {c.competency.name}: {c.score}.')
    if a.is_first:
        if not a.prep_exam:
            errors.append('Zaznacz, czy oceniany zaliczył egzamin ze służby przygotowawczej.')
        if a.report_on_time is None:
            errors.append('Zaznacz, czy sprawozdanie zostało złożone w terminie.')
    if errors:
        return errors
    summary = a.summary()
    if not summary.complete:
        return summary.reasons
    if summary.result == Result.NEGATIVE and not a.justification.strip():
        errors.append('Uzasadnienie jest obowiązkowe przy ocenie negatywnej.')
    if not a.is_first and a.employee.is_civil_servant and a.promotion_request is None:
        errors.append('Zaznacz, czy do oceny dołączono wniosek o przyznanie kolejnego stopnia służbowego.')
    if a.promotion_request and summary.result != Result.POSITIVE:
        errors.append('Wniosek o kolejny stopień służbowy wymaga oceny pozytywnej.')
    return errors


def check_approve(a):
    return [] if a.is_first else ['Potwierdzenie przez kierującego komórką dotyczy tylko pierwszej oceny.']


def check_acknowledge(a, acknowledged_on=None):
    errors = []
    if a.is_first and a.status != Status.APPROVED:
        errors.append('Pierwsza ocena wymaga najpierw potwierdzenia przez kierującego komórką.')
    if not acknowledged_on:
        errors.append('Podaj datę zapoznania się ocenianego z oceną.')
    return errors


CHECKS = {
    'set_criteria': check_set_criteria,
    'complete_interview': check_complete_interview,
    'finalize': check_finalize,
    'approve': check_approve,
}


def can_perform(action, a, user, membership):
    """Kto może wykonać akcję: oceniający; zatwierdza kierujący komórką; admin zawsze."""
    if membership.role == Role.ADMIN:
        return True
    if action == 'approve':
        return membership.role == Role.UNIT_HEAD and (a.unit_head_id in (None, user.id))
    return a.evaluator_id == user.id


def available_actions(a, user, membership):
    out = []
    for action, (sources, _) in TRANSITIONS.items():
        if a.status in sources and can_perform(action, a, user, membership):
            if action == 'approve' and not a.is_first:
                continue
            out.append(action)
    return out


@transaction.atomic
def perform(a, action, *, user, membership, data=None):
    data = data or {}
    if action not in TRANSITIONS:
        raise TransitionError(f'Nieznana akcja: {action}.')
    sources, target = TRANSITIONS[action]
    if a.status not in sources:
        raise TransitionError(f'Akcja „{action}” niedostępna w statusie „{a.get_status_display()}”.')
    if not can_perform(action, a, user, membership):
        raise TransitionError('Brak uprawnień do wykonania tej akcji.')
    if action == 'acknowledge':
        errors = check_acknowledge(a, data.get('acknowledged_on'))
    else:
        errors = CHECKS.get(action, lambda _a: [])(a)
    if errors:
        raise TransitionError(errors)

    if action == 'finalize':
        s = a.summary()
        a.average, a.level, a.result = s.average, s.level, s.result
        a.finalized_at = timezone.now()
    elif action == 'reopen':
        a.average = a.level = None
        a.result = ''
        a.finalized_at = None
    elif action == 'approve':
        a.approved_at, a.approved_by = timezone.now(), user
    elif action == 'acknowledge':
        a.acknowledged_on = data['acknowledged_on']
    a.status = target
    a.save()
    from apps.deadlines.notify import on_transition
    transaction.on_commit(lambda: on_transition(a, action, user))
    return a
