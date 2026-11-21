"""Wyliczenia oceny — czyste funkcje, deterministyczne, zgodne z przepisami.

Wynik (pozytywna/negatywna) wynika wprost z przepisów i ocen cząstkowych przyznanych
przez przełożonego; AI nie uczestniczy w tych wyliczeniach.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

POSITIVE = 'POSITIVE'
NEGATIVE = 'NEGATIVE'

PERIODIC_LEVELS = {
    1: 'znacznie poniżej oczekiwań',
    2: 'poniżej oczekiwań',
    3: 'na poziomie oczekiwań',
    4: 'powyżej oczekiwań',
    5: 'znacznie powyżej oczekiwań',
}


@dataclass
class ScoreSummary:
    complete: bool
    average: Decimal | None = None
    level: int | None = None
    level_label: str = ''
    result: str | None = None
    reasons: list = field(default_factory=list)  # warunki niespełnione / uwagi

    def as_dict(self):
        return {
            'complete': self.complete,
            'average': str(self.average) if self.average is not None else None,
            'level': self.level,
            'level_label': self.level_label,
            'result': self.result,
            'reasons': self.reasons,
        }


def _average(scores):
    return Fraction(sum(scores), len(scores))


def _display(avg: Fraction) -> Decimal:
    return (Decimal(avg.numerator) / Decimal(avg.denominator)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def periodic_level(avg: Fraction) -> int:
    """§ 11 rozp. 2016: 1–2 / >2–4 / >4–6 / >6–8 / >8–9 pkt."""
    if avg <= 2:
        return 1
    if avg <= 4:
        return 2
    if avg <= 6:
        return 3
    if avg <= 8:
        return 4
    return 5


def periodic_summary(scores) -> ScoreSummary:
    if not scores or any(s is None for s in scores):
        return ScoreSummary(complete=False, reasons=['Nie wszystkie kryteria mają ocenę cząstkową.'])
    avg = _average(scores)
    level = periodic_level(avg)
    reasons = []
    if level < 3:
        reasons.append(f'Ogólny poziom spełnienia kryteriów: {PERIODIC_LEVELS[level]}.')
    if 1 in scores:
        reasons.append('Co najmniej jedna ocena cząstkowa na poziomie „znacznie poniżej oczekiwań”.')
    result = POSITIVE if not reasons else NEGATIVE
    return ScoreSummary(True, _display(avg), level, PERIODIC_LEVELS[level], result, reasons)


def first_summary(scores, *, exam_passed, report_on_time) -> ScoreSummary:
    """§ 10 rozp. 2015.

    exam_passed: True / False / None (nie dotyczy).
    report_on_time: True / False / None (jeszcze nie ustalono).
    """
    if not scores or any(s is None for s in scores):
        return ScoreSummary(complete=False, reasons=['Nie wszystkie elementy oceny mają ocenę cząstkową.'])
    avg = _average(scores)
    reasons = []
    if exam_passed is False:
        reasons.append('Oceniany nie zaliczył egzaminu ze służby przygotowawczej.')
    if report_on_time is False:
        reasons.append('Sprawozdanie nie zostało złożone w wyznaczonym terminie.')
    if scores.count(3) > 1:
        reasons.append('Więcej niż jedna ocena cząstkowa w wysokości 3 punktów.')
    if avg < 5:
        reasons.append('Ocena łączna niższa niż 5 punktów.')
    complete = report_on_time is not None
    if not complete:
        return ScoreSummary(False, _display(avg), reasons=reasons + ['Nie określono, czy sprawozdanie złożono w terminie.'])
    return ScoreSummary(True, _display(avg), None, '', POSITIVE if not reasons else NEGATIVE, reasons)


def suggest_points_from_indicator_levels(levels, form_config):
    """Podpowiedź (nie decyzja): punkty odpowiadające medianie poziomów wskaźników ocenionych przez przełożonego."""
    levels = sorted(lv for lv in levels if lv)
    if not levels:
        return None
    mid = levels[(len(levels) - 1) // 2]
    return form_config.points_for_model_level(mid)
