"""Konfiguracja arkuszy oceny wg rozporządzeń.

- Pierwsza ocena: rozp. PRM z 23.07.2015 (Dz.U. poz. 1144), § 2 i § 9.
- Ocena okresowa: rozp. PRM z 4.04.2016 (Dz.U. poz. 470), § 3–§ 5, § 11.
"""
from dataclasses import dataclass

from django.db import models

from apps.competencies import codes as c


class FormType(models.TextChoices):
    FIRST = 'FIRST', 'Pierwsza ocena w służbie cywilnej'
    PERIODIC_A = 'PERIODIC_A', 'Ocena okresowa — arkusz A (kierownik urzędu)'
    PERIODIC_B = 'PERIODIC_B', 'Ocena okresowa — arkusz B (kierujący pracownikami)'
    PERIODIC_C = 'PERIODIC_C', 'Ocena okresowa — arkusz C (pozostałe stanowiska)'


@dataclass(frozen=True)
class ScalePoint:
    points: int
    label: str
    model_levels: tuple  # poziomy (1–5) modelu kompetencji odpowiadające temu punktowi


PERIODIC_SCALE = (
    ScalePoint(1, 'Znacznie poniżej oczekiwań', (1,)),
    ScalePoint(3, 'Poniżej oczekiwań', (2,)),
    ScalePoint(5, 'Na poziomie oczekiwań', (3,)),
    ScalePoint(7, 'Powyżej oczekiwań', (4,)),
    ScalePoint(9, 'Znacznie powyżej oczekiwań', (5,)),
)

FIRST_SCALE = (
    ScalePoint(3, 'Poniżej oczekiwań', (1, 2)),
    ScalePoint(5, 'Na poziomie oczekiwań', (3,)),
    ScalePoint(7, 'Powyżej oczekiwań', (4, 5)),
)


@dataclass(frozen=True)
class FormConfig:
    form_type: str
    short_name: str
    mandatory: tuple
    scale: tuple
    max_additional: int
    is_first: bool = False

    @property
    def allowed_points(self):
        return {p.points for p in self.scale}

    def points_for_model_level(self, level):
        for p in self.scale:
            if level in p.model_levels:
                return p.points
        return None

    def label_for_points(self, points):
        return next((p.label for p in self.scale if p.points == points), '')


FORMS = {
    FormType.FIRST: FormConfig(
        FormType.FIRST, 'Arkusz pierwszej oceny',
        (c.RZETELNOSC, c.WIEDZA, c.ORGANIZACJA, c.KOMUNIKACJA, c.WSPOLPRACA),
        FIRST_SCALE, 0, is_first=True,
    ),
    FormType.PERIODIC_A: FormConfig(
        FormType.PERIODIC_A, 'Arkusz A',
        (c.LUDZMI, c.DECYZJE, c.ORGANIZACJA, c.WSPOLPRACA, c.KOMUNIKACJA, c.STRATEGICZNE),
        PERIODIC_SCALE, 3,
    ),
    FormType.PERIODIC_B: FormConfig(
        FormType.PERIODIC_B, 'Arkusz B',
        (c.LUDZMI, c.DECYZJE, c.ORGANIZACJA, c.WSPOLPRACA, c.KOMUNIKACJA),
        PERIODIC_SCALE, 3,
    ),
    FormType.PERIODIC_C: FormConfig(
        FormType.PERIODIC_C, 'Arkusz C',
        (c.WIEDZA, c.RZETELNOSC, c.ORGANIZACJA, c.WSPOLPRACA, c.KOMUNIKACJA),
        PERIODIC_SCALE, 3,
    ),
}


def get_form(form_type) -> FormConfig:
    return FORMS[FormType(form_type)]


def suggest_periodic_form(employee):
    """§ 3 rozp. 2016: A – kierownik urzędu, B – bezpośrednie kierowanie pracownikami, C – pozostali."""
    if employee.is_office_head:
        return FormType.PERIODIC_A
    jd = employee.job_descriptions.first()
    if employee.is_managerial or (jd is not None and jd.manages_people):
        return FormType.PERIODIC_B
    return FormType.PERIODIC_C
