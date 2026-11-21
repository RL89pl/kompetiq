"""Eksport arkuszy oceny do PDF i DOCX.

Arkusze odwzorowują 1:1 wzory z załączników do rozporządzeń:
- arkusz pierwszej oceny: zał. nr 2 do rozp. PRM z 23 lipca 2015 r. (Dz. U. poz. 1144),
- arkusze A, B, C: zał. nr 2–4 do rozp. PRM z 4 kwietnia 2016 r. (Dz. U. poz. 470),
łącznie z numeracją przypisów, ich treścią i polami podpisów. W tekstach znacznik `{n}` oznacza odwołanie do przypisu n.
"""
import io
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm, Pt

from apps.assessments.forms_config import FormType
from apps.assessments.models import ExamStatus, Result

ANNEX = {FormType.FIRST: 'Załącznik nr 2', FormType.PERIODIC_A: 'Załącznik nr 2',
         FormType.PERIODIC_B: 'Załącznik nr 3', FormType.PERIODIC_C: 'Załącznik nr 4'}
DOTS = '………………………………'
DATE_HINT = '(dd.mm.rrrr)'
_MARK = re.compile(r'\{(\d+)\}')


def d(v, empty=DATE_HINT):
    return v.strftime('%d.%m.%Y') if v else empty


def num(v):
    return '' if v is None else str(v).replace('.', ',')


def person(user):
    if not user:
        return ('', '', '', '')
    m = user.memberships.first()
    return (user.first_name, user.last_name, (m.org_unit.name if m and m.org_unit else ''), (m.position if m else ''))


def full_name(user):
    return user.get_full_name() if user else ''


def _x(cond):
    return 'X' if cond else ''


# ---------------------------------------------------------------- DOCX

class Sheet:
    """Arkusz DOCX (wersja edytowalna)."""

    def __init__(self):
        self.doc = Document()
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Mm(210), Mm(297)
        sec.left_margin = sec.right_margin = Mm(15)
        sec.top_margin, sec.bottom_margin = Mm(15), Mm(18)
        st = self.doc.styles['Normal']
        st.font.name = 'Times New Roman'
        st.font.size = Pt(10)
        st.paragraph_format.space_after = Pt(2)

    @staticmethod
    def _fill(par, text, bold=False, size=None):
        for i, part in enumerate(_MARK.split('' if text is None else str(text))):
            if not part:
                continue
            run = par.add_run(f'{part})' if i % 2 else part)
            run.bold = bold
            if i % 2:
                run.font.superscript = True
            if size:
                run.font.size = Pt(size)

    def p(self, text='', bold=False, align=None, size=None):
        par = self.doc.add_paragraph()
        self._fill(par, text, bold, size)
        if align:
            par.alignment = align
        return par

    def heading(self, text):
        self.p(text, bold=True, size=10.5)

    def table(self, rows, widths=None, bold_rows=(), spans=(), grid=True, min_height=None, small_rows=(),
              center_cols=()):
        ncol = max(len(r) for r in rows)
        t = self.doc.add_table(rows=len(rows), cols=ncol)
        if grid:
            t.style = 'Table Grid'
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j in range(ncol):
                val = row[j] if j < len(row) else ''
                cell = t.cell(i, j)
                if widths:
                    cell.width = Mm(180 * widths[j])
                par = cell.paragraphs[0]
                self._fill(par, val, bold=i in bold_rows, size=7.5 if i in small_rows else None)
                if j in center_cols and i not in bold_rows:
                    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r0, c0, r1, c1 in spans:
            t.cell(r0, c0).merge(t.cell(r1, c1))
        if min_height:
            t.rows[-1].height = Mm(min_height)
        self.doc.add_paragraph()
        return t

    def kv(self, title, pairs):
        if title:
            self.heading(title)
        self.table([[k, v] for k, v in pairs], widths=[0.42, 0.58])

    def box(self, title, text, height=40):
        self.table([[title], [text or '']], bold_rows=(0,), min_height=None if text else height)

    def signature(self, labels, values=None):
        values = values or [None] * len(labels)
        self.table([[v or DOTS for v in values], labels], grid=False, small_rows=(1,),
                   widths=[1 / len(labels)] * len(labels))

    def footnotes(self, notes):
        self.p('______________________', size=7.5)
        for n in sorted(notes):
            self.p(f'{n}) {notes[n]}', size=7.5)

    def page_break(self):
        self.doc.add_page_break()

    def bytes(self):
        buf = io.BytesIO()
        self.doc.save(buf)
        return buf.getvalue()


# ---------------------------------------------------------------- PDF

def _find_fonts():
    import os
    candidates = [
        (os.environ.get('PDF_FONT_REGULAR', ''), os.environ.get('PDF_FONT_BOLD', '')),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'),
        ('/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
    ]
    for reg, bold in candidates:
        if reg and bold and os.path.exists(reg) and os.path.exists(bold):
            return reg, bold
    raise RuntimeError('Brak czcionki TTF z polskimi znakami do PDF (zainstaluj fonts-dejavu-core lub ustaw PDF_FONT_REGULAR/PDF_FONT_BOLD).')


_FONTS_READY = False


def _register_fonts():
    global _FONTS_READY
    if _FONTS_READY:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    reg, bold = _find_fonts()
    pdfmetrics.registerFont(TTFont('Kompas', reg))
    pdfmetrics.registerFont(TTFont('Kompas-Bold', bold))
    from reportlab.lib.fonts import addMapping
    addMapping('Kompas', 0, 0, 'Kompas')
    addMapping('Kompas', 1, 0, 'Kompas-Bold')
    _FONTS_READY = True


class PdfSheet:
    """Ten sam interfejs co Sheet (DOCX), renderowany przez reportlab do PDF (A4)."""

    def __init__(self, footer_text='Wygenerowano w aplikacji KompetIQ'):
        from reportlab.lib.styles import ParagraphStyle
        _register_fonts()
        self.footer_text = footer_text
        self.story = []
        self.base = ParagraphStyle('base', fontName='Kompas', fontSize=9.5, leading=12.5, spaceAfter=3)
        self.cell = ParagraphStyle('cell', parent=self.base, fontSize=9, leading=11.5, spaceAfter=0)
        self.cell_bold = ParagraphStyle('cellb', parent=self.cell, fontName='Kompas-Bold')
        self.cell_small = ParagraphStyle('cells', parent=self.cell, fontSize=7, leading=8.5)
        self.cell_center = ParagraphStyle('cellc', parent=self.cell, alignment=1)
        self.note = ParagraphStyle('note', parent=self.base, fontSize=7, leading=8.6, spaceAfter=1)

    @staticmethod
    def _esc(text):
        from xml.sax.saxutils import escape
        out = escape('' if text is None else str(text)).replace('\n', '<br/>')
        return _MARK.sub(r'<super rise="3" size="6">\1)</super>', out)

    def p(self, text='', bold=False, align=None, size=None):
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Paragraph
        al = {WD_ALIGN_PARAGRAPH.CENTER: TA_CENTER, WD_ALIGN_PARAGRAPH.RIGHT: TA_RIGHT}.get(align, TA_LEFT)
        st = ParagraphStyle('p', parent=self.base, alignment=al, fontName='Kompas-Bold' if bold else 'Kompas',
                            fontSize=(size or 9.5) + (1 if size else 0), leading=((size or 9.5) + 3.5))
        self.story.append(Paragraph(self._esc(text), st))

    def heading(self, text):
        from reportlab.platypus import Spacer
        self.story.append(Spacer(1, 4))
        self.p(text, bold=True, size=9.5)

    def table(self, rows, widths=None, bold_rows=(), spans=(), grid=True, min_height=None, small_rows=(),
              center_cols=()):
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        ncol = max(len(r) for r in rows)
        rows = [list(r) + [''] * (ncol - len(r)) for r in rows]
        width = 180 * mm
        if widths:
            col_w = [width * w for w in widths]
        elif ncol == 1:
            col_w = [width]
        elif ncol == 2:
            col_w = [width * 0.42, width * 0.58]
        else:
            col_w = [width * 0.34] + [width * 0.66 / (ncol - 1)] * (ncol - 1)

        def style_for(i, j):
            if i in bold_rows:
                return self.cell_bold
            if i in small_rows:
                return self.cell_small
            return self.cell_center if j in center_cols else self.cell

        data = [[Paragraph(self._esc(v), style_for(i, j)) for j, v in enumerate(row)] for i, row in enumerate(rows)]
        heights = [None] * len(data)
        if min_height:
            heights[-1] = min_height * mm
        t = Table(data, colWidths=col_w, rowHeights=heights)
        style = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE' if grid else 'BOTTOM'),
                 ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
        if grid:
            style.append(('GRID', (0, 0), (-1, -1), 0.5, colors.black))
        else:
            style += [('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]
        for r0, c0, r1, c1 in spans:
            style.append(('SPAN', (c0, r0), (c1, r1)))
        t.setStyle(TableStyle(style))
        self.story += [t, Spacer(1, 6)]
        return t

    def kv(self, title, pairs):
        if title:
            self.heading(title)
        self.table([[k, v] for k, v in pairs], widths=[0.42, 0.58])

    def box(self, title, text, height=40):
        self.table([[title], [text or '']], bold_rows=(0,), min_height=None if text else height)

    def signature(self, labels, values=None):
        from reportlab.platypus import Spacer
        values = values or [None] * len(labels)
        self.story.append(Spacer(1, 8))
        self.table([[v or DOTS for v in values], labels], grid=False, small_rows=(1,),
                   widths=[1 / len(labels)] * len(labels))

    def footnotes(self, notes):
        from reportlab.platypus import HRFlowable, Paragraph, Spacer
        self.story += [Spacer(1, 4), HRFlowable(width='30%', thickness=0.5, color='black', hAlign='LEFT', spaceAfter=3)]
        for n in sorted(notes):
            self.story.append(Paragraph(self._esc(f'{n}) {notes[n]}'), self.note))

    def page_break(self):
        from reportlab.platypus import PageBreak
        self.story.append(PageBreak())

    def bytes(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate
        buf = io.BytesIO()

        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Kompas', 7.5)
            if self.footer_text:
                canvas.drawString(15 * mm, 10 * mm, self.footer_text)
            canvas.drawRightString(195 * mm, 10 * mm, f'str. {doc.page}')
            canvas.restoreState()

        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                                bottomMargin=18 * mm, title='KompetIQ', author='KompetIQ')
        doc.build(self.story, onFirstPage=footer, onLaterPages=footer)
        return buf.getvalue()


def _sheet(fmt, official=False):
    if fmt == 'pdf':
        return PdfSheet(footer_text='' if official else 'Wygenerowano w aplikacji KompetIQ')
    return Sheet()


# ---------------------------------------------------------------- treść przypisów

ROZP_2016 = ('rozporządzenia Prezesa Rady Ministrów z dnia 4 kwietnia 2016 r. w sprawie warunków i sposobu '
             'przeprowadzania ocen okresowych urzędników służby cywilnej i pracowników służby cywilnej')

FIRST_NOTES = {
    1: 'W przypadku ocenianego zatrudnionego w celu zastępstwa nieobecnego członka korpusu służby cywilnej – data '
       'ustalenia przez strony stosunku pracy, że oceniany będzie podlegać pierwszej ocenie.',
    2: 'W trakcie rozmowy oceniającej omawiane są:\n− postawa ocenianego, jego zaangażowanie i postępy w pracy, relacje '
       'ze współpracownikami oraz terminowość wykonywania zadań, oceniane za pomocą elementów oceny,\n− wynik egzaminu '
       'ze służby przygotowawczej, jeżeli oceniany był obowiązany do przystąpienia do tego egzaminu,\n− sprawozdanie '
       'sporządzone przez ocenianego.\nMożna również omówić kierunki dalszego rozwoju zawodowego i potrzeby ocenianego.',
    3: 'Opisy elementów oceny są określone w załączniku nr 1 do rozporządzenia Prezesa Rady Ministrów z dnia 23 lipca '
       '2015 r. w sprawie szczegółowych warunków i sposobu dokonywania pierwszej oceny w służbie cywilnej '
       '(Dz. U. poz. 1144).',
    4: 'Ocena łączna jest średnią arytmetyczną ze wszystkich ocen cząstkowych.',
    5: 'Nie dotyczy ocenianego będącego:\n− absolwentem Krajowej Szkoły Administracji Publicznej, który nie złożył '
       'wniosku o mianowanie w służbie cywilnej,\n− pracownikiem służby cywilnej zatrudnionym w celu zastępstwa '
       'nieobecnego członka korpusu służby cywilnej, podlegającym pierwszej ocenie,\n− pracownikiem służby cywilnej '
       'zatrudnionym na wyższym stanowisku w służbie cywilnej.',
    6: 'Pozytywną pierwszą ocenę należy przyznać ocenianemu, który łącznie spełnił następujące warunki:\n− zaliczył '
       'egzamin ze służby przygotowawczej, chyba że nie dotyczył go obowiązek przystąpienia do tego egzaminu,\n'
       '− złożył sprawozdanie w wyznaczonym terminie,\n− uzyskał nie więcej niż jedną ocenę cząstkową w wysokości '
       '3 punktów za postawę ocenianego, jego zaangażowanie i postępy w pracy, relacje ze współpracownikami oraz '
       'terminowość wykonywania zadań,\n− uzyskał ocenę łączną nie niższą niż 5 punktów za postawę ocenianego, jego '
       'zaangażowanie i postępy w pracy, relacje ze współpracownikami oraz terminowość wykonywania zadań.',
    7: 'W przypadku przyznania negatywnej pierwszej oceny uzasadnienie przyznanej oceny jest obowiązkowe, a w przypadku '
       'przyznania pozytywnej pierwszej oceny – fakultatywne. Uzasadnienie przyznanej oceny może polegać na ogólnym '
       'omówieniu oceny lub na szczegółowym odniesieniu się do wszystkich ocen cząstkowych albo tylko do niektórych '
       'z nich.',
    8: 'Wnioski dotyczące rozwoju zawodowego ocenianego sporządza się fakultatywnie – tylko w przypadku przyznania '
       'pozytywnej pierwszej oceny. Określa się m.in. zakres wiedzy, która powinna być poszerzona, zakres umiejętności, '
       'które wymagają doskonalenia, oraz proponowane formy rozwoju zawodowego ocenianego.',
}

_FORM_PURPOSE = {
    FormType.PERIODIC_A: 'Arkusz służy do sporządzenia oceny okresowej urzędnika służby cywilnej lub pracownika służby '
                         'cywilnej, zatrudnionego na stanowisku kierownika urzędu, które jest stanowiskiem pracy '
                         'w służbie cywilnej.',
    FormType.PERIODIC_B: 'Arkusz służy do sporządzenia oceny okresowej urzędnika służby cywilnej lub pracownika służby '
                         'cywilnej, zatrudnionego na stanowisku, na którym praca polega na bezpośrednim kierowaniu '
                         'pracownikami.',
    FormType.PERIODIC_C: 'Arkusz służy do sporządzenia oceny okresowej urzędnika służby cywilnej lub pracownika służby '
                         'cywilnej, zatrudnionego na stanowisku, które nie jest:\n– stanowiskiem kierownika urzędu, '
                         'będącym stanowiskiem pracy w służbie cywilnej, ani\n– stanowiskiem, na którym praca polega na '
                         'bezpośrednim kierowaniu pracownikami.',
}
_POSITION = ('Należy wskazać pełną nazwę stanowiska pracy wraz z jego rozszerzeniem określającym, do jakich spraw jest '
             'to stanowisko (jeżeli zostało to określone w opisie stanowiska pracy).')
_ADDITIONAL = f'Należy wpisać nazwy wybranych kryteriów, korzystając z załącznika nr 1 do {ROZP_2016}.'
_TOPICS_I = ('W trakcie rozmowy omawiane są: 1) główne obowiązki wynikające z opisu stanowiska pracy zajmowanego przez '
             'ocenianego, 2) kryteria obowiązkowe i kryteria dodatkowe, jeżeli są wybierane przez oceniającego, '
             '3) oczekiwania oceniającego co do sposobu spełniania kryteriów oceny przez ocenianego, 4) cele do '
             'osiągnięcia w okresie, w którym oceniany podlega ocenie, jeżeli ich określenie jest uzasadnione ze względu '
             'na charakter obowiązków wynikających z opisu stanowiska pracy zajmowanego przez ocenianego, a także sposób '
             'realizacji wyznaczonych celów.')
_TOPICS_II = ('W trakcie rozmowy oceniającej omawia się: 1) główne obowiązki wykonywane przez ocenianego w okresie, '
              'w którym podlegał ocenie, oraz sposób ich realizacji, z uwzględnieniem spełniania przez ocenianego '
              'ustalonych kryteriów oceny, 2) sposób realizowania przez ocenianego celów do osiągnięcia w okresie, '
              'w którym oceniany podlegał ocenie, jeżeli cele te zostały wyznaczone, 3) kierunki dalszego rozwoju '
              'zawodowego i potrzeby ocenianego w zakresie podnoszenia kwalifikacji i doskonalenia umiejętności.')
_FROM = 'Data „od” oznacza datę zapoznania ocenianego z kryteriami oceny – z części I arkusza oceny.'
_TO = ('Data „do” oznacza datę sporządzenia oceny na piśmie. Jeżeli ocena okresowa jest sporządzana w związku '
       'z zastosowaniem art. 81 ust. 6 ustawy z dnia 21 listopada 2008 r. o służbie cywilnej (Dz. U. z 2014 r. '
       'poz. 1111, z późn. zm.) i nie została sporządzona przed zmianą stanowiska pracy, należy w tym polu wpisać '
       'ostatni dzień pracy na zajmowanym stanowisku pracy.')
_X = 'Należy wstawić znak „X” w odpowiednie pole.'
_POS = ('POZYTYWNA – w przypadku ustalenia ogólnego poziomu spełniania kryteriów oceny na poziomie „znacznie powyżej '
        'oczekiwań”, „powyżej oczekiwań” albo „na poziomie oczekiwań”, pod warunkiem nieuzyskania przez ocenianego '
        'żadnej z ocen cząstkowych na poziomie „znacznie poniżej oczekiwań”.')
_NEG = ('NEGATYWNA – w przypadku ustalenia ogólnego poziomu spełniania kryteriów oceny na poziomie „poniżej oczekiwań” '
        'albo „znacznie poniżej oczekiwań”, a także w przypadku uzyskania przez ocenianego co najmniej jednej oceny '
        'cząstkowej na poziomie „znacznie poniżej oczekiwań”.')
_JUST = ('Uzasadnienie jest obligatoryjne w przypadku otrzymania przez ocenianego negatywnej oceny okresowej. '
         'W przypadku przyznania oceny pozytywnej uzasadnienie jest fakultatywne. Sporządzenie uzasadnienia oceny może '
         'polegać na ogólnym omówieniu oceny lub na szczegółowym odniesieniu się do wszystkich ocen cząstkowych albo '
         'tylko do niektórych z nich.')
_IPRZ = ('Uwzględniając sporządzoną ocenę, realizowane i przyszłe zadania oraz oczekiwania ocenianego, należy określić '
         'kierunki rozwoju zawodowego ocenianego, biorąc pod uwagę obszary wiedzy i umiejętności wymagające '
         'doskonalenia, oraz zaproponować optymalne formy i metody ich realizacji.')
_PREV = 'Należy wpisać „pozytywna” lub „negatywna”.'
_PREV_LEVEL = 'Należy wpisać, na jakim poziomie była przyznana poprzednia ocena okresowa (np. „na poziomie oczekiwań”).'
_DG = ('W urzędzie, w którym przepisy nie przewidują tworzenia stanowiska dyrektora generalnego urzędu, sprzeciw '
       'składa się do kierownika tego urzędu.')
_PART3 = ('Części III nie drukuje się i nie dołącza do arkusza oceny okresowej w przypadku ocenianego będącego '
          'pracownikiem służby cywilnej oraz w razie nieskładania wniosku o przyznanie urzędnikowi służby cywilnej '
          'kolejnego stopnia służbowego.')


def periodic_notes(form_type):
    """Numeracja przypisów: w arkuszu A brak przypisu do „Stanowiska pracy”, więc kolejne są przesunięte o 1."""
    texts = [_FORM_PURPOSE[form_type]] + ([] if form_type == FormType.PERIODIC_A else [_POSITION]) + [
        _ADDITIONAL, _TOPICS_I, _TOPICS_II, _FROM, _TO, _X, _ADDITIONAL, _POS, _NEG, _JUST, _IPRZ, _PREV, _PREV_LEVEL,
        _X] + ([] if form_type == FormType.PERIODIC_A else [_DG]) + [_PART3]
    keys = ['purpose'] + ([] if form_type == FormType.PERIODIC_A else ['position']) + [
        'additional', 'topics_i', 'topics_ii', 'from', 'to', 'x', 'additional2', 'pos', 'neg', 'just', 'iprz', 'prev',
        'prev_level', 'promotion'] + ([] if form_type == FormType.PERIODIC_A else ['dg']) + ['part3']
    num_of = {k: i + 1 for i, k in enumerate(keys)}
    return num_of, {i + 1: t for i, t in enumerate(texts)}


# ---------------------------------------------------------------- arkusz pierwszej oceny

def _first(s, a):
    e = a.employee
    N = FIRST_NOTES
    s.p(ANNEX[a.form_type], align=WD_ALIGN_PARAGRAPH.RIGHT)
    s.p('ARKUSZ PIERWSZEJ OCENY W SŁUŻBIE CYWILNEJ', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
    s.heading('I. CZĘŚĆ OGÓLNA')
    s.kv('', [['NAZWA URZĘDU', a.institution.name]])
    s.kv('DANE OCENIANEGO', [['Imię', e.first_name], ['Nazwisko', e.last_name],
                             ['Komórka organizacyjna', e.org_unit.name if e.org_unit else ''],
                             ['Stanowisko pracy', e.position],
                             ['Data nawiązania stosunku pracy{1}', d(e.employment_date)]])
    for title, user in (('DANE BEZPOŚREDNIEGO PRZEŁOŻONEGO', a.evaluator),
                        ('DANE KIERUJĄCEGO KOMÓRKĄ ORGANIZACYJNĄ', a.unit_head)):
        f, l, u, pos = person(user)
        s.kv(title, [['Imię', f], ['Nazwisko', l], ['Komórka organizacyjna', u], ['Stanowisko pracy', pos]])

    s.heading('II. ROZMOWA WSTĘPNA')
    s.table([
        ['Data przeprowadzenia rozmowy wstępnej', d(a.criteria_interview_date)],
        ['Termin wyznaczony na złożenie sprawozdania dotyczącego zadań realizowanych przez ocenianego w trakcie '
         'przepracowanego okresu', f'od {d(a.report_deadline_from)} – do {d(a.report_deadline_to)}'],
        ['Okres, w którym powinna zostać dokonana pierwsza ocena w służbie cywilnej',
         f'od {d(a.window_from)} – do {d(a.window_to)}'],
    ], widths=[0.55, 0.45])
    s.p('Potwierdzamy przeprowadzenie rozmowy wstępnej oraz wyznaczenie terminu na złożenie sprawozdania i zapoznanie '
        'z nim ocenianego.')
    date_i = d(a.criteria_interview_date, None)
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'podpis bezpośredniego przełożonego'], [None, date_i, None])
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'podpis ocenianego'], [None, date_i, None])
    s.footnotes({1: N[1]})

    s.heading('III. ROZMOWA OCENIAJĄCA')
    s.table([['Data przeprowadzenia rozmowy oceniającej', d(a.evaluation_interview_date)]], widths=[0.55, 0.45])
    s.p('Potwierdzamy przeprowadzenie rozmowy oceniającej i omówienie w trakcie tej rozmowy wszystkich wymaganych '
        'zagadnień{2}.')
    date_e = d(a.evaluation_interview_date, None)
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka bezpośredniego przełożonego',
                 'podpis bezpośredniego przełożonego'], [None, date_e, full_name(a.evaluator), None])
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka ocenianego', 'podpis ocenianego'],
                [None, date_e, e.full_name, None])

    s.heading('IV. OCENA POSTAWY OCENIANEGO, JEGO ZAANGAŻOWANIA I POSTĘPÓW W PRACY, RELACJI ZE WSPÓŁPRACOWNIKAMI '
              'ORAZ TERMINOWOŚCI WYKONYWANIA ZADAŃ')
    rows = [['ELEMENTY OCENY{3}', 'OCENA CZĄSTKOWA (należy wstawić znak „X” w odpowiednie pole)', '', ''],
            ['', 'poniżej oczekiwań', 'na poziomie oczekiwań', 'powyżej oczekiwań'],
            ['', '3 punkty', '5 punktów', '7 punktów']]
    for i, c in enumerate(a.ordered_criteria(), 1):
        rows.append([f'{i}. {c.competency.name}', _x(c.score == 3), _x(c.score == 5), _x(c.score == 7)])
    summary = a.summary()
    rows.append(['OCENA ŁĄCZNA{4}', num(summary.average), '', ''])
    s.table(rows, widths=[0.4, 0.2, 0.2, 0.2], bold_rows=(0,), center_cols=(1, 2, 3),
            spans=[(0, 0, 2, 0), (0, 1, 0, 3), (len(rows) - 1, 1, len(rows) - 1, 3)])

    s.heading('V. PIERWSZA OCENA W SŁUŻBIE CYWILNEJ')
    w6 = [0.14, 0.06, 0.14, 0.06, 0.5, 0.1]
    s.table([['OCENIANY ZALICZYŁ EGZAMIN ZE SŁUŻBY PRZYGOTOWAWCZEJ (należy wstawić znak „X” w odpowiednie pole)'],
             ['TAK', _x(a.prep_exam == ExamStatus.PASSED), 'NIE', _x(a.prep_exam == ExamStatus.FAILED),
              'NIE DOTYCZY{5}', _x(a.prep_exam == ExamStatus.NOT_APPLICABLE)]],
            widths=w6, bold_rows=(0,), spans=[(0, 0, 0, 5)], center_cols=(1, 3, 5))
    s.table([['SPRAWOZDANIE ZOSTAŁO ZŁOŻONE W WYZNACZONYM TERMINIE (należy wstawić znak „X” w odpowiednie pole)'],
             ['TAK', _x(a.report_on_time is True), 'NIE', _x(a.report_on_time is False)]],
            widths=[0.4, 0.1, 0.4, 0.1], bold_rows=(0,), spans=[(0, 0, 0, 3)], center_cols=(1, 3))
    s.table([['PIERWSZA OCENA W SŁUŻBIE CYWILNEJ (należy wstawić znak „X” w odpowiednie pole)'],
             ['POZYTYWNA{6}', _x(a.result == Result.POSITIVE), 'NEGATYWNA', _x(a.result == Result.NEGATIVE)]],
            widths=[0.4, 0.1, 0.4, 0.1], bold_rows=(0,), spans=[(0, 0, 0, 3)], center_cols=(1, 3))
    s.footnotes({k: N[k] for k in (2, 3, 4, 5, 6)})

    s.box('UZASADNIENIE PRZYZNANEJ OCENY{7}', a.justification)
    s.heading('VI. WNIOSKI DOTYCZĄCE ROZWOJU ZAWODOWEGO OCENIANEGO')
    s.box('WNIOSKI DOTYCZĄCE ROZWOJU ZAWODOWEGO OCENIANEGO{8}', a.development_conclusions)
    s.heading('POTWIERDZENIE DOKONANIA PIERWSZEJ OCENY W SŁUŻBIE CYWILNEJ')
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka bezpośredniego przełożonego',
                 'podpis bezpośredniego przełożonego'], [None, None, full_name(a.evaluator), None])
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka kierującego komórką organizacyjną',
                 'podpis kierującego komórką organizacyjną'], [None, None, full_name(a.unit_head), None])
    s.p('Zapoznałam(-łem) się z pierwszą oceną w służbie cywilnej.')
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka ocenianego', 'podpis ocenianego'],
                [None, d(a.acknowledged_on, None), e.full_name, None])
    s.footnotes({k: N[k] for k in (7, 8)})


# ---------------------------------------------------------------- arkusze A, B, C

def _evaluator_rows(a, with_unit):
    f, l, u, pos = person(a.evaluator)
    if with_unit:
        return [['Imię', f], ['Nazwisko', l], ['Komórka organizacyjna', u], ['Stanowisko pracy', pos]]
    return [['Imię', f], ['Nazwisko', l], ['Stanowisko', pos]]


def _scale_table(s, title, form, crits, n_scale, min_rows=0):
    rows = [[title, f'OCENA CZĄSTKOWA{{{n_scale}}}'] + [''] * (len(form.scale) - 1),
            [''] + [p.label[0].upper() + p.label[1:] for p in form.scale],
            [''] + [f'{p.points} {"punkt" if p.points == 1 else "punkty" if p.points in (2, 3, 4) else "punktów"}'
                    for p in form.scale]]
    for c in crits:
        rows.append([c.competency.name] + [_x(c.score == p.points) for p in form.scale])
    rows += [['\u00a0'] * (len(form.scale) + 1) for _ in range(max(0, min_rows - len(crits)))]
    ncol = len(form.scale)
    s.table(rows, widths=[0.4] + [0.6 / ncol] * ncol, bold_rows=(0,), center_cols=tuple(range(1, ncol + 1)),
            spans=[(0, 0, 2, 0), (0, 1, 0, ncol)])


def _periodic(s, a):
    form, e = a.form, a.employee
    is_a = a.form_type == FormType.PERIODIC_A
    n, notes = periodic_notes(a.form_type)
    title = ('ARKUSZ ' + a.form_type[-1], 'OCENA OKRESOWA',
             f'URZĘDNIKA SŁUŻBY CYWILNEJ LUB PRACOWNIKA SŁUŻBY CYWILNEJ{{{n["purpose"]}}}')

    # CZĘŚĆ I
    s.p(ANNEX[a.form_type], align=WD_ALIGN_PARAGRAPH.RIGHT)
    for line in title:
        s.p(line, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
    s.heading('CZĘŚĆ I')
    s.kv('', [['NAZWA URZĘDU', a.institution.name]])
    if is_a:
        s.kv('DANE OCENIANEGO', [['Imię', e.first_name], ['Nazwisko', e.last_name], ['Stanowisko pracy', e.position]])
    else:
        s.kv('DANE OCENIANEGO', [['Imię', e.first_name], ['Nazwisko', e.last_name],
                                 ['Komórka organizacyjna', e.org_unit.name if e.org_unit else ''],
                                 [f'Stanowisko pracy{{{n["position"]}}}', e.position]])
    s.kv('DANE OCENIAJĄCEGO', _evaluator_rows(a, with_unit=not is_a))

    s.heading('KRYTERIA OCENY I TERMIN SPORZĄDZENIA OCENY')
    mand = [c.competency.name for c in a.ordered_criteria() if c.is_mandatory]
    add = [c.competency.name for c in a.ordered_criteria() if not c.is_mandatory]
    right = (add + [''] * form.max_additional)[:form.max_additional]
    right_dates = ['Termin sporządzenia oceny']
    rows = [['Kryteria obowiązkowe',
             f'Kryteria dodatkowe wybrane przez oceniającego (nie więcej niż {form.max_additional}){{{n["additional"]}}}',
             '']]
    nrows = max(len(mand), len(right) + 1)
    for i in range(nrows):
        left = mand[i] if i < len(mand) else ''
        if i < len(right):
            rows.append([left, right[i], ''])
        elif i == len(right):
            rows.append([left, right_dates[0], d(a.due_date)])
        else:
            rows.append([left, '', ''])
    spans = [(0, 1, 0, 2)] + [(i + 1, 1, i + 1, 2) for i in range(nrows) if i != len(right)]
    s.table(rows, widths=[0.45, 0.33, 0.22], bold_rows=(0,), spans=spans)
    s.p('Potwierdzamy:\n− przeprowadzenie rozmowy, o której mowa w § 5 ust. 1 rozporządzenia Prezesa Rady Ministrów '
        'z dnia 4 kwietnia 2016 r. w sprawie warunków i sposobu przeprowadzania ocen okresowych urzędników służby '
        'cywilnej i pracowników służby cywilnej (Dz. U. poz. 470), i omówienie w trakcie tej rozmowy wszystkich '
        f'wymaganych zagadnień{{{n["topics_i"]}}},\n− zapoznanie ocenianego z kryteriami oceny oraz terminem '
        'sporządzenia oceny.')
    date_i = d(a.criteria_interview_date, None)
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'podpis oceniającego'], [None, date_i, None])
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'podpis ocenianego'], [None, date_i, None])
    s.footnotes({n[k]: notes[n[k]] for k in ('purpose', 'position', 'additional', 'topics_i') if k in n})

    # CZĘŚĆ II
    s.page_break()
    s.p(ANNEX[a.form_type], align=WD_ALIGN_PARAGRAPH.RIGHT)
    s.heading('CZĘŚĆ II')
    s.table([[f'DATA PRZEPROWADZENIA ROZMOWY OCENIAJĄCEJ{{{n["topics_ii"]}}}', d(a.evaluation_interview_date), '', ''],
             ['OKRES, W KTÓRYM OCENIANY PODLEGAŁ OCENIE', f'OD{{{n["from"]}}}:', d(a.period_from),
              f'DO{{{n["to"]}}}: {d(a.period_to)}']],
            widths=[0.46, 0.12, 0.2, 0.22], spans=[(0, 1, 0, 3)])
    crits = list(a.ordered_criteria())
    _scale_table(s, 'KRYTERIA OBOWIĄZKOWE', form, [c for c in crits if c.is_mandatory], n['x'])
    _scale_table(s, f'KRYTERIA DODATKOWE WYBRANE PRZEZ OCENIAJĄCEGO{{{n["additional2"]}}}', form,
                 [c for c in crits if not c.is_mandatory], n['x'], min_rows=form.max_additional)
    summary = a.summary()
    s.table([['Średnia arytmetyczna z ocen cząstkowych przyznanych za poszczególne kryteria oceny:',
              num(summary.average)]], widths=[0.75, 0.25])
    s.heading('PRZYZNANIE OCENY')
    bands = ['od 1 punktu do 2 punktów', 'powyżej 2 punktów do 4 punktów', 'powyżej 4 punktów do 6 punktów',
             'powyżej 6 punktów do 8 punktów', 'powyżej 8 punktów do 9 punktów']
    labels = ['znacznie poniżej oczekiwań', 'poniżej oczekiwań', 'na poziomie oczekiwań', 'powyżej oczekiwań',
              'znacznie powyżej oczekiwań']
    s.table([['Należy wstawić znak „X” w odpowiednie pole',
              'Liczba punktów stanowiąca średnią arytmetyczną ze wszystkich ocen cząstkowych',
              'Ogólny poziom spełnienia kryteriów oceny']]
            + [[_x(summary.level == i + 1), b, lab] for i, (b, lab) in enumerate(zip(bands, labels))],
            widths=[0.2, 0.45, 0.35], bold_rows=(0,), center_cols=(0,))
    s.table([['OCENA OKRESOWA W SŁUŻBIE CYWILNEJ', f'POZYTYWNA{{{n["pos"]}}}', _x(a.result == Result.POSITIVE),
              f'NEGATYWNA{{{n["neg"]}}}', _x(a.result == Result.NEGATIVE)]],
            widths=[0.4, 0.2, 0.1, 0.2, 0.1], center_cols=(2, 4))
    s.footnotes({n[k]: notes[n[k]] for k in ('topics_ii', 'from', 'to', 'x', 'additional2', 'pos', 'neg')})

    s.box(f'UZASADNIENIE PRZYZNANEJ OCENY OKRESOWEJ{{{n["just"]}}}', a.justification, height=55)
    s.box(f'WNIOSKI DOTYCZĄCE INDYWIDUALNEGO PROGRAMU ROZWOJU ZAWODOWEGO{{{n["iprz"]}}}', a.development_conclusions)
    s.heading('DANE DOTYCZĄCE POPRZEDNIEJ OCENY OKRESOWEJ URZĘDNIKA SŁUŻBY CYWILNEJ')
    s.table([[f'Ocena{{{n["prev"]}}}', (a.get_previous_result_display() or '').lower(), f'Poziom{{{n["prev_level"]}}}',
              a.previous_level, 'Data sporządzenia', d(a.previous_date)]],
            widths=[0.1, 0.17, 0.1, 0.25, 0.18, 0.2])
    s.heading(f'CZY DO OCENY OKRESOWEJ DOŁĄCZONO WNIOSEK O PRZYZNANIE KOLEJNEGO STOPNIA SŁUŻBOWEGO?{{{n["promotion"]}}}')
    not_applicable = not e.is_civil_servant
    s.table([['TAK', _x(not not_applicable and a.promotion_request is True), 'NIE',
              _x(not not_applicable and a.promotion_request is False),
              'NIE DOTYCZY (oceniany jest pracownikiem służby cywilnej)', _x(not_applicable)]],
            widths=[0.1, 0.07, 0.1, 0.07, 0.56, 0.1], center_cols=(1, 3, 5))
    s.kv('DANE OCENIAJĄCEGO', _evaluator_rows(a, with_unit=not is_a))
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'podpis oceniającego'])
    s.p('Przeprowadzono ze mną rozmowę oceniającą oraz zapoznałem(-łam) się z oceną okresową i wnioskami dotyczącymi '
        'indywidualnego programu rozwoju zawodowego.')
    s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka ocenianego', 'podpis ocenianego'],
                [None, d(a.acknowledged_on, None), e.full_name, None])
    s.p('Pouczenie', bold=True)
    if is_a:
        s.p('Na podstawie art. 83 ust. 1 ustawy z dnia 21 listopada 2008 r. o służbie cywilnej od oceny okresowej '
            'służy, w terminie 7 dni od dnia zapoznania się z oceną, sprzeciw do:')
        s.p(DOTS * 4)
    else:
        s.p('Zgodnie z art. 83 ust. 1 ustawy z dnia 21 listopada 2008 r. o służbie cywilnej od oceny okresowej służy, '
            f'w terminie 7 dni od dnia zapoznania się z oceną, sprzeciw do dyrektora generalnego urzędu{{{n["dg"]}}}.')
    s.footnotes({n[k]: notes[n[k]] for k in ('just', 'iprz', 'prev', 'prev_level', 'promotion', 'dg') if k in n})

    # CZĘŚĆ III — tylko urzędnik służby cywilnej i złożony wniosek (przypis do części III)
    if e.is_civil_servant and a.promotion_request:
        s.page_break()
        s.p(ANNEX[a.form_type], align=WD_ALIGN_PARAGRAPH.RIGHT)
        s.heading('CZĘŚĆ III')
        s.p('Wniosek jest wypełniany i dołączany do arkusza oceny okresowej ocenianego tylko w sytuacji skorzystania '
            'przez oceniającego z możliwości przewidzianej w art. 89 ust. 1 ustawy z dnia 21 listopada 2008 r. '
            f'o służbie cywilnej.{{{n["part3"]}}}', align=WD_ALIGN_PARAGRAPH.CENTER)
        s.kv('DANE URZĘDNIKA SŁUŻBY CYWILNEJ', [
            ['Imię', e.first_name], ['Nazwisko', e.last_name],
            ['Rok mianowania', str(e.appointment_year) if e.appointment_year else '(rrrr)'],
            ['Posiadany stopień służbowy', e.service_grade],
            ['Data przyznania stopnia służbowego', d(e.service_grade_date)]])
        s.heading('WNIOSEK O PRZYZNANIE URZĘDNIKOWI SŁUŻBY CYWILNEJ KOLEJNEGO STOPNIA SŁUŻBOWEGO')
        s.p(f'W związku z uzyskaniem przez Panią/Pana {e.full_name} pozytywnej oceny okresowej, na podstawie art. 89 '
            f'ust. 1 ustawy z dnia 21 listopada 2008 r. o służbie cywilnej wnioskuję o przyznanie '
            f'{a.promotion_grade or "………."} stopnia służbowego.')
        s.box('Umotywowanie wniosku', a.promotion_motivation, height=60)
        s.signature(['miejscowość', 'data (dd.mm.rrrr)', 'imię i nazwisko lub pieczątka oceniającego',
                     'podpis oceniającego'], [None, None, full_name(a.evaluator), None])
        s.footnotes({n['part3']: notes[n['part3']]})


def assessment_doc(a, fmt='docx') -> bytes:
    s = _sheet(fmt, official=True)
    (_first if a.is_first else _periodic)(s, a)
    return s.bytes()


def development_plan_doc(plan, fmt='docx') -> bytes:
    s = _sheet(fmt)
    a = plan.assessment
    s.p('PLAN ROZWOJU ZAWODOWEGO', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    s.table([['Oceniany', a.employee.full_name], ['Stanowisko', a.employee.position],
             ['Ocena', a.get_form_type_display()], ['Wnioski', plan.summary]])
    rows = [['Kompetencja', 'Działanie', 'Forma', 'Miernik sukcesu', 'Termin', 'Status']]
    for act in plan.actions.select_related('competency'):
        rows.append([act.competency.name if act.competency else '', f'{act.title}\n{act.description}',
                     act.get_type_display(), act.success_measure, d(act.due_date), act.get_status_display()])
    s.table(rows, bold_rows=(0,))
    return s.bytes()


def interview_plan_doc(a, script: dict, fmt='docx') -> bytes:
    s = _sheet(fmt)
    s.p('SCENARIUSZ ROZMOWY OCENIAJĄCEJ', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    s.p(f'{a.get_form_type_display()} — {a.employee.position}')
    s.heading('Cel rozmowy')
    s.p(script.get('goal', ''))
    for title, key in (('Przygotowanie', 'preparation_checklist'),):
        s.heading(title)
        for x in script.get(key, []):
            s.p(f'☐ {x}')
    s.heading('Otwarcie')
    s.p(script.get('opening', ''))
    for sec in script.get('sections', []):
        s.heading(sec.get('title', ''))
        for x in sec.get('talking_points', []):
            s.p(f'• {x}')
        for x in sec.get('questions_to_employee', []):
            s.p(f'? {x}')
    for title, key in (('Informacja zwrotna — mocne strony', 'strengths_feedback'),
                       ('Informacja zwrotna — obszary do rozwoju', 'development_feedback')):
        s.heading(title)
        for f in script.get(key, []):
            s.p(f"{f.get('competency', '')}: sytuacja — {f.get('situation', '')}; zachowanie — "
                f"{f.get('behaviour', '')}; wpływ — {f.get('impact', '')}")
    s.heading('Rozmowa o rozwoju')
    for x in script.get('development_dialogue_questions', []):
        s.p(f'? {x}')
    s.heading('Zamknięcie')
    s.p(script.get('closing', ''))
    s.heading('Elementy formalne')
    for x in script.get('formal_reminders', []):
        s.p(f'☐ {x}')
    s.heading('Trudne momenty')
    for x in script.get('difficult_moments_tips', []):
        s.p(f'• {x}')
    return s.bytes()
