from datetime import date, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.deadlines.models import Notification
from apps.deadlines.reminders import send_due_reminders
from tests.test_api_flow import act, create

pytestmark = pytest.mark.django_db
OSP = Path(settings.LEGAL_DOCS_DIR) / 'OSP_word'


@pytest.mark.skipif(not OSP.exists(), reason='brak wzorów OSP')
def test_import_osp_detects_manager_and_competencies(org, api):
    f = OSP / 'OSP DWM WKAM 1 naczelnik wydziału.docx'
    r = api(org.sup).post('/api/v1/job-descriptions/import-osp/',
                          {'employee': org.emp.id, 'file': SimpleUploadedFile(f.name, f.read_bytes())}, format='multipart')
    assert r.status_code == 201, r.data
    assert r.data['manages_people'] is True and r.data['symbol'] == 'DWM WKAM 1'
    assert 'zarzadzanie-ludzmi' in r.data['soft_competencies']
    assert api(org.sup).get('/api/v1/employees/').data[0]['suggested_form'] in ('PERIODIC_B',)
    bad = api(org.sup).post('/api/v1/job-descriptions/import-osp/',
                            {'employee': org.emp.id, 'file': SimpleUploadedFile('x.docx', b'nie-docx')}, format='multipart')
    assert bad.status_code == 400
    assert api(org.other_sup).post('/api/v1/job-descriptions/import-osp/',
                                   {'employee': org.emp.id, 'file': SimpleUploadedFile(f.name, f.read_bytes())},
                                   format='multipart').status_code == 403


def test_pdf_and_docx_export(org, api):
    a = create(api, org.sup, org.new, form='FIRST')
    c = api(org.sup)
    pdf = c.get(f"/api/v1/assessments/{a['id']}/export/sheet/")
    assert pdf.status_code == 200 and pdf['Content-Type'] == 'application/pdf' and pdf.content[:4] == b'%PDF'
    docx = c.get(f"/api/v1/assessments/{a['id']}/export/sheet/?fmt=docx")
    assert docx.content[:2] == b'PK'
    assert c.get(f"/api/v1/assessments/{a['id']}/export/sheet/?fmt=xls").status_code == 404


def test_first_assessment_notifies_unit_head_and_evaluator(org, api, django_capture_on_commit_callbacks):
    c = api(org.sup)
    a = create(api, org.sup, org.new, form='FIRST')
    today = date.today()
    c.patch(f"/api/v1/assessments/{a['id']}/", {'criteria_interview_date': str(today), 'evaluation_interview_date': str(today),
                                               'prep_exam': 'NA', 'report_on_time': True}, format='json')
    act(c, a['id'], 'set_criteria')
    act(c, a['id'], 'complete_interview')
    for cr in a['criteria']:
        c.patch(f"/api/v1/criteria/{cr['id']}/", {'score': 5}, format='json')
    with django_capture_on_commit_callbacks(execute=True):
        assert act(c, a['id'], 'finalize').status_code == 200
    n = api(org.head).get('/api/v1/notifications/?unread=1').data
    assert n and n[0]['kind'] == 'APPROVAL'
    with django_capture_on_commit_callbacks(execute=True):
        act(api(org.head), a['id'], 'approve')
    assert api(org.sup).get('/api/v1/notifications/').data[0]['kind'] == 'STATUS'
    nid = n[0]['id']
    api(org.head).post(f'/api/v1/notifications/{nid}/read/')
    assert api(org.head).get('/api/v1/notifications/?unread=1').data == []


def test_hr_overview_and_reminders(org, api):
    a = create(api, org.sup, org.emp)
    c = api(org.sup)
    c.patch(f"/api/v1/assessments/{a['id']}/", {'due_date': str(date.today() + timedelta(days=5))}, format='json')
    assert api(org.sup).get('/api/v1/hr/overview/').status_code == 403
    ov = api(org.hr).get('/api/v1/hr/overview/').data
    assert ov['totals']['all'] == 1 and ov['assessments'][0]['next_deadline']['days_left'] == 5
    assert ov['units'][0]['unit'] == 'Wydział'
    assert send_due_reminders() == 1
    assert send_due_reminders() == 0  # bez duplikatów
    assert Notification.objects.get().recipient == org.sup
    r = api(org.hr).post(f"/api/v1/assessments/{a['id']}/message/", {'to': 'evaluator', 'reminder': True,
                                                                    'message': 'Proszę o uzupełnienie kryteriów.'}, format='json')
    assert r.status_code == 201
    # przełożony może napisać do kadr i kierującego, ale nie „przypominać” sam sobie
    assert api(org.sup).post(f"/api/v1/assessments/{a['id']}/message/", {'to': 'hr', 'message': 'Pytanie'},
                             format='json').status_code == 201
    assert api(org.sup).post(f"/api/v1/assessments/{a['id']}/message/", {'to': 'evaluator', 'message': 'x'},
                             format='json').status_code == 403


def test_development_plan_list_shows_current_plan_per_employee(org, api):
    from apps.assessments.models import Assessment
    c = api(org.sup)
    a1 = create(api, org.sup, org.new, form='FIRST')
    p1 = c.post('/api/v1/development-plans/', {'assessment': a1['id']}, format='json').data
    c.post('/api/v1/development-actions/', {'plan': p1['id'], 'title': 'Stare', 'type': 'TRAINING',
                                            'due_date': str(date.today() - timedelta(days=3))}, format='json')
    Assessment.objects.filter(pk=a1['id']).update(status='ACKNOWLEDGED')
    a2 = create(api, org.sup, org.new, form='PERIODIC_C')
    p2 = c.post('/api/v1/development-plans/', {'assessment': a2['id']}, format='json').data
    c.post('/api/v1/development-actions/', {'plan': p2['id'], 'title': 'Nowe', 'type': 'MENTORING',
                                            'due_date': str(date.today() - timedelta(days=1))}, format='json')
    rows = c.get('/api/v1/development-plans/').data
    assert [r['id'] for r in rows] == [p2['id']]  # tylko aktualny plan pracownika
    st = rows[0]['stats']
    assert st['total'] == 1 and st['overdue'] == 1 and st['next_action']['title'] == 'Nowe'
    assert 'actions' not in rows[0]  # lista jest lekka
    assert len(c.get('/api/v1/development-plans/?all=1').data) == 2
    detail = c.get(f"/api/v1/development-plans/{p2['id']}/").data
    assert detail['can_edit'] and [h['id'] for h in detail['history']] == [p1['id']]
    assert api(org.hr).get(f"/api/v1/development-plans/{p2['id']}/").data['can_edit'] is False


def _docx_text(content):
    import io

    import docx
    d = docx.Document(io.BytesIO(content))
    parts = [p.text for p in d.paragraphs]
    parts += [c.text for t in d.tables for row in t.rows for c in row.cells]
    return '\n'.join(parts)


def test_sheet_export_follows_official_template(org, api):
    """Arkusz jak wzór z rozporządzenia: bez napisu „WZÓR”, z przypisami, pełnymi polami podpisów i części III."""
    c = api(org.sup)
    first = _docx_text(c.get(f"/api/v1/assessments/{create(api, org.sup, org.new, form='FIRST')['id']}/export/sheet/?fmt=docx").content)
    assert 'WZÓR' not in first
    assert 'Ocena łączna jest średnią arytmetyczną ze wszystkich ocen cząstkowych.' in first
    assert 'imię i nazwisko lub pieczątka kierującego komórką organizacyjną' in first

    org.emp.is_civil_servant, org.emp.appointment_year = True, 2015
    org.emp.save()
    a = create(api, org.sup, org.emp)
    c.patch(f"/api/v1/assessments/{a['id']}/", {'promotion_request': True}, format='json')
    text = _docx_text(c.get(f"/api/v1/assessments/{a['id']}/export/sheet/?fmt=docx").content)
    assert 'WZÓR' not in text
    assert 'CZĘŚĆ III' in text and 'Rok mianowania' in text and '2015' in text
    assert 'Data przyznania stopnia służbowego' in text
    assert 'Data „od” oznacza datę zapoznania ocenianego z kryteriami oceny' in text
    assert text.count('DANE OCENIAJĄCEGO') == 2
