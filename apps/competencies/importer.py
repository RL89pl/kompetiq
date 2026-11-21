"""Import modelu kompetencji z pliku Model_kompetencji.xlsx.

Układ pliku: arkusz-indeks „Model kompetencji” (wskazówki w A4:A6, lista kompetencji od wiersza 9)
oraz po jednym arkuszu na kompetencję: A1 = nazwa, wiersz 3 = nagłówki,
od wiersza 4: A = wskaźnik, B..F = opisy poziomów 1..5.
Nazwy arkuszy bywają obcięte/niezgodne, więc kompetencję rozpoznajemy po A1.
"""
from dataclasses import dataclass, field

import openpyxl
from django.db import transaction

from .codes import NAME_TO_CODE
from .models import BehavioralIndicator, Competency, CompetencyModel, IndicatorLevelDescription


class ImportError_(Exception):
    pass


@dataclass
class ParsedIndicator:
    text: str
    levels: list


@dataclass
class ParsedCompetency:
    name: str
    code: str
    order: int
    indicators: list = field(default_factory=list)


def _clean(v):
    return ' '.join(str(v).split()) if v is not None else ''


def parse_workbook(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    index = wb.worksheets[0]
    guidance = [_clean(index[f'A{r}'].value) for r in (4, 5, 6)]
    order_by_name = {}
    for row in index.iter_rows(min_row=9, values_only=True):
        if row and isinstance(row[0], (int, float)) and row[1]:
            order_by_name[_clean(row[1]).upper()] = (int(row[0]), int(row[2] or 0))

    competencies = []
    for ws in wb.worksheets[1:]:
        name = _clean(ws['A1'].value)
        key = name.upper()
        code = NAME_TO_CODE.get(key)
        if not code:
            raise ImportError_(f'Nieznana kompetencja w arkuszu „{ws.title}”: {name!r}')
        order, expected = order_by_name.get(key, (len(competencies) + 1, None))
        comp = ParsedCompetency(name=name, code=code, order=order)
        for row in ws.iter_rows(min_row=4, values_only=True):
            if not row or not row[0]:
                continue
            levels = [_clean(c) for c in row[1:6]]
            if len(levels) != 5 or not all(levels):
                raise ImportError_(f'{name}: wskaźnik bez kompletu 5 poziomów: {_clean(row[0])[:60]}')
            comp.indicators.append(ParsedIndicator(text=_clean(row[0]), levels=levels))
        if expected is not None and expected != len(comp.indicators):
            raise ImportError_(f'{name}: oczekiwano {expected} wskaźników, jest {len(comp.indicators)}')
        competencies.append(comp)
    competencies.sort(key=lambda c: c.order)
    return '\n'.join(g for g in guidance if g), competencies


@transaction.atomic
def import_model(path, *, name='Model kompetencji służby cywilnej', version='1.0', institution=None, replace=False):
    guidance, comps = parse_workbook(path)
    existing = CompetencyModel.objects.filter(institution=institution, version=version, name=name)
    if existing.exists():
        if not replace:
            raise ImportError_(f'Model {name} {version} już istnieje (użyj --replace).')
        existing.delete()
    CompetencyModel.objects.filter(institution=institution).update(is_active=False)
    model = CompetencyModel.objects.create(name=name, version=version, institution=institution,
                                           guidance=guidance, is_active=True)
    for c in comps:
        comp = Competency.objects.create(model=model, code=c.code, name=c.name.capitalize(), order=c.order)
        for i, ind in enumerate(c.indicators, start=1):
            bi = BehavioralIndicator.objects.create(competency=comp, text=ind.text, order=i)
            IndicatorLevelDescription.objects.bulk_create(
                IndicatorLevelDescription(indicator=bi, level=lvl, text=t)
                for lvl, t in enumerate(ind.levels, start=1)
            )
    return model
