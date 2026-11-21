"""Funkcje asystenta. Każda przygotowuje materiał (pseudonimizowany), wywołuje model i zapisuje AIInteraction."""
import hashlib
import json
import re

from apps.assessments.models import Assessment, AssessmentCriterion
from apps.competencies.models import LEVEL_LABELS

from . import prompts, schemas
from .client import AssistantError, AssistantInputError, get_provider
from .models import AIInteraction, Conversation, GuidingQuestionCache, Message
from .retrieval import build_context, search_scored


class Pseudonymizer:
    """Zastępuje imię i nazwisko ocenianego (we wszystkich odmianach zaczynających się od rdzenia)."""

    def __init__(self, employee):
        names = [n for n in (employee.first_name, employee.last_name) if n and len(n) >= 3]
        self.patterns = [re.compile(r'\b' + re.escape(n[:max(3, len(n) - 2)]) + r'\w*', re.I) for n in names]
        self.label = 'Oceniana' if employee.form_of_address == 'PANI' else 'Oceniany'

    def __call__(self, text):
        text = text or ''
        for p in self.patterns:
            text = p.sub(self.label, text)
        # „Oceniana Oceniana” (imię + nazwisko) → jedno słowo
        return re.sub(rf'\b({self.label})(\s+{self.label})+\b', r'\1', text)


def _system(model, codes=None, levels=True):
    """Zasady + (opcjonalnie) potrzebny fragment modelu. codes=[] — same zasady."""
    if codes is not None and not codes:
        return [prompts.SYSTEM_PRINCIPLES]
    return [prompts.SYSTEM_PRINCIPLES, prompts.competency_model_text(model, codes, levels)]


def _codes(a):
    return list(a.criteria.values_list('competency__code', flat=True))


def _log(request, assessment, feature, prompt, result=None, error=''):
    m = request.membership
    return AIInteraction.objects.create(
        institution=m.institution, user=request.user, assessment=assessment, feature=feature,
        model=getattr(result, 'model', '') or '', request_digest=hashlib.sha256(prompt.encode()).hexdigest(),
        response=(result.parsed.model_dump() if result and result.parsed is not None
                  else ({'text': result.text, 'citations': result.citations} if result else None)),
        error=error, input_tokens=getattr(result, 'input_tokens', 0), output_tokens=getattr(result, 'output_tokens', 0),
        cache_read_tokens=getattr(result, 'cache_read_tokens', 0), duration_ms=getattr(result, 'duration_ms', 0),
    )


def address_note(a):
    """Instrukcja o formie zwracania się do ocenianego — z danych kadrowych, nigdy zgadywana z imienia."""
    return prompts.ADDRESS_NOTES.get(a.employee.form_of_address or '', prompts.ADDRESS_NOTES[''])


def _run_structured(request, assessment, feature, prompt, schema, effort='medium', codes=None, levels=True):
    prompt = f'{prompt}\n\n{address_note(assessment)}'
    try:
        result = get_provider().structured(system=_system(assessment.competency_model, codes, levels), prompt=prompt,
                                           schema=schema, effort=effort)
    except AssistantError as e:
        _log(request, assessment, feature, prompt, error=f'{type(e).__name__}: {e}')
        raise
    log = _log(request, assessment, feature, prompt, result)
    return log, result.parsed


def _criterion_material(crit: AssessmentCriterion, anon):
    inds = list(crit.selected_indicators.all())
    ratings = {r.indicator_id: r for r in crit.ratings.all()}
    ind_text = '\n'.join(f'- [{i.id}] {i.text}' for i in inds)
    rating_text = ', '.join(
        f'[{iid}]: {"brak podstaw" if r.no_basis else LEVEL_LABELS.get(r.level, "")}' for iid, r in ratings.items()
    ) or 'brak'
    ev = []
    for e in crit.evidence.all():
        ev.append(json.dumps({
            'evidence_id': e.id, 'indicator_id': e.indicator_id, 'data': str(e.occurred_on or ''),
            'sytuacja': anon(e.situation), 'dzialanie': anon(e.action), 'rezultat': anon(e.result),
        }, ensure_ascii=False))
    return inds, ind_text, rating_text, '\n'.join(ev) or '(brak przykładów)'


def _assessment_material(a: Assessment, anon, *, with_scores=True):
    form = a.form
    lines = [f'Rodzaj: {a.get_form_type_display()}', f'Stanowisko: {a.employee.position}']
    if a.goals:
        lines.append(f'Cele na okres oceny: {anon(a.goals)}')
    if a.expectations:
        lines.append(f'Oczekiwania przełożonego: {anon(a.expectations)}')
    if with_scores:
        s = a.summary()
        if s.complete:
            lines.append(f'Wynik ustalony na podstawie ocen przełożonego: {"pozytywna" if s.result == "POSITIVE" else "negatywna"}'
                         + (f', średnia {s.average}' if s.average is not None else ''))
    for c in a.ordered_criteria().prefetch_related('evidence', 'selected_indicators'):
        lines.append(f'\n## {c.competency.name} [kod: {c.competency.code}]'
                     f'{" (obowiązkowe)" if c.is_mandatory else " (dodatkowe)"}')
        if with_scores and c.score is not None:
            lines.append(f'Ocena cząstkowa przełożonego: {c.score} pkt — {form.label_for_points(c.score)}')
        if c.justification:
            lines.append(f'Uzasadnienie przełożonego: {anon(c.justification)}')
        for e in c.evidence.all():
            lines.append(f'- Przykład ({e.occurred_on or "bez daty"}): S: {anon(e.situation)} | '
                         f'D: {anon(e.action)} | R: {anon(e.result)}')
    if a.interview_notes:
        lines.append(f'\nNotatki z rozmowy: {anon(a.interview_notes)}')
    return '\n'.join(lines)


# --- funkcje --------------------------------------------------------------------------------------------------

def analyze_job_description(request, a: Assessment):
    anon = Pseudonymizer(a.employee)
    jd = a.employee.job_descriptions.first()
    if jd is None:
        raise AssistantInputError('Brak opisu stanowiska — dodaj go w danych pracownika.')
    form = a.form
    prompt = prompts.JOB_ANALYSIS.format(
        kind='pierwsza ocena' if a.is_first else 'ocena okresowa', form=form.short_name,
        mandatory=', '.join(form.mandatory), is_managerial=a.employee.is_managerial,
        is_office_head=a.employee.is_office_head, job_description=anon(jd.as_text()),
        max_additional=form.max_additional,
    )
    log, out = _run_structured(request, a, 'analyze_job_description', prompt, schemas.JobAnalysis, levels=False)
    valid_codes = set(a.competency_model.competencies.values_list('code', flat=True)) - set(form.mandatory)
    out.additional_criteria = [c for c in out.additional_criteria if c.competency_code in valid_codes][:form.max_additional]
    valid_ind = set(a.competency_model.competencies.values_list('indicators__id', flat=True))
    out.priority_indicators = [p for p in out.priority_indicators if p.indicator_id in valid_ind]
    return log, out


def guiding_questions(request, crit: AssessmentCriterion):
    a = crit.assessment
    inds = list(crit.selected_indicators.all())
    cached = {c.indicator_id: c.questions for c in GuidingQuestionCache.objects.filter(indicator__in=inds)}
    missing = [i for i in inds if i.id not in cached]
    log = None
    if missing:
        prompt = prompts.GUIDING_QUESTIONS.format(
            context='', competency=crit.competency.name,
            indicators='\n'.join(f'- [{i.id}] {i.text}' for i in missing))
        log, out = _run_structured(request, a, 'guiding_questions', prompt, schemas.GuidingQuestions, effort='low',
                                   codes=[])
        ids = {i.id for i in missing}
        for item in out.items:
            if item.indicator_id in ids:
                GuidingQuestionCache.objects.update_or_create(indicator_id=item.indicator_id,
                                                              defaults={'questions': item.questions})
                cached[item.indicator_id] = item.questions
    return log, schemas.GuidingQuestions(items=[
        schemas.IndicatorQuestions(indicator_id=i.id, questions=cached.get(i.id, [])) for i in inds])


def analyze_evidence(request, crit: AssessmentCriterion):
    anon = Pseudonymizer(crit.assessment.employee)
    inds, ind_text, rating_text, ev_text = _criterion_material(crit, anon)
    if not crit.evidence.exists():
        raise AssistantInputError('Dodaj co najmniej jeden przykład zachowania, aby asystent mógł go przeanalizować.')
    prompt = prompts.EVIDENCE_ANALYSIS.format(competency=crit.competency.name, indicators=ind_text,
                                              ratings=rating_text, evidence=ev_text)
    log, out = _run_structured(request, crit.assessment, 'analyze_evidence', prompt, schemas.EvidenceAnalysis,
                               codes=[crit.competency.code],
                               effort='high')
    valid_ev = set(crit.evidence.values_list('id', flat=True))
    valid_ind = {i.id for i in inds}
    out.mappings = [m for m in out.mappings if m.evidence_id in valid_ev]
    for m in out.mappings:
        if m.indicator_id not in valid_ind:
            m.indicator_id = None
        if m.closest_anchor_level is not None and m.closest_anchor_level not in range(1, 6):
            m.closest_anchor_level = None
    with_ev = set(crit.evidence.exclude(indicator__isnull=True).values_list('indicator_id', flat=True))
    out.indicators_without_evidence = sorted(valid_ind - with_ev - {m.indicator_id for m in out.mappings})
    return log, out


def draft_justification(request, a: Assessment, crit: AssessmentCriterion | None = None):
    anon = Pseudonymizer(a.employee)
    if crit is not None:
        if crit.score is None:
            raise AssistantInputError('Najpierw ustal ocenę cząstkową — asystent nie proponuje ocen.')
        _, ind_text, rating_text, ev_text = _criterion_material(crit, anon)
        levels = []
        for ind in crit.selected_indicators.prefetch_related('levels'):
            for lv in ind.levels.all():
                levels.append(f'[{ind.id}] poziom {lv.level}: {lv.text}')
        body = (f'Kryterium: {crit.competency.name}\nOcena cząstkowa ustalona przez przełożonego: {crit.score} pkt — '
                f'{a.form.label_for_points(crit.score)}\nWskaźniki:\n{ind_text}\nOpisy poziomów:\n' + '\n'.join(levels)
                + f'\nOceny wskaźników: {rating_text}\nPrzykłady:\n{ev_text}')
        what = f'oceny cząstkowej za kryterium „{crit.competency.name}”'
    else:
        s = a.summary()
        if not s.complete:
            raise AssistantInputError('Uzupełnij wszystkie oceny cząstkowe przed przygotowaniem uzasadnienia oceny.')
        body = _assessment_material(a, anon)
        what = 'przyznanej oceny (pole „Uzasadnienie przyznanej oceny” w arkuszu)'
    prompt = prompts.JUSTIFICATION.format(what=what, body=body)
    return _run_structured(request, a, 'draft_justification', prompt, schemas.JustificationDraft,
                           codes=[] if crit is not None else _codes(a), levels=False)


def interview_script(request, a: Assessment):
    anon = Pseudonymizer(a.employee)
    prompt = prompts.INTERVIEW.format(kind=a.get_form_type_display(), body=_assessment_material(a, anon))
    return _run_structured(request, a, 'interview_script', prompt, schemas.InterviewScript, effort='high',
                           codes=_codes(a), levels=False)


def development_suggestions(request, a: Assessment):
    anon = Pseudonymizer(a.employee)
    prompt = prompts.DEVELOPMENT.format(
        body=_assessment_material(a, anon),
        conclusions_field='rozwoju zawodowego ocenianego' if a.is_first else 'indywidualnego programu rozwoju zawodowego')
    log, out = _run_structured(request, a, 'development_suggestions', prompt, schemas.DevelopmentSuggestions,
                               codes=_codes(a), levels=False)
    valid = set(a.competency_model.competencies.values_list('code', flat=True))
    out.actions = [x for x in out.actions if x.competency_code in valid]
    return log, out


def _formal_context(a):
    if a is None:
        return 'brak'
    return (f'{a.get_form_type_display()}; status: {a.get_status_display()}; '
            f'termin oceny: {a.due_date or a.window_to or "—"}; data rozmowy: {a.criteria_interview_date or "—"}')


def _history(conv, limit=10):
    msgs = list(conv.messages.order_by('-created_at')[:limit])[::-1]
    return [{'role': m.role, 'content': m.content} for m in msgs]


def chat(request, conv: Conversation, text: str):
    """Kolejna wymiana w rozmowie z asystentem. Zwraca zapisaną wiadomość asystenta."""
    a = conv.assessment
    anon = Pseudonymizer(a.employee) if a else (lambda t: t)
    question = anon(text)
    history = _history(conv)
    Message.objects.create(conversation=conv, role=Message.Role.USER, content=text)
    if not conv.title:
        conv.title = text[:120]
    conv.save()

    # Wyszukiwanie: najpierw samo bieżące pytanie. Poprzednie pytanie dołączamy tylko do dopytań,
    # które same mają jakiekolwiek dopasowanie w bazie (np. „A po ocenie negatywnej?”) — pytanie spoza
    # tematu nie może „pożyczyć” źródeł od poprzedniego.
    from django.conf import settings
    threshold = settings.ASSISTANT_MIN_RETRIEVAL_SCORE
    scored = search_scored(question, k=6)
    best = scored[0][0] if scored else 0.0
    prev_q = next((h['content'] for h in reversed(history) if h['role'] == 'user'), '')
    if prev_q and 0 < best < threshold:
        scored = search_scored(f'{question} {anon(prev_q)}', k=6)
        best = scored[0][0] if scored else 0.0
    picked = build_context(scored, question, settings.ASSISTANT_CONTEXT_CHARS)
    scored = [(sc, c) for sc, c, _ in picked]
    docs = [{'title': f'{c.title}' + (f', s. {c.page}' if c.kind not in ('FAQ', 'MODEL') else ''), 'text': text}
            for _, c, text in picked]

    if conv.mode == Conversation.Mode.FORMAL:
        if best < threshold:
            return Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT,
                                          content=prompts.NO_SOURCES_ANSWER, grounded=False)
        prompt = prompts.CHAT_FORMAL.format(context=_formal_context(a), question=question)
        if a is not None:
            prompt += f'\n\n{address_note(a)}'
        feature = 'chat_formal'
    else:
        if a is None:
            raise AssistantInputError('Tryb przygotowania do rozmowy wymaga wskazania oceny.')
        material = _assessment_material(a, anon)
        docs = [{'title': 'Materiał z oceny', 'text': material}] + [
            d for (s_, _), d in zip(scored, docs) if s_ >= threshold][:4]
        prompt = prompts.CHAT_INTERVIEW.format(question=question) + f'\n\n{address_note(a)}'
        feature = 'chat_interview'

    from apps.competencies.models import CompetencyModel
    model = a.competency_model if a else CompetencyModel.active_for(request.membership.institution)
    try:
        codes = [] if conv.mode == Conversation.Mode.FORMAL else _codes(a)
        result = get_provider().answer_with_citations(system=_system(model, codes, levels=False), prompt=prompt,
                                                      documents=docs,
                                                      history=history)
    except AssistantError as e:
        _log(request, a, feature, prompt, error=f'{type(e).__name__}: {e}')
        Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, grounded=False,
                               content=str(e) if e.args else e.public_message)
        raise
    log = _log(request, a, feature, prompt, result)
    grounded = bool(result.citations) or conv.mode == Conversation.Mode.INTERVIEW
    return Message.objects.create(
        conversation=conv, role=Message.Role.ASSISTANT, content=result.text, citations=result.citations,
        sources=[{'title': d['title']} for d in docs], grounded=grounded, interaction=log)
