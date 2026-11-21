"""Budowa bazy wiedzy: odczyt tekstu ze źródeł (PDF, DOCX, TXT/MD) i podział na fragmenty do wyszukiwania."""
import io
import re

from pypdf import PdfReader

from .models import KnowledgeDocument, LegalChunk, SourceKind

ALLOWED_EXT = ('.pdf', '.docx', '.txt', '.md')
MAX_UPLOAD = 20 * 1024 * 1024
CHUNK_CHARS = 6000          # limit fragmentu (strona PDF albo sekcja dokumentu tekstowego)
TEXT_CHUNK_TARGET = 3000    # docelowa długość sekcji dla DOCX/TXT

NOISE = re.compile(r'^(l|\.go|v\.p|w\.|rcl|ww|\d+)$')

# (prefiks nazwy pliku, tytuł źródła, rodzaj) — tytuły źródeł wbudowanych w docs_assets
KNOWN = [
    ('Ustawa o służbie cywilnej', 'Ustawa z 21.11.2008 o służbie cywilnej (t.j. Dz.U. 2026 poz. 590)', SourceKind.ACT),
    ('Rozporządzenie o ocenach okresowych z 2016 r. (4)', 'Rozporządzenie PRM z 4.04.2016 – zał. nr 1: wykaz kryteriów oceny',
     SourceKind.REGULATION),
    ('Rozporządzenie o ocenach okresowych', 'Rozporządzenie PRM z 4.04.2016 w sprawie ocen okresowych (Dz.U. poz. 470)',
     SourceKind.REGULATION),
    ('Poradnik - oceny okresowe', 'Poradnik KPRM – oceny okresowe w służbie cywilnej', SourceKind.GUIDE),
    ('Rozporządzenie o pierwszej ocenie', 'Rozporządzenie PRM z 23.07.2015 w sprawie pierwszej oceny (Dz.U. poz. 1144)',
     SourceKind.REGULATION),
    ('Pierwsza ocena w służbie cywilnej - poradnik', 'Poradnik KPRM – pierwsza ocena w służbie cywilnej (2016)',
     SourceKind.GUIDE),
]


class KnowledgeFileError(ValueError):
    pass


def clean(text):
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not NOISE.match(ln)]
    return re.sub(r'[ \t]+', ' ', '\n'.join(lines)).strip()


def classify(filename):
    """Tytuł i rodzaj źródła z nazwy pliku (dla plików bez opisu, np. z docs_assets)."""
    for prefix, title, kind in KNOWN:
        if filename.startswith(prefix):
            return title, kind
    stem = filename.rsplit('.', 1)[0]
    low = filename.lower()
    if 'ustaw' in low:
        return stem, SourceKind.ACT
    if 'rozporz' in low:
        return stem, SourceKind.REGULATION
    if 'poradnik' in low:
        return stem, SourceKind.GUIDE
    return stem, SourceKind.OTHER


def _group(paragraphs):
    """Łączy akapity w sekcje ~TEXT_CHUNK_TARGET znaków; numer sekcji pełni rolę „strony”."""
    out, buf, size = [], [], 0
    for p in paragraphs:
        if buf and size + len(p) > TEXT_CHUNK_TARGET:
            out.append('\n'.join(buf))
            buf, size = [], 0
        buf.append(p)
        size += len(p) + 1
    if buf:
        out.append('\n'.join(buf))
    return out


def extract_pages(filename, data: bytes):
    """Zwraca listę (numer strony/sekcji, tekst). Strony bez treści (np. okładki, skany) są pomijane."""
    low = filename.lower()
    if low.endswith('.pdf'):
        try:
            pages = [clean(p.extract_text() or '') for p in PdfReader(io.BytesIO(data)).pages]
        except Exception as e:  # noqa: BLE001 — uszkodzony lub zaszyfrowany plik
            raise KnowledgeFileError(f'Nie udało się odczytać PDF: {e}') from e
        return [(i, t[:CHUNK_CHARS]) for i, t in enumerate(pages, start=1) if len(t) >= 80]
    if low.endswith('.docx'):
        from docx import Document
        try:
            doc = Document(io.BytesIO(data))
        except Exception as e:  # noqa: BLE001
            raise KnowledgeFileError(f'Nie udało się odczytać DOCX: {e}') from e
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    paras.append(' | '.join(dict.fromkeys(cells)))
    elif low.endswith(('.txt', '.md')):
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = data.decode('cp1250', errors='replace')
        paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    else:
        raise KnowledgeFileError('Obsługiwane formaty: PDF, DOCX, TXT, MD.')
    return [(i, t[:CHUNK_CHARS]) for i, t in enumerate(_group(paras), start=1) if len(t) >= 80]


def index_document(doc: KnowledgeDocument, data: bytes) -> int:
    """(Prze)buduje fragmenty jednego źródła. Zwraca liczbę fragmentów."""
    pages = extract_pages(doc.source, data)
    doc.chunks.all().delete()
    LegalChunk.objects.bulk_create(
        LegalChunk(document=doc, kind=doc.kind, source=doc.source, title=doc.title, page=page, text=text)
        for page, text in pages)
    return len(pages)
