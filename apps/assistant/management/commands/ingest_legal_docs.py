import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from pypdf import PdfReader

from apps.assistant.models import LegalChunk
from apps.competencies.models import CompetencyModel

Kind = LegalChunk.Kind

# (prefiks nazwy pliku, tytuł źródła, rodzaj)
KNOWN = [
    ('Ustawa o służbie cywilnej', 'Ustawa z 21.11.2008 o służbie cywilnej (t.j. Dz.U. 2026 poz. 590)', Kind.ACT),
    ('Rozporządzenie o ocenach okresowych z 2016 r. (4)', 'Rozporządzenie PRM z 4.04.2016 – zał. nr 1: wykaz kryteriów oceny', Kind.REGULATION),
    ('Rozporządzenie o ocenach okresowych', 'Rozporządzenie PRM z 4.04.2016 w sprawie ocen okresowych (Dz.U. poz. 470)', Kind.REGULATION),
    ('Poradnik - oceny okresowe', 'Poradnik KPRM – oceny okresowe w służbie cywilnej', Kind.GUIDE),
    ('Rozporządzenie o pierwszej ocenie', 'Rozporządzenie PRM z 23.07.2015 w sprawie pierwszej oceny (Dz.U. poz. 1144)', Kind.REGULATION),
    ('Pierwsza ocena w służbie cywilnej - poradnik', 'Poradnik KPRM – pierwsza ocena w służbie cywilnej (2016)', Kind.GUIDE),
]
# Pliki, które nie są bazą wiedzy (np. regulamin wyzwania)
EXCLUDE = ('cd955907',)
NOISE = re.compile(r'^(l|\.go|v\.p|w\.|rcl|ww|\d+)$')
FAQ_FILE = Path(__file__).resolve().parents[2] / 'knowledge' / 'faq.json'


def clean(text):
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not NOISE.match(ln)]
    return re.sub(r'[ \t]+', ' ', '\n'.join(lines)).strip()


def classify(pdf: Path):
    for prefix, title, kind in KNOWN:
        if pdf.name.startswith(prefix):
            return title, kind
    low = pdf.name.lower()
    if 'ustaw' in low:
        return 'Ustawa z 21.11.2008 o służbie cywilnej', Kind.ACT
    if 'rozporz' in low:
        return pdf.stem, Kind.REGULATION
    if 'poradnik' in low:
        return pdf.stem, Kind.GUIDE
    return pdf.stem, Kind.OTHER


class Command(BaseCommand):
    help = ('Buduje bazę wiedzy asystenta: wszystkie PDF z docs_assets (ustawa, rozporządzenia, poradniki), '
            'model kompetencji oraz zestaw pytań i odpowiedzi.')

    def add_arguments(self, parser):
        parser.add_argument('--dir', default=str(settings.LEGAL_DOCS_DIR))

    def handle(self, dir, **opts):
        LegalChunk.objects.all().delete()
        total = 0
        for pdf in sorted(Path(dir).rglob('*.pdf')):
            if any(x in pdf.name for x in EXCLUDE):
                continue
            title, kind = classify(pdf)
            rows = []
            for i, page in enumerate(PdfReader(str(pdf)).pages, start=1):
                text = clean(page.extract_text() or '')
                if len(text) >= 80:
                    rows.append(LegalChunk(kind=kind, source=pdf.name, title=title, page=i, text=text[:6000]))
            LegalChunk.objects.bulk_create(rows)
            total += len(rows)
            self.stdout.write(f'{title}: {len(rows)} stron')
        if not LegalChunk.objects.filter(kind=Kind.ACT).exists():
            self.stdout.write(self.style.WARNING(
                'Brak ustawy o służbie cywilnej w bazie wiedzy — dodaj PDF z „ustaw” w nazwie do docs_assets.'))

        model = CompetencyModel.objects.filter(institution__isnull=True, is_active=True).first()
        if model:
            labels = {1: 'znacznie poniżej', 2: 'poniżej', 3: 'na poziomie', 4: 'powyżej', 5: 'znacznie powyżej'}
            rows = [LegalChunk(kind=Kind.MODEL, source='Model_kompetencji.xlsx', title='Model kompetencji – wskazówki',
                               page=0, text=model.guidance)]
            for comp in model.competencies.prefetch_related('indicators__levels'):
                lines = [f'Kompetencja: {comp.name}']
                for ind in comp.indicators.all():
                    lines.append(f'Wskaźnik: {ind.text}')
                    lines += [f'  {lv.level} ({labels[lv.level]} oczekiwań): {lv.text}' for lv in ind.levels.all()]
                rows.append(LegalChunk(kind=Kind.MODEL, source='Model_kompetencji.xlsx',
                                       title=f'Model kompetencji – {comp.name}', page=comp.order, text='\n'.join(lines)))
            LegalChunk.objects.bulk_create(rows)
            total += len(rows)
            self.stdout.write(f'Model kompetencji: {len(rows)} fragmentów')

        faq = json.loads(FAQ_FILE.read_text(encoding='utf-8'))
        LegalChunk.objects.bulk_create(
            LegalChunk(kind=Kind.FAQ, source='faq.json', title=f'Pytania i odpowiedzi: {x["q"]}', page=i,
                       text=f'Pytanie: {x["q"]}\nOdpowiedź: {x["a"]}\nPodstawa: {x["basis"]}')
            for i, x in enumerate(faq, start=1))
        total += len(faq)
        self.stdout.write(f'Pytania i odpowiedzi: {len(faq)}')
        self.stdout.write(self.style.SUCCESS(f'Zaindeksowano {total} fragmentów.'))
