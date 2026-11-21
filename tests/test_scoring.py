from fractions import Fraction

import pytest

from apps.assessments import scoring
from apps.assessments.forms_config import FORMS, FormType
from apps.deadlines import rules
from datetime import date


@pytest.mark.parametrize('avg,level', [
    (Fraction(1), 1), (Fraction(2), 1), (Fraction(201, 100), 2), (Fraction(4), 2), (Fraction(401, 100), 3),
    (Fraction(6), 3), (Fraction(7), 4), (Fraction(8), 4), (Fraction(81, 10), 5), (Fraction(9), 5),
])
def test_periodic_level_thresholds(avg, level):
    assert scoring.periodic_level(avg) == level


def test_periodic_positive():
    s = scoring.periodic_summary([5, 5, 7, 5, 3])
    assert s.complete and s.result == scoring.POSITIVE and str(s.average) == '5.00' and s.level == 3


def test_periodic_negative_due_to_one_point_even_with_good_average():
    s = scoring.periodic_summary([9, 9, 9, 9, 1])
    assert s.level == 4 and s.result == scoring.NEGATIVE


def test_periodic_negative_level_below():
    s = scoring.periodic_summary([3, 3, 5, 3, 5])  # 3.8
    assert s.level == 2 and s.result == scoring.NEGATIVE


def test_periodic_incomplete():
    assert not scoring.periodic_summary([5, None]).complete


def test_first_positive_and_conditions():
    assert scoring.first_summary([5, 5, 5, 3, 7], exam_passed=True, report_on_time=True).result == scoring.POSITIVE
    assert scoring.first_summary([5, 5, 5, 3, 7], exam_passed=None, report_on_time=True).result == scoring.POSITIVE
    assert scoring.first_summary([7, 7, 7, 3, 3], exam_passed=True, report_on_time=True).result == scoring.NEGATIVE
    assert scoring.first_summary([5, 5, 5, 5, 3], exam_passed=True, report_on_time=True).result == scoring.NEGATIVE  # 4.6
    assert scoring.first_summary([7] * 5, exam_passed=False, report_on_time=True).result == scoring.NEGATIVE
    assert scoring.first_summary([7] * 5, exam_passed=True, report_on_time=False).result == scoring.NEGATIVE


def test_form_config():
    c = FORMS[FormType.PERIODIC_C]
    assert c.allowed_points == {1, 3, 5, 7, 9} and c.max_additional == 3
    f = FORMS[FormType.FIRST]
    assert f.allowed_points == {3, 5, 7} and f.points_for_model_level(2) == 3 and f.points_for_model_level(5) == 7
    assert scoring.suggest_points_from_indicator_levels([3, 4, 5], c) == 7
    assert scoring.suggest_points_from_indicator_levels([], c) is None


def test_deadlines():
    d = rules.first_assessment_dates(date(2026, 1, 31))
    assert d.initial_interview_by == date(2026, 2, 21)
    assert d.report_from == date(2026, 9, 30)
    assert d.window_to == date(2026, 12, 30)
    assert rules.periodic_due_date(date(2026, 3, 1)) == date(2028, 3, 1)
    assert rules.periodic_due_date(date(2026, 3, 1), previous_negative=True, acknowledged_on=date(2026, 3, 5)) == date(2026, 9, 5)
    assert rules.objection_deadline(date(2026, 3, 5)) == date(2026, 3, 12)
    assert rules.periodic_criteria_deadline(date(2026, 3, 1), previous_negative=True) == date(2026, 3, 8)
