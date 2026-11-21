import os
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessments.forms_config import FormType
from apps.assessments.models import BehavioralEvidence
from apps.assessments.services import create_assessment
from apps.competencies.models import CompetencyModel
from apps.deadlines.rules import add_months
from django.conf import settings

from apps.competencies.models import CompetencyModel as _CM
from apps.employees.models import Employee, JobDescription
from apps.employees.osp import map_competencies, parse_osp

OSP_DIR = settings.LEGAL_DOCS_DIR / 'OSP_word'


def jd_from_osp(employee, filename):
    """Opis stanowiska z wzorcowego OSP (docs_assets/OSP_word); gdy brak pliku — opis zastępczy."""
    path = OSP_DIR / filename
    if not path.exists():
        return JobDescription.objects.create(employee=employee, main_duties=JD_SPECIALIST)
    osp = parse_osp(path.read_bytes())
    return JobDescription.objects.create(
        employee=employee, symbol=osp.symbol, purpose=osp.purpose, main_duties='\n'.join(osp.tasks),
        responsibilities='\n'.join(osp.authorizations), subordinates=osp.subordinates,
        manages_people=osp.manages_people, source_name=filename,
        soft_competencies=map_competencies(osp.soft_competencies, _CM.objects.filter(institution__isnull=True).first()),
        requirements='Kompetencje miękkie: ' + ', '.join(osp.soft_competencies))
from apps.institutions.models import Institution, Membership, OrgUnit, Role

User = get_user_model()
# Domena testowa (RFC 2606): poczta kont demo trafia tylko do skrzynki testowej w aplikacji.
DEMO_EMAIL_DOMAIN = 'urzad-demo.test'

JD_SPECIALIST = """Prowadzenie postępowań administracyjnych w sprawach zezwoleń, przygotowywanie projektów decyzji
i pism, udzielanie informacji interesantom telefonicznie i w punkcie obsługi, prowadzenie rejestru spraw,
współpraca z innymi komórkami przy sprawach złożonych, przygotowywanie zestawień i analiz na potrzeby kierownictwa."""
JD_LEADER = """Kierowanie zespołem 6 osób ds. obsługi klienta, planowanie i rozdzielanie zadań, monitorowanie terminowości
spraw, ocena pracowników i ich rozwój, rozpatrywanie skarg, udział w negocjacjach z wykonawcami usług,
przygotowywanie sprawozdań kwartalnych, reprezentowanie urzędu na spotkaniach z interesariuszami."""
JD_NEW = """Obsługa korespondencji wpływającej, wprowadzanie danych do systemu EZD, przygotowywanie projektów odpowiedzi
w sprawach prostych, archiwizacja dokumentacji, wsparcie zespołu w organizacji szkoleń."""


class Command(BaseCommand):
    help = 'Tworzy instytucję demonstracyjną z użytkownikami, pracownikami i ocenami w różnych stanach.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=os.environ.get('DEMO_PASSWORD', ''))
        parser.add_argument('--reset', action='store_true',
                            help='Usuwa instytucję demo (oceny, pracowników, powiadomienia, skrzynkę testową) i tworzy ją od nowa.')

    @transaction.atomic
    def handle(self, password, reset=False, **opts):
        if not password:
            raise CommandError('Podaj hasło dla kont demo: --password lub DEMO_PASSWORD.')
        if not CompetencyModel.objects.exists():
            raise CommandError('Najpierw uruchom import_competency_model.')
        if reset:
            from apps.deadlines.models import OutgoingEmail
            OutgoingEmail.objects.filter(to__icontains=DEMO_EMAIL_DOMAIN).delete()
            from apps.assessments.models import Assessment
            # Oceny najpierw: chronią pracowników i oceniających (PROTECT), więc nie znikają kaskadowo z instytucją.
            deleted = Assessment.objects.filter(institution__slug='urzad-demo').delete()[0]
            deleted += Institution.objects.filter(slug='urzad-demo').delete()[0]
            self.stdout.write(f'Usunięto dane demo ({deleted} rekordów).')
        inst, created = Institution.objects.get_or_create(slug='urzad-demo', defaults={'name': 'Urząd Demonstracyjny'})
        if not created:
            self.stdout.write('Instytucja demo już istnieje — pomijam.')
            return

        def user(username, first, last, role, unit=None, position=''):
            # Konto może już istnieć (poprzedni reset) — odtwarzamy dane i hasło. Konta superużytkownika nie ruszamy.
            u, _ = User.objects.get_or_create(username=username)
            if not u.is_superuser:
                u.first_name, u.last_name, u.email = first, last, f'{username}@{DEMO_EMAIL_DOMAIN}'
                u.set_password(password)
                u.save()
            Membership.objects.create(user=u, institution=inst, role=role, org_unit=unit, position=position)
            return u

        dept = OrgUnit.objects.create(institution=inst, name='Wydział Spraw Obywatelskich')
        team = OrgUnit.objects.create(institution=inst, name='Oddział Zezwoleń', parent=dept)
        head = user('kierownik', 'Maria', 'Wójcik', Role.UNIT_HEAD, dept, 'Dyrektor wydziału')
        dept.head = head
        dept.save()
        sup = user('przelozony', 'Tomasz', 'Zieliński', Role.SUPERVISOR, team, 'Kierownik oddziału')
        team.head = head
        team.save()
        user('kadry', 'Ewa', 'Kaczmarek', Role.HR, None, 'Specjalista ds. kadr')
        user('admin', 'Adam', 'Mazur', Role.ADMIN, None, 'Administrator')

        today = date.today()
        e1 = Employee.objects.create(institution=inst, org_unit=team, supervisor=sup, first_name='Katarzyna', form_of_address='PANI',
                                     last_name='Nowicka', position='Starszy specjalista', is_civil_servant=False,
                                     employment_date=today - timedelta(days=900))
        jd_from_osp(e1, 'OSP DC WZKSOiC 6 starszy specjalista.docx')
        e2 = Employee.objects.create(institution=inst, org_unit=team, supervisor=sup, first_name='Piotr', form_of_address='PAN',
                                     last_name='Lewicki', position='Naczelnik wydziału', is_managerial=True,
                                     is_civil_servant=True, service_grade='radca',
                                     employment_date=today - timedelta(days=2000))
        jd_from_osp(e2, 'OSP DWM WKAM 1 naczelnik wydziału.docx')
        e3 = Employee.objects.create(institution=inst, org_unit=team, supervisor=sup, first_name='Julia', form_of_address='PANI',
                                     last_name='Sadowska', position='Referent', employment_date=today - timedelta(days=200),
                                     contract_end_date=add_months(today - timedelta(days=200), 12) - timedelta(days=1))
        JobDescription.objects.create(employee=e3, main_duties=JD_NEW)
        e4 = Employee.objects.create(institution=inst, org_unit=team, supervisor=sup, first_name='Marek', form_of_address='PAN',
                                     last_name='Kowalczyk', position='Radca', is_civil_servant=True,
                                     service_grade='starszy radca', employment_date=today - timedelta(days=1500))
        jd_from_osp(e4, 'OSP DSI WWI 5 radca.docx')

        # Ocena okresowa C w toku — z przykładami zachowań
        a1 = create_assessment(institution=inst, employee=e1, evaluator=sup, form_type=FormType.PERIODIC_C,
                               criteria_interview_date=today - timedelta(days=600),
                               due_date=today + timedelta(days=40), period_from=today - timedelta(days=620),
                               period_to=today + timedelta(days=40),
                               expectations='Terminowe przygotowywanie aktualizacji dokumentacji zarządzania kryzysowego; aktywna współpraca z zespołami CSIRT; rzetelne protokoły z kontroli podmiotów krytycznych.')
        a1.status = 'CRITERIA_SET'
        a1.save()
        wsp = a1.criteria.get(competency__code='wspolpraca')
        inds = list(wsp.selected_indicators.all())
        BehavioralEvidence.objects.create(
            criterion=wsp, indicator=inds[0], occurred_on=today - timedelta(days=120), created_by=sup,
            situation='W marcu wydział miał opóźnienie w aktualizacji krajowego planu reagowania na incydenty — trzy rozdziały wymagały uzgodnień z CSIRT NASK i RCB.',
            action='Zaproponowała podział rozdziałów między członków zespołu, przejęła uzgodnienia z CSIRT NASK i zorganizowała wspólne spotkanie robocze.',
            result='Projekt aktualizacji przekazano kierownictwu w terminie, z uwagami CSIRT uwzględnionymi w jednej rundzie.')
        BehavioralEvidence.objects.create(
            criterion=wsp, indicator=inds[1] if len(inds) > 1 else None, occurred_on=today - timedelta(days=30),
            created_by=sup, situation='Nowo zatrudniona osoba przygotowywała pierwszą kontrolę podmiotu krytycznego.',
            action='Przekazała jej wzory dokumentów z poprzednich kontroli i omówiła z nią listę kontrolną.', result='')

        # Ocena okresowa B — szkic
        create_assessment(institution=inst, employee=e2, evaluator=sup, form_type=FormType.PERIODIC_B)
        # Pierwsza ocena — szkic z wyliczonymi terminami
        create_assessment(institution=inst, employee=e3, evaluator=sup, form_type=FormType.FIRST,
                          criteria_interview_date=e3.employment_date + timedelta(days=10))

        from django.core.management import call_command
        call_command('seed_demo_full', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            'Utworzono dane demo. Konta: kierownik, przelozony, kadry, admin (hasło z --password).'))
