"""Eksport arkuszy oceny do DOCX — układ odwzorowuje wzory z załączników do rozporządzeń."""
import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from apps.assessments.forms_config import FormType
from apps.assessments.models import ExamStatus, Result

ANNEX = {FormType.FIRST: 'Załącznik nr 2', FormType.PERIODIC_A: 'Załącznik nr 2',
         FormType.PERIODIC_B: 'Załącznik nr 3', FormType.PERIODIC_C: 'Załącznik nr 4'}
TITLE = {
    FormType.FIRST: 'ARKUSZ PIERWSZEJ OCENY W SŁUŻBIE CYWILNEJ',
    FormType.PERIODIC_A: 'ARKUSZ A\nOCENA OKRESOWA URZĘDNIKA SŁUŻBY CYWILNEJ LUB PRACOWNIKA SŁUŻBY CYWILNEJ',
    FormType.PERIODIC_B: 'ARKUSZ B\nOCENA OKRESOWA URZĘDNIKA SŁUŻBY CYWILNEJ LUB PRACOWNIKA SŁUŻBY CYWILNEJ',
    FormType.PERIODIC_C: 'ARKUSZ C\nOCENA OKRESOWA URZĘDNIKA SŁUŻBY CYWILNEJ LUB PRACOWNIKA SŁUŻBY CYWILNEJ',
}
SIGN = '…………………………………'


def d(v):
    return v.strftime('%d.%m.%Y') if v else '……………'


def person(user):
    if not user:
        return ('', '', '', '')
    m = user.memberships.first()
    return (user.first_name, user.last_name, (m.org_unit.name if m and m.org_unit else ''), (m.position if m else ''))


class Sheet:
    def __init__(self):
        self.doc = Document()
        st = self.doc.styles['Normal']
        st.font.name = 'Times New Roman'
        st.font.size = Pt(10)

    def p(self, text='', bold=False, align=None, size=None):
        par = self.doc.add_paragraph()
        run = par.add_run(text)
        run.bold = bold
        if size:
            run.font.size = Pt(size)
        if align:
            par.alignment = align
        return par

    def heading(self, text):
        self.p(text, bold=True, size=11)

    def table(self, rows, widths=None, header=False):
        t = self.doc.add_table(rows=0, cols=len(rows[0]))
        t.style = 'Table Grid'
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            cells = t.add_row().cells
            for j, val in enumerate(row):
                cells[j].text = '' if val is None else str(val)
                if header and i == 0:
                    for r in cells[j].paragraphs[0].runs:
                        r.bold = True
        self.doc.add_paragraph()
        return t

    def kv(self, title, pairs):
        self.heading(title)
        if all(k == '' for k, _ in pairs):
            text = '\n'.join(str(v or '') for _, v in pairs)
            self.table([[text if text.strip() else '\n\n\n']])
        else:
            self.table([[k, v] for k, v in pairs])

    def signatures(self, labels):
        self.table([[SIGN] * len(labels), labels])

    def page_break(self):
        self.doc.add_page_break()

    def bytes(self):
        buf = io.BytesIO()
        self.doc.save(buf)
        return buf.getvalue()


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

    def __init__(self):
        from reportlab.lib.styles import ParagraphStyle
        _register_fonts()
        self.story = []
        self.base = ParagraphStyle('base', fontName='Kompas', fontSize=9.5, leading=12.5, spaceAfter=3)
        self.cell = ParagraphStyle('cell', parent=self.base, fontSize=9, leading=11.5, spaceAfter=0)
        self.cell_bold = ParagraphStyle('cellb', parent=self.cell, fontName='Kompas-Bold')

    @staticmethod
    def _esc(text):
        from xml.sax.saxutils import escape
        return escape('' if text is None else str(text)).replace('\n', '<br/>')

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
        self.p(text, bold=True, size=10)

    def table(self, rows, widths=None, header=False, min_height=None):
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
        data = [[Paragraph(self._esc(v), self.cell_bold if (header and i == 0) else self.cell) for v in row]
                for i, row in enumerate(rows)]
        heights = [min_height if (min_height and ncol == 1) else None for _ in data]
        t = Table(data, colWidths=col_w, rowHeights=heights, repeatRows=1 if header else 0)
        style = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                 ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
        if header:
            style.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')))
        t.setStyle(TableStyle(style))
        self.story += [t, Spacer(1, 6)]
        return t

    def kv(self, title, pairs):
        self.heading(title)
        if all(k == '' for k, _ in pairs):
            from reportlab.lib.units import mm
            text = '\n'.join(str(v or '') for _, v in pairs)
            self.table([[text]], min_height=None if text.strip() else 22 * mm)
        else:
            self.table([[k, v] for k, v in pairs])

    def signatures(self, labels):
        self.table([[SIGN] * len(labels), labels], widths=[1 / len(labels)] * len(labels))

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
            canvas.drawString(15 * mm, 10 * mm, 'Wygenerowano w Kompasie Kompetencji')
            canvas.drawRightString(195 * mm, 10 * mm, f'str. {doc.page}')
            canvas.restoreState()

        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                                bottomMargin=18 * mm, title='Kompas Kompetencji', author='Kompas Kompetencji')
        doc.build(self.story, onFirstPage=footer, onLaterPages=footer)
        return buf.getvalue()


def _sheet(fmt):
    return PdfSheet() if fmt == 'pdf' else Sheet()


def _x(cond):
    return 'X' if cond else ''


def _header(s, a):
    s.p(ANNEX[a.form_type], align=WD_ALIGN_PARAGRAPH.RIGHT)
    s.p('WZÓR', align=WD_ALIGN_PARAGRAPH.RIGHT)
    s.p(TITLE[a.form_type], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    s.kv('NAZWA URZĘDU', [['', a.institution.name]])
    e = a.employee
    s.kv('DANE OCENIANEGO', [['Imię', e.first_name], ['Nazwisko', e.last_name],
                             ['Komórka organizacyjna', e.org_unit.name if e.org_unit else ''],
                             ['Stanowisko pracy', e.position]]
         + ([['Data nawiązania stosunku pracy', d(e.employment_date)]] if a.is_first else []))


def _first(s, a):
    s.p('CZĘŚĆ OGÓLNA', bold=True)
    _header(s, a)
    for title, user in (('DANE BEZPOŚREDNIEGO PRZEŁOŻONEGO', a.evaluator),
                        ('DANE KIERUJĄCEGO KOMÓRKĄ ORGANIZACYJNĄ', a.unit_head)):
        f, l, u, pos = person(user)
        s.kv(title, [['Imię', f], ['Nazwisko', l], ['Komórka organizacyjna', u], ['Stanowisko pracy', pos]])
    s.heading('ROZMOWA WSTĘPNA')
    s.table([
        ['Data przeprowadzenia rozmowy wstępnej', d(a.criteria_interview_date)],
        ['Termin wyznaczony na złożenie sprawozdania', f'od {d(a.report_deadline_from)} – do {d(a.report_deadline_to)}'],
        ['Okres, w którym powinna zostać dokonana pierwsza ocena', f'od {d(a.window_from)} – do {d(a.window_to)}'],
    ])
    s.p('Potwierdzamy przeprowadzenie rozmowy wstępnej oraz wyznaczenie terminu na złożenie sprawozdania i zapoznanie z nim ocenianego.')
    s.signatures(['miejscowość, data, podpis bezpośredniego przełożonego', 'miejscowość, data, podpis ocenianego'])
    s.heading('ROZMOWA OCENIAJĄCA')
    s.table([['Data przeprowadzenia rozmowy oceniającej', d(a.evaluation_interview_date)]])
    s.p('Potwierdzamy przeprowadzenie rozmowy oceniającej i omówienie w trakcie tej rozmowy wszystkich wymaganych zagadnień.')
    s.signatures(['bezpośredni przełożony', 'oceniany'])
    s.heading('OCENA POSTAWY OCENIANEGO, JEGO ZAANGAŻOWANIA I POSTĘPÓW W PRACY, RELACJI ZE WSPÓŁPRACOWNIKAMI '
              'ORAZ TERMINOWOŚCI WYKONYWANIA ZADAŃ')
    rows = [['Elementy oceny', 'poniżej oczekiwań (3 pkt)', 'na poziomie oczekiwań (5 pkt)', 'powyżej oczekiwań (7 pkt)']]
    for c in a.ordered_criteria():
        rows.append([c.competency.name, _x(c.score == 3), _x(c.score == 5), _x(c.score == 7)])
    s.table(rows, header=True)
    summary = a.summary()
    s.table([['OCENA ŁĄCZNA', summary.average if summary.average is not None else '']])
    s.heading('PIERWSZA OCENA W SŁUŻBIE CYWILNEJ')
    s.table([
        ['Oceniany zaliczył egzamin ze służby przygotowawczej', f'TAK [{_x(a.prep_exam == ExamStatus.PASSED)}]  '
         f'NIE [{_x(a.prep_exam == ExamStatus.FAILED)}]  NIE DOTYCZY [{_x(a.prep_exam == ExamStatus.NOT_APPLICABLE)}]'],
        ['Sprawozdanie zostało złożone w wyznaczonym terminie',
         f'TAK [{_x(a.report_on_time is True)}]  NIE [{_x(a.report_on_time is False)}]'],
        ['PIERWSZA OCENA W SŁUŻBIE CYWILNEJ', f'POZYTYWNA [{_x(a.result == Result.POSITIVE)}]  '
         f'NEGATYWNA [{_x(a.result == Result.NEGATIVE)}]'],
    ])
    s.kv('UZASADNIENIE PRZYZNANEJ OCENY', [['', a.justification]])
    s.kv('WNIOSKI DOTYCZĄCE ROZWOJU ZAWODOWEGO OCENIANEGO', [['', a.development_conclusions]])
    s.heading('POTWIERDZENIE DOKONANIA PIERWSZEJ OCENY W SŁUŻBIE CYWILNEJ')
    s.signatures(['bezpośredni przełożony', 'kierujący komórką organizacyjną'])
    s.p('Zapoznałam(-łem) się z pierwszą oceną w służbie cywilnej.')
    s.signatures([f'oceniany (data: {d(a.acknowledged_on)})'])


def _periodic(s, a):
    form = a.form
    s.p('CZĘŚĆ I', bold=True)
    _header(s, a)
    f, l, u, pos = person(a.evaluator)
    s.kv('DANE OCENIAJĄCEGO', [['Imię', f], ['Nazwisko', l], ['Komórka organizacyjna', u], ['Stanowisko pracy', pos]])
    s.heading('KRYTERIA OCENY I TERMIN SPORZĄDZENIA OCENY')
    mand = [c.competency.name for c in a.ordered_criteria() if c.is_mandatory]
    add = [c.competency.name for c in a.ordered_criteria() if not c.is_mandatory]
    rows = [['Kryteria obowiązkowe', 'Kryteria dodatkowe wybrane przez oceniającego (nie więcej niż 3)']]
    for i in range(max(len(mand), 3)):
        rows.append([mand[i] if i < len(mand) else '', add[i] if i < len(add) else ''])
    s.table(rows, header=True)
    s.table([['Termin sporządzenia oceny', d(a.due_date)]])
    s.p('Potwierdzamy: przeprowadzenie rozmowy, o której mowa w § 5 ust. 1 rozporządzenia Prezesa Rady Ministrów z dnia '
        '4 kwietnia 2016 r. w sprawie warunków i sposobu przeprowadzania ocen okresowych urzędników służby cywilnej '
        'i pracowników służby cywilnej (Dz. U. poz. 470), i omówienie w trakcie tej rozmowy wszystkich wymaganych '
        f'zagadnień; zapoznanie ocenianego z kryteriami oceny oraz terminem sporządzenia oceny. '
        f'(data rozmowy: {d(a.criteria_interview_date)})')
    s.signatures(['miejscowość, data, podpis oceniającego', 'miejscowość, data, podpis ocenianego'])

    s.p('CZĘŚĆ II', bold=True)
    s.table([['DATA PRZEPROWADZENIA ROZMOWY OCENIAJĄCEJ', d(a.evaluation_interview_date)],
             ['OKRES, W KTÓRYM OCENIANY PODLEGAŁ OCENIE', f'od {d(a.period_from)} do {d(a.period_to)}']])
    head = ['Kryterium'] + [f'{p.label} ({p.points} pkt)' for p in form.scale]
    for title, mandatory in (('KRYTERIA OBOWIĄZKOWE', True), ('KRYTERIA DODATKOWE WYBRANE PRZEZ OCENIAJĄCEGO', False)):
        crits = [c for c in a.ordered_criteria() if c.is_mandatory == mandatory]
        if not crits and not mandatory:
            continue
        s.heading(title)
        s.table([head] + [[c.competency.name] + [_x(c.score == p.points) for p in form.scale] for c in crits],
                header=True)
    summary = a.summary()
    s.table([['Średnia arytmetyczna z ocen cząstkowych', summary.average if summary.average is not None else '']])
    s.heading('PRZYZNANIE OCENY')
    bands = ['od 1 punktu do 2 punktów', 'powyżej 2 punktów do 4 punktów', 'powyżej 4 punktów do 6 punktów',
             'powyżej 6 punktów do 8 punktów', 'powyżej 8 punktów do 9 punktów']
    labels = ['znacznie poniżej oczekiwań', 'poniżej oczekiwań', 'na poziomie oczekiwań', 'powyżej oczekiwań',
              'znacznie powyżej oczekiwań']
    s.table([['Liczba punktów (średnia)', 'Ogólny poziom spełnienia kryteriów oceny', '']]
            + [[b, lab, _x(summary.level == i + 1)] for i, (b, lab) in enumerate(zip(bands, labels))], header=True)
    s.table([['OCENA OKRESOWA W SŁUŻBIE CYWILNEJ', f'POZYTYWNA [{_x(a.result == Result.POSITIVE)}]  '
              f'NEGATYWNA [{_x(a.result == Result.NEGATIVE)}]']])
    s.kv('UZASADNIENIE PRZYZNANEJ OCENY OKRESOWEJ', [['', a.justification]])
    s.kv('WNIOSKI DOTYCZĄCE INDYWIDUALNEGO PROGRAMU ROZWOJU ZAWODOWEGO', [['', a.development_conclusions]])
    s.kv('DANE DOTYCZĄCE POPRZEDNIEJ OCENY OKRESOWEJ URZĘDNIKA SŁUŻBY CYWILNEJ',
         [['Ocena', a.get_previous_result_display()], ['Poziom', a.previous_level],
          ['Data sporządzenia', d(a.previous_date)]])
    s.table([['CZY DO OCENY OKRESOWEJ DOŁĄCZONO WNIOSEK O PRZYZNANIE KOLEJNEGO STOPNIA SŁUŻBOWEGO?',
              f'TAK [{_x(a.promotion_request is True)}]  NIE [{_x(a.promotion_request is False)}]  '
              f'NIE DOTYCZY [{_x(not a.employee.is_civil_servant)}]']])
    s.signatures(['miejscowość, data, podpis oceniającego'])
    s.p('Przeprowadzono ze mną rozmowę oceniającą oraz zapoznałem(-łam) się z oceną okresową i wnioskami dotyczącymi '
        'indywidualnego programu rozwoju zawodowego.')
    s.signatures([f'miejscowość, data ({d(a.acknowledged_on)}), podpis ocenianego'])
    s.p('Pouczenie', bold=True)
    s.p('Zgodnie z art. 83 ust. 1 ustawy z dnia 21 listopada 2008 r. o służbie cywilnej od oceny okresowej służy, '
        'w terminie 7 dni od dnia zapoznania się z oceną, sprzeciw do dyrektora generalnego urzędu.')
    if a.promotion_request:
        s.page_break()
        s.p('CZĘŚĆ III', bold=True)
        e = a.employee
        s.kv('DANE URZĘDNIKA SŁUŻBY CYWILNEJ', [['Imię', e.first_name], ['Nazwisko', e.last_name],
                                                ['Posiadany stopień służbowy', e.service_grade]])
        s.heading('WNIOSEK O PRZYZNANIE URZĘDNIKOWI SŁUŻBY CYWILNEJ KOLEJNEGO STOPNIA SŁUŻBOWEGO')
        s.p(f'W związku z uzyskaniem przez Panią/Pana {e.full_name} pozytywnej oceny okresowej, na podstawie art. 89 '
            f'ust. 1 ustawy z dnia 21 listopada 2008 r. o służbie cywilnej wnioskuję o przyznanie '
            f'{a.promotion_grade or "………."} stopnia służbowego.')
        s.kv('Umotywowanie wniosku', [['', a.promotion_motivation]])
        s.signatures(['miejscowość, data, podpis oceniającego'])


def assessment_doc(a, fmt='docx') -> bytes:
    s = _sheet(fmt)
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
    s.table(rows, header=True)
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
