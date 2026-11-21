from datetime import date, timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.competencies.importer import import_model
from apps.employees.models import Employee, JobDescription
from apps.institutions.models import Institution, Membership, OrgUnit, Role

PASSWORD = 'Test-haslo-2026!'


@pytest.fixture
def competency_model(db):
    return import_model(settings.LEGAL_DOCS_DIR / 'Model_kompetencji.xlsx')


def make_user(inst, username, role, unit=None):
    u = get_user_model().objects.create_user(username, password=PASSWORD, first_name=username.title(), last_name='Test')
    Membership.objects.create(user=u, institution=inst, role=role, org_unit=unit)
    return u


@pytest.fixture
def org(db, competency_model):
    inst = Institution.objects.create(name='Urząd A', slug='a')
    unit = OrgUnit.objects.create(institution=inst, name='Wydział')
    head = make_user(inst, 'head', Role.UNIT_HEAD, unit)
    unit.head = head
    unit.save()
    sup = make_user(inst, 'sup', Role.SUPERVISOR, unit)
    other_sup = make_user(inst, 'other', Role.SUPERVISOR, unit)
    hr = make_user(inst, 'hr', Role.HR)
    emp = Employee.objects.create(institution=inst, org_unit=unit, supervisor=sup, first_name='Katarzyna',
                                  last_name='Nowicka', position='Specjalista',
                                  employment_date=date.today() - timedelta(days=800))
    JobDescription.objects.create(employee=emp, main_duties='Prowadzenie postępowań administracyjnych.')
    new = Employee.objects.create(institution=inst, org_unit=unit, supervisor=sup, first_name='Julia',
                                  last_name='Sadowska', position='Referent',
                                  employment_date=date.today() - timedelta(days=100))
    return type('Org', (), dict(inst=inst, unit=unit, head=head, sup=sup, other_sup=other_sup, hr=hr, emp=emp,
                                new=new))


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    c.force_login(user)
    return c


@pytest.fixture
def api():
    return client_for
