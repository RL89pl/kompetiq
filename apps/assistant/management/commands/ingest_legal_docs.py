import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assistant.knowledge import classify, index_document
from apps.assistant.models import KnowledgeDocument, LegalChunk, SourceKind
from apps.competencies.models import CompetencyModel

# Pliki, które nie są bazą wiedzy (np. regulamin wyzwania)
EXCLUDE = ('cd955907',)
FAQ_FILE = Path(__file__).resolve().parents[2] / 'knowledge' / 'faq.json'
LEVEL_LABELS = {1: 'znacznie poniżej', 2: 'poniżej', 3: 'na poziomie', 4: 'powyżej', 5: 'znacznie powyżej'}


def builtin(source, title, kind):
    """Źródło wbudowane — zachowuje ID między przebudowami, więc wyłączenia w urzędach nie giną."""
    doc, _ = KnowledgeDocument.objects.update_or_create(
        institution=None, builtin=True, source=source, defaults={'title': title, 'kind': kind})
    return doc


def replace_chunks(doc, rows):
    doc.chunks.all().delete()
    LegalChunk.objects.bulk_create(LegalChunk(document=doc, kind=doc.kind, source=doc.source, **r) for r in rows)
    return len(rows)


class Command(BaseCommand):
    help = ('Przebudowuje wbudowaną część bazy wiedzy asystenta: wszystkie PDF z docs_assets (ustawa, rozporządzenia, '
            'poradniki), model kompetencji oraz zestaw pytań i odpowiedzi. Źródeł dodanych przez urzędy w panelu '
            '„Baza wiedzy” nie zmienia.')

    def add_arguments(self, parser):
        parser.add_argument('--dir', default=str(settings.LEGAL_DOCS_DIR))

    @transaction.atomic
    def handle(self, dir, **opts):
        LegalChunk.objects.filter(document__isnull=True).delete()  # fragmenty sprzed wprowadzenia źródeł
        seen = set()
        total = 0
        for pdf in sorted(Path(dir).rglob('*.pdf')):
            if any(x in pdf.name for x in EXCLUDE):
                continue
            title, kind = classify(pdf.name)
            doc = builtin(pdf.name, title, kind)
            n = index_document(doc, pdf.read_bytes())
            seen.add(doc.id)
            total += n
            self.stdout.write(f'{title}: {n} stron')

        model = CompetencyModel.objects.filter(institution__isnull=True, is_active=True).first()
        if model:
            doc = builtin('Model_kompetencji.xlsx', f'Model kompetencji {model.version}', SourceKind.MODEL)
            rows = [{'title': 'Model kompetencji – wskazówki', 'page': 0, 'text': model.guidance}]
            for comp in model.competencies.prefetch_related('indicators__levels'):
                lines = [f'Kompetencja: {comp.name}']
                for ind in comp.indicators.all():
                    lines.append(f'Wskaźnik: {ind.text}')
                    lines += [f'  {lv.level} ({LEVEL_LABELS[lv.level]} oczekiwań): {lv.text}' for lv in ind.levels.all()]
                rows.append({'title': f'Model kompetencji – {comp.name}', 'page': comp.order, 'text': '\n'.join(lines)})
            n = replace_chunks(doc, rows)
            seen.add(doc.id)
            total += n
            self.stdout.write(f'Model kompetencji: {n} fragmentów')

        faq = json.loads(FAQ_FILE.read_text(encoding='utf-8'))
        doc = builtin('faq.json', 'Pytania i odpowiedzi', SourceKind.FAQ)
        n = replace_chunks(doc, [
            {'title': f'Pytania i odpowiedzi: {x["q"]}', 'page': i,
             'text': f'Pytanie: {x["q"]}\nOdpowiedź: {x["a"]}\nPodstawa: {x["basis"]}'}
            for i, x in enumerate(faq, start=1)])
        seen.add(doc.id)
        total += n
        self.stdout.write(f'Pytania i odpowiedzi: {n}')

        gone = KnowledgeDocument.objects.filter(builtin=True).exclude(id__in=seen)
        if gone.exists():
            self.stdout.write(f'Usunięto źródła, których nie ma już w docs_assets: {", ".join(gone.values_list("source", flat=True))}')
            gone.delete()
        if not LegalChunk.objects.filter(kind=SourceKind.ACT).exists():
            self.stdout.write(self.style.WARNING(
                'Brak ustawy o służbie cywilnej w bazie wiedzy — dodaj PDF z „ustaw” w nazwie do docs_assets.'))
        self.stdout.write(self.style.SUCCESS(f'Zaindeksowano {total} fragmentów.'))
