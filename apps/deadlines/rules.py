"""Terminy wynikające z przepisów (ustawa o służbie cywilnej, rozp. 2015 i 2016).

Funkcje zwracają podpowiedzi — przełożony zawsze może je zmienić (np. nieobecności, art. 81 ust. 7).
"""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


@dataclass
class FirstAssessmentDates:
    initial_interview_by: date      # § 3: 21 dni od nawiązania stosunku pracy
    report_from: date                # § 4 ust. 1: po upływie 8 miesięcy
    report_to: date
    window_from: date
    window_to: date                  # art. 38 ust. 1: nie później niż miesiąc przed końcem umowy


def first_assessment_dates(employment_date: date, contract_end: date | None = None) -> FirstAssessmentDates:
    report_from = add_months(employment_date, 8)
    report_to = report_from + timedelta(days=14)
    end = contract_end or (add_months(employment_date, 12) - timedelta(days=1))
    return FirstAssessmentDates(
        initial_interview_by=employment_date + timedelta(days=21),
        report_from=report_from,
        report_to=report_to,
        window_from=report_to,
        window_to=add_months(end, -1),
    )


def periodic_criteria_deadline(previous_assessment_date: date, previous_negative=False) -> date:
    """§ 7 rozp. 2016: 30 dni od poprzedniej oceny/zatrudnienia na czas nieokreślony; 7 dni po negatywnej."""
    return previous_assessment_date + timedelta(days=7 if previous_negative else 30)


def periodic_due_date(previous_assessment_date: date, *, previous_negative=False, acknowledged_on: date | None = None) -> date:
    """Art. 81 ust. 4 — co 24 miesiące; ust. 9 — po negatywnej: po upływie 6 miesięcy od zapoznania się."""
    if previous_negative:
        return add_months(acknowledged_on or previous_assessment_date, 6)
    return add_months(previous_assessment_date, 24)


def objection_deadline(acknowledged_on: date) -> date:
    """Art. 83 ust. 1 — sprzeciw w terminie 7 dni od dnia zapoznania się z oceną."""
    return acknowledged_on + timedelta(days=7)
