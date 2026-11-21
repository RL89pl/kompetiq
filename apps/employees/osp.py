"""Import opisu stanowiska pracy (OSP) z pliku .docx w standardowym układzie służby cywilnej.

Odczytuje: nazwę i symbol stanowiska, komórkę, cel istnienia stanowiska, liczbę podległych pracowników
(→ czy stanowisko polega na kierowaniu pracownikami, § 3 rozp. 2016), zadania, upoważnienia oraz
„Kompetencje miękkie” (→ kody kompetencji z modelu: podpowiedź kryteriów dodatkowych).
Przetwarzanie lokalne, bez AI.
"""
import io
import re
from dataclasses import dataclass, field

from docx import Document
from docx.oxml.ns import qn

CHECKED = '☒'
SECTION_ENDS = {
    'purpose': ('LICZBA PODLEGŁYCH PRACOWNIKÓW',),
    'tasks': ('UPOWAŻNIENIA I PEŁNOMOCNICTWA',),
    'soft': ('DOŚWIADCZENIE ZAWODOWE',),
}


@dataclass
class ParsedOSP:
    position: str = ''
    symbol: str = ''
    unit: str = ''
    purpose: str = ''
    subordinates: str = ''
    manages_people: bool = False
    tasks: list = field(default_factory=list)
    authorizations: list = field(default_factory=list)
    soft_competencies: list = field(default_factory=list)  # nazwy z dokumentu
    raw_text: str = ''


def _paragraphs(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    out = []
    for p in doc.element.body.iter(qn('w:p')):
        text = ''.join(t.text or '' for t in p.iter(qn('w:t'))).strip()
        if text:
            out.append(' '.join(text.split()))
    return out


def _after(lines, label, n=1):
    for i, ln in enumerate(lines):
        if ln.upper().startswith(label):
            return lines[i + 1:i + 1 + n]
    return []


def _between(lines, start, ends):
    out, on = [], False
    for ln in lines:
        if on and any(ln.upper().startswith(e) for e in ends):
            break
        if on:
            out.append(ln)
        if ln.upper().startswith(start):
            on = True
    return out


def parse_osp(file_bytes) -> ParsedOSP:
    lines = _paragraphs(file_bytes)
    if not any('OPIS STANOWISKA PRACY' in ln.upper() for ln in lines[:5]):
        raise ValueError('Plik nie wygląda na opis stanowiska pracy (brak nagłówka „OPIS STANOWISKA PRACY”).')
    r = ParsedOSP(raw_text='\n'.join(lines))
    r.position = (_after(lines, 'NAZWA STANOWISKA PRACY') or [''])[0]
    sym = _after(lines, 'SYMBOL STANOWISKA PRACY')
    r.symbol = sym[0] if sym else ''
    r.unit = ' / '.join(_between(lines, 'NAZWA KOMÓRKI ORGANIZACYJNEJ', ('NAZWA STANOWISKA PRACY',)))
    r.purpose = '\n'.join(_between(lines, 'CEL ISTNIENIA STANOWISKA PRACY', SECTION_ENDS['purpose']))
    subs = _between(lines, 'LICZBA PODLEGŁYCH PRACOWNIKÓW', ('GŁÓWNE ZADANIA',))
    chosen = [s.lstrip(CHECKED).strip() for s in subs if s.startswith(CHECKED)]
    r.subordinates = chosen[0] if chosen else ''
    r.manages_people = bool(chosen) and not chosen[0].lower().startswith('brak')
    tasks = _between(lines, 'GŁÓWNE ZADANIA REALIZOWANE', SECTION_ENDS['tasks'])
    r.tasks = [t for t in tasks if re.match(r'^Zadanie\s*\d+', t, re.I)]
    auth = _between(lines, 'UPOWAŻNIENIA I PEŁNOMOCNICTWA', ('ZŁOŻONOŚĆ',))
    r.authorizations = [a.lstrip(CHECKED).strip() for a in auth if a.startswith(CHECKED)]
    soft = _between(lines, 'KOMPETENCJE MIĘKKIE', SECTION_ENDS['soft'])
    names = []
    for chunk in soft:
        names += [x.strip(' .;:-') for x in re.split(r'[,;\n]', chunk)]
    r.soft_competencies = [n for n in names if n]
    return r


def _norm(s):
    return re.sub(r'\s+', ' ', s.lower().replace('/', ' ')).strip()


def map_competencies(names, model):
    """Nazwy kompetencji z OSP → kody modelu (dopasowanie po początku nazwy)."""
    comps = [(c.code, _norm(c.name)) for c in model.competencies.all()]
    codes = []
    for n in names:
        nn = _norm(n)
        for code, cname in comps:
            if nn and (cname.startswith(nn[:18]) or nn.startswith(cname[:18])) and code not in codes:
                codes.append(code)
    return codes
