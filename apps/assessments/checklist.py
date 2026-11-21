"""Deterministyczna lista kontrolna wymogów formalnych (bez AI)."""
from datetime import date

from apps.deadlines import rules

from .forms_config import suggest_periodic_form
from .models import Result, Status


def item(key, label, ok, basis, hint='', severity='error'):
    return {'key': key, 'label': label, 'ok': bool(ok), 'basis': basis, 'hint': hint,
            'severity': 'ok' if ok else severity}


def build_checklist(a, today=None):
    today = today or date.today()
    items = []
    emp = a.employee
    if a.is_first:
        if emp.employment_date:
            limit = rules.first_assessment_dates(emp.employment_date, emp.contract_end_date).initial_interview_by
            items.append(item(
                'initial_interview', 'Rozmowa wstępna w ciągu 21 dni od nawiązania stosunku pracy',
                a.criteria_interview_date and a.criteria_interview_date <= limit,
                '§ 3 rozp. z 23.07.2015', f'Termin: {limit:%d.%m.%Y}',
                severity='warning' if a.criteria_interview_date else 'error'))
            min_report = rules.add_months(emp.employment_date, 8)
            items.append(item(
                'report_deadline', 'Termin sprawozdania po upływie 8 miesięcy od zatrudnienia',
                a.report_deadline_from and a.report_deadline_from >= min_report,
                '§ 4 ust. 1 rozp. z 23.07.2015', f'Najwcześniej: {min_report:%d.%m.%Y}'))
        else:
            items.append(item('employment_date', 'Data nawiązania stosunku pracy w danych pracownika', False,
                              'arkusz pierwszej oceny, cz. I'))
        items.append(item('window', 'Okres dokonania pierwszej oceny wpisany do arkusza',
                          a.window_from and a.window_to, '§ 4 ust. 2 pkt 3 rozp. z 23.07.2015'))
        if a.status in (Status.INTERVIEW_DONE, Status.FINALIZED):
            items.append(item('exam', 'Informacja o egzaminie ze służby przygotowawczej', a.prep_exam,
                              '§ 10 ust. 1 pkt 1 i ust. 3 rozp. z 23.07.2015'))
            items.append(item('report', 'Informacja, czy sprawozdanie złożono w terminie',
                              a.report_on_time is not None, '§ 10 ust. 1 pkt 2 rozp. z 23.07.2015'))
        if a.window_to and a.status not in (Status.FINALIZED, Status.APPROVED, Status.ACKNOWLEDGED):
            days = (a.window_to - today).days
            early = bool(a.window_from and today < a.window_from)
            if days < 0:
                hint, severity = 'Termin minął', 'error'
            elif early:
                # Przed początkiem okresu ustalonego na rozmowie wstępnej — sygnał, nie blokada (np. przejście demonstracyjne).
                hint, severity = (f'Okres na dokonanie oceny zaczyna się {a.window_from:%d.%m.%Y}; '
                                  'ocena dokonana wcześniej odbiega od terminu przekazanego ocenianemu'), 'warning'
            else:
                hint, severity = f'Pozostało dni: {days}', 'error'
            items.append(item('window_left', 'Ocena dokonana w wyznaczonym okresie', days >= 0 and not early,
                              'art. 38 ust. 1 ustawy; § 4 ust. 2 pkt 3 rozp. z 23.07.2015', hint, severity=severity))
    else:
        suggested = suggest_periodic_form(emp)
        items.append(item('form', 'Arkusz właściwy dla stanowiska', a.form_type == suggested,
                          '§ 3 rozp. z 4.04.2016',
                          '' if a.form_type == suggested else f'Dane pracownika wskazują: {suggested}',
                          severity='warning'))
        n_add = a.criteria.filter(is_mandatory=False).count()
        items.append(item('additional', f'Kryteria dodatkowe: {n_add} (maks. 3)', n_add <= 3, '§ 5 ust. 2 rozp. z 4.04.2016'))
        items.append(item('criteria_interview', 'Rozmowa o obowiązkach, kryteriach i oczekiwaniach przeprowadzona',
                          a.criteria_interview_date, '§ 5 ust. 1 i § 7 rozp. z 4.04.2016'))
        items.append(item('due_date', 'Termin sporządzenia oceny wpisany do części I', a.due_date,
                          '§ 5 ust. 3 rozp. z 4.04.2016'))
        if a.due_date and a.status not in (Status.FINALIZED, Status.ACKNOWLEDGED):
            days = (a.due_date - today).days
            items.append(item('due_left', 'Ocena sporządzona w terminie', days >= 0, 'art. 81 ust. 4 ustawy',
                              f'Pozostało dni: {days}' if days >= 0 else 'Termin minął',
                              severity='warning' if days >= 0 else 'error'))
    if a.status in (Status.INTERVIEW_DONE, Status.FINALIZED, Status.APPROVED, Status.ACKNOWLEDGED):
        items.append(item('evaluation_interview', 'Rozmowa oceniająca przeprowadzona przed sporządzeniem oceny',
                          a.evaluation_interview_date,
                          '§ 8 rozp. z 23.07.2015' if a.is_first else '§ 10 rozp. z 4.04.2016'))
    scored = [c for c in a.criteria.all()]
    missing_ev = [c.competency.name for c in scored if c.score is not None and not c.evidence.exists()]
    items.append(item('evidence', 'Oceny cząstkowe oparte na udokumentowanych przykładach zachowań',
                      not missing_ev, 'model kompetencji — wskazówki stosowania',
                      ('Brak przykładów: ' + ', '.join(missing_ev)) if missing_ev else '', severity='warning'))
    summary = a.summary()
    if summary.complete and summary.result == Result.NEGATIVE:
        items.append(item('justification', 'Uzasadnienie oceny negatywnej', a.justification.strip(),
                          '§ 10 ust. 4 rozp. z 23.07.2015' if a.is_first else '§ 11 ust. 3 rozp. z 4.04.2016'))
    if a.acknowledged_on and not a.is_first:
        dl = rules.objection_deadline(a.acknowledged_on)
        items.append(item('objection', f'Termin na sprzeciw do dyrektora generalnego: {dl:%d.%m.%Y}', True,
                          'art. 83 ust. 1 ustawy', severity='info'))
    return items
