"""Kartoteka pracowników prowadzona przez kadry w aplikacji (przycisk „Dodaj pracownika”)."""
from datetime import date, timedelta

import pytest

from apps.employees.models import Employee
from apps.institutions.models import Institution, OrgUnit, Role
from tests.conftest import make_user

pytestmark = pytest.mark.django_db


def payload(org, **kw):
    return {'first_name': 'Anna', 'last_name': 'Nowa', 'position': 'Referent', 'form_of_address': 'PANI',
            'org_unit': org.unit.id, 'supervisor': org.sup.id,
            'employment_date': str(date.today() - timedelta(days=60)), **kw}


def test_hr_creates_employee_with_job_description_and_supervisor_sees_it(org, api):
    r = api(org.hr).post('/api/v1/employees/', payload(org), format='json')
    assert r.status_code == 201, r.data
    emp = r.data
    assert emp['suggested_form'] == 'PERIODIC_C' and emp['first_assessment_block'] == ''
    jd = api(org.hr).post('/api/v1/job-descriptions/', {'employee': emp['id'], 'main_duties': 'Rozpatrywanie wniosków'},
                          format='json')
    assert jd.status_code == 201
    mine = {e['id']: e for e in api(org.sup).get('/api/v1/employees/').data}
    assert mine[emp['id']]['latest_job_description']['main_duties'] == 'Rozpatrywanie wniosków'
    # przełożony od razu może rozpocząć pierwszą ocenę
    r = api(org.sup).post('/api/v1/assessments/', {'employee': emp['id'], 'form_type': 'FIRST'}, format='json')
    assert r.status_code == 201


def test_only_hr_and_admin_manage_employees(org, api):
    assert api(org.sup).post('/api/v1/employees/', payload(org), format='json').status_code == 403
    admin = make_user(org.inst, 'adm', Role.ADMIN)
    r = api(admin).post('/api/v1/employees/', payload(org), format='json')
    assert r.status_code == 201
    # edycja i dezaktywacja (pracownik znika z listy, historia ocen zostaje)
    assert api(org.hr).patch(f"/api/v1/employees/{r.data['id']}/", {'position': 'Starszy referent'},
                             format='json').data['position'] == 'Starszy referent'
    assert api(org.hr).delete(f"/api/v1/employees/{r.data['id']}/").status_code == 204
    assert not Employee.objects.get(pk=r.data['id']).is_active


def test_employee_validation(org, api):
    other = Institution.objects.create(name='Urząd B', slug='b')
    foreign_unit = OrgUnit.objects.create(institution=other, name='Obca')
    foreign_user = make_user(other, 'obcy', Role.SUPERVISOR)
    today = date.today()
    r = api(org.hr).post('/api/v1/employees/', payload(org, org_unit=foreign_unit.id, supervisor=foreign_user.id,
                                                        contract_end_date=str(today - timedelta(days=90)),
                                                        service_grade='radca', appointment_year=1990), format='json')
    assert r.status_code == 400
    assert {'org_unit', 'supervisor', 'contract_end_date', 'is_civil_servant'} <= set(r.data)
    r = api(org.hr).post('/api/v1/employees/', payload(org, is_civil_servant=True, appointment_year=1990), format='json')
    assert r.status_code == 400 and 'appointment_year' in r.data
    # kierownik urzędu → stanowisko kierownicze, arkusz A
    r = api(org.hr).post('/api/v1/employees/', payload(org, is_office_head=True), format='json')
    assert r.status_code == 201 and r.data['is_managerial'] and r.data['suggested_form'] == 'PERIODIC_A'
