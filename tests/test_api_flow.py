from datetime import date, timedelta

import pytest

from apps.employees.models import Employee
from apps.institutions.models import Institution, Role
from tests.conftest import make_user

pytestmark = pytest.mark.django_db


def create(api, user, emp, form='PERIODIC_C'):
    r = api(user).post('/api/v1/assessments/', {'employee': emp.id, 'form_type': form}, format='json')
    assert r.status_code == 201, r.data
    return r.data


def act(c, aid, action, **data):
    return c.post(f'/api/v1/assessments/{aid}/transition/', {'action': action, **data}, format='json')


def test_periodic_c_full_flow(org, api):
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    codes = [x['competency_code'] for x in a['criteria']]
    assert codes == ['wykorzystywanie-wiedzy', 'rzetelnosc', 'organizacja-pracy', 'wspolpraca', 'komunikacja']

    # kryteria dodatkowe: maks. 3, bez obowiązkowych
    model = c.get('/api/v1/competency-models/active/').data
    by_code = {x['code']: x['id'] for x in model['competencies']}
    r = c.put(f"/api/v1/assessments/{a['id']}/additional-criteria/",
              {'competency_ids': [by_code['kreatywnosc'], by_code['negocjowanie'], by_code['myslenie-analityczne'],
                                  by_code['wystapienia-publiczne']]}, format='json')
    assert r.status_code == 400
    r = c.put(f"/api/v1/assessments/{a['id']}/additional-criteria/",
              {'competency_ids': [by_code['rzetelnosc']]}, format='json')
    assert r.status_code == 400
    r = c.put(f"/api/v1/assessments/{a['id']}/additional-criteria/",
              {'competency_ids': [by_code['orientacja-na-klienta']]}, format='json')
    assert r.status_code == 200 and len(r.data['criteria']) == 6

    # przejście wymaga danych formalnych
    r = act(c, a['id'], 'set_criteria')
    assert r.status_code == 400 and len(r.data['errors']) >= 2
    today = date.today()
    c.patch(f"/api/v1/assessments/{a['id']}/", {'criteria_interview_date': str(today - timedelta(days=300)),
                                               'due_date': str(today + timedelta(days=30))}, format='json')
    assert act(c, a['id'], 'set_criteria').status_code == 200

    detail = c.get(f"/api/v1/assessments/{a['id']}/").data
    crit = detail['criteria'][0]
    ind = crit['selected_indicators'][0]
    r = c.post('/api/v1/evidence/', {'criterion': crit['id'], 'indicator': ind, 'situation': 'S', 'action': 'D',
                                     'result': 'R'}, format='json')
    assert r.status_code == 201
    r = c.put(f"/api/v1/criteria/{crit['id']}/rating/", {'indicator': ind, 'level': 4}, format='json')
    assert r.data['suggested_points'] == 7

    # niedozwolona punktacja
    assert c.patch(f"/api/v1/criteria/{crit['id']}/", {'score': 4}, format='json').status_code == 400
    for cr in detail['criteria']:
        assert c.patch(f"/api/v1/criteria/{cr['id']}/", {'score': 5}, format='json').status_code == 200

    assert act(c, a['id'], 'finalize').status_code == 400  # zły status
    c.patch(f"/api/v1/assessments/{a['id']}/", {'evaluation_interview_date': str(today),
                                               'period_from': str(today - timedelta(days=700)),
                                               'period_to': str(today)}, format='json')
    assert act(c, a['id'], 'complete_interview').status_code == 200
    r = act(c, a['id'], 'finalize')
    assert r.status_code == 200, r.data
    assert r.data['result'] == 'POSITIVE' and r.data['average'] == '5.00' and r.data['level'] == 3

    # po sporządzeniu — blokada edycji
    assert c.patch(f"/api/v1/criteria/{crit['id']}/", {'score': 7}, format='json').status_code == 403
    assert c.patch(f"/api/v1/assessments/{a['id']}/", {'justification': 'x'}, format='json').status_code in (400, 403)

    assert act(c, a['id'], 'approve').status_code == 400  # nie dotyczy okresowej
    assert act(c, a['id'], 'acknowledge').status_code == 400
    r = act(c, a['id'], 'acknowledge', acknowledged_on=str(today))
    assert r.status_code == 200 and r.data['status'] == 'ACKNOWLEDGED'

    checklist = c.get(f"/api/v1/assessments/{a['id']}/checklist/").data
    assert any(i['key'] == 'objection' for i in checklist)

    r = c.get(f"/api/v1/assessments/{a['id']}/export/sheet/")
    assert r.status_code == 200 and r.content[:4] == b'%PDF'
    assert len(c.get(f"/api/v1/assessments/{a['id']}/history/").data) >= 4


def test_negative_requires_justification(org, api):
    c = api(org.sup)
    a = create(api, org.sup, org.emp)
    today = date.today()
    c.patch(f"/api/v1/assessments/{a['id']}/", {'criteria_interview_date': str(today), 'due_date': str(today),
                                               'evaluation_interview_date': str(today), 'period_from': str(today),
                                               'period_to': str(today)}, format='json')
    act(c, a['id'], 'set_criteria')
    act(c, a['id'], 'complete_interview')
    for i, cr in enumerate(a['criteria']):
        c.patch(f"/api/v1/criteria/{cr['id']}/", {'score': 1 if i == 0 else 9}, format='json')
    r = act(c, a['id'], 'finalize')
    assert r.status_code == 400 and any('Uzasadnienie' in e for e in r.data['errors'])
    c.patch(f"/api/v1/assessments/{a['id']}/", {'justification': 'Uzasadnienie.'}, format='json')
    r = act(c, a['id'], 'finalize')
    assert r.status_code == 200 and r.data['result'] == 'NEGATIVE'


def test_first_assessment_requires_unit_head_approval(org, api):
    c = api(org.sup)
    a = create(api, org.sup, org.new, form='FIRST')
    assert a['report_deadline_from'] and a['window_to']
    assert len(a['criteria']) == 5
    today = date.today()
    c.patch(f"/api/v1/assessments/{a['id']}/", {'criteria_interview_date': str(today - timedelta(days=90))}, format='json')
    assert act(c, a['id'], 'set_criteria').status_code == 200
    c.patch(f"/api/v1/assessments/{a['id']}/", {'evaluation_interview_date': str(today)}, format='json')
    assert act(c, a['id'], 'complete_interview').status_code == 200
    for cr in a['criteria']:
        c.patch(f"/api/v1/criteria/{cr['id']}/", {'score': 5}, format='json')
    assert act(c, a['id'], 'finalize').status_code == 400  # brak egzaminu / sprawozdania
    c.patch(f"/api/v1/assessments/{a['id']}/", {'prep_exam': 'PASSED', 'report_on_time': True}, format='json')
    assert act(c, a['id'], 'finalize').data['result'] == 'POSITIVE'
    assert act(c, a['id'], 'acknowledge', acknowledged_on=str(today)).status_code == 400
    assert act(c, a['id'], 'approve').status_code == 400  # przełożony nie zatwierdza
    h = api(org.head)
    assert 'approve' in h.get(f"/api/v1/assessments/{a['id']}/").data['available_actions']
    assert act(h, a['id'], 'approve').status_code == 200
    assert act(c, a['id'], 'acknowledge', acknowledged_on=str(today)).status_code == 200


def test_visibility_and_permissions(org, api):
    a = create(api, org.sup, org.emp)
    # inny przełożony nie widzi
    assert api(org.other_sup).get(f"/api/v1/assessments/{a['id']}/").status_code == 404
    assert api(org.other_sup).get('/api/v1/employees/').data == []
    # nie może rozpocząć oceny cudzego pracownika
    r = api(org.other_sup).post('/api/v1/assessments/', {'employee': org.emp.id, 'form_type': 'PERIODIC_C'},
                                format='json')
    assert r.status_code == 403
    # HR widzi, ale nie edytuje
    hr = api(org.hr)
    assert hr.get(f"/api/v1/assessments/{a['id']}/").status_code == 200
    assert hr.patch(f"/api/v1/assessments/{a['id']}/", {'goals': 'x'}, format='json').status_code == 403
    # kierujący komórką widzi oceny w swojej komórce
    assert api(org.head).get(f"/api/v1/assessments/{a['id']}/").status_code == 200
    # przełożony nie zmienia danych kadrowych
    assert api(org.sup).patch(f'/api/v1/employees/{org.emp.id}/', {'position': 'x'}, format='json').status_code == 403
    # druga ocena w toku niedozwolona
    r = api(org.sup).post('/api/v1/assessments/', {'employee': org.emp.id, 'form_type': 'PERIODIC_C'}, format='json')
    assert r.status_code == 400


def test_tenant_isolation(org, api):
    a = create(api, org.sup, org.emp)
    other = Institution.objects.create(name='Urząd B', slug='b')
    admin_b = make_user(other, 'adminb', Role.ADMIN)
    emp_b = Employee.objects.create(institution=other, first_name='X', last_name='Y', position='Z')
    c = api(admin_b)
    assert c.get(f"/api/v1/assessments/{a['id']}/").status_code == 404
    assert [e['id'] for e in c.get('/api/v1/employees/').data] == [emp_b.id]
    assert c.get(f"/api/v1/assessments/{a['id']}/export/sheet/").status_code == 404
    crit = a['criteria'][0]['id']
    assert c.post('/api/v1/evidence/', {'criterion': crit, 'situation': 'x'}, format='json').status_code == 403
    # użytkownik bez członkostwa
    from django.contrib.auth import get_user_model
    nobody = get_user_model().objects.create_user('nobody', password='x')
    assert api(nobody).get('/api/v1/assessments/').status_code == 403


def test_login_and_me(org, client):
    from rest_framework.test import APIClient
    c = APIClient(enforce_csrf_checks=True)
    token = c.get('/api/v1/auth/csrf/').data['csrfToken']
    r = c.post('/api/v1/auth/login/', {'username': 'sup', 'password': 'zle'}, format='json', HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 400
    r = c.post('/api/v1/auth/login/', {'username': 'sup', 'password': 'Test-haslo-2026!'}, format='json',
               HTTP_X_CSRFTOKEN=token)
    assert r.status_code == 200 and r.data['active_membership']['role'] == 'SUPERVISOR'
    assert c.get('/api/v1/auth/me/').data['username'] == 'sup'


def test_deadlines_and_development_plan(org, api):
    c = api(org.sup)
    a = create(api, org.sup, org.new, form='FIRST')
    rows = c.get('/api/v1/deadlines/upcoming/?days=400').data
    assert {'report', 'first_window'} <= {r['kind'] for r in rows}
    plan = c.post('/api/v1/development-plans/', {'assessment': a['id']}, format='json').data
    r = c.post('/api/v1/development-actions/', {'plan': plan['id'], 'title': 'Mentoring', 'type': 'MENTORING',
                                                'due_date': str(date.today() + timedelta(days=10))}, format='json')
    assert r.status_code == 201
    c.patch(f"/api/v1/development-actions/{r.data['id']}/", {'status': 'DONE'}, format='json')
    assert c.get(f"/api/v1/development-plans/{plan['id']}/").data['progress']['percent'] == 100
    assert c.get(f"/api/v1/assessments/{a['id']}/export/development-plan/").status_code == 200
    assert api(org.hr).post(f"/api/v1/development-actions/{r.data['id']}/notes/", {'text': 'x'},
                            format='json').status_code == 403


def test_spa_fallback(client, db):
    r = client.get('/oceny/1')
    assert r.status_code in (200, 503)
