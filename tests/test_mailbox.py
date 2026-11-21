"""Skrzynka testowa, e-maile HTML i przywracanie danych demonstracyjnych."""
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import override_settings

from apps.assessments.models import Assessment
from apps.deadlines.models import Notification, OutgoingEmail
from apps.deadlines.notify import notify
from apps.institutions.models import Institution
from tests.conftest import make_user
from apps.institutions.models import Role

pytestmark = pytest.mark.django_db

OUTBOX_MAILERS = {
    'default': {'BACKEND': 'kompetiq.mail.OutboxBackend'},
    'delivery': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'},
}


@override_settings(MAILERS=OUTBOX_MAILERS)
def test_demo_addresses_are_captured_and_real_ones_delivered(org):
    mail.outbox = []
    org.head.email = 'kierownik@urzad-demo.test'
    org.head.save()
    org.sup.email = 'tomasz@example.pl'
    org.sup.save()
    for user in (org.head, org.sup):
        notify(user, institution=org.inst, kind=Notification.Kind.APPROVAL, title='Pierwsza ocena czeka na potwierdzenie')

    captured = OutgoingEmail.objects.get(recipient=org.head)
    assert captured.status == OutgoingEmail.Status.CAPTURED and captured.institution == org.inst
    sent = OutgoingEmail.objects.get(recipient=org.sup)
    assert sent.status == OutgoingEmail.Status.SENT
    # na zewnątrz wyszedł tylko e-mail na prawdziwy adres
    assert [m.to for m in mail.outbox] == [['Sup Test <tomasz@example.pl>']]
    # profesjonalna treść: HTML z przyciskiem, bez danych oceny, wersja tekstowa z linkiem
    assert 'Potwierdź ocenę' in captured.body_html and 'nie zawiera treści oceny' in captured.body_html
    assert 'Dzień dobry' in captured.body_text and 'https://' in captured.body_text
    assert captured.subject == 'KompetIQ: Pierwsza ocena czeka na potwierdzenie'


@override_settings(MAILERS=OUTBOX_MAILERS)
def test_mailbox_api_shows_own_mail_and_admin_sees_institution(org, api):
    org.head.email, org.sup.email = 'head@a.test', 'sup@a.test'
    org.head.save()
    org.sup.save()
    for user in (org.head, org.sup):
        notify(user, institution=org.inst, kind=Notification.Kind.MESSAGE, title=f'Wiadomość dla {user.username}')
    admin = make_user(org.inst, 'adm', Role.ADMIN)
    assert [m['subject'] for m in api(org.sup).get('/api/v1/test-mailbox/').data] == ['KompetIQ: Wiadomość dla sup']
    assert len(api(admin).get('/api/v1/test-mailbox/').data) == 2
    other = Institution.objects.create(name='Urząd B', slug='b')
    assert api(make_user(other, 'admb', Role.ADMIN)).get('/api/v1/test-mailbox/').data == []


def test_seed_demo_reset_restores_initial_state(competency_model):
    call_command('seed_demo', password='Demo-haslo-2026!')
    inst = Institution.objects.get(slug='urzad-demo')
    initial = Assessment.objects.filter(institution=inst).count()
    sup = get_user_model().objects.get(username='przelozony')
    assert sup.email == 'przelozony@urzad-demo.test'
    Assessment.objects.filter(institution=inst).update(status='ACKNOWLEDGED')  # „przejście ścieżki” przed resetem
    OutgoingEmail.objects.create(institution=inst, to='przelozony@urzad-demo.test', subject='x', body_text='x',
                                 status=OutgoingEmail.Status.CAPTURED)

    call_command('seed_demo', password='Demo-haslo-2026!', reset=True)
    inst = Institution.objects.get(slug='urzad-demo')
    assert Assessment.objects.filter(institution=inst).count() == initial
    assert Assessment.objects.filter(institution=inst, status='ACKNOWLEDGED').count() < initial
    assert not OutgoingEmail.objects.exists()
    assert get_user_model().objects.filter(username='przelozony').count() == 1
    assert get_user_model().objects.get(username='przelozony').check_password('Demo-haslo-2026!')


def test_admin_reset_view_only_for_superuser(client, competency_model, monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD', 'Demo-haslo-2026!')
    staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
    client.force_login(staff)
    assert client.get('/admin/institutions/institution/reset-demo/').status_code == 403
    root = get_user_model().objects.create_superuser('root', password='x')
    client.force_login(root)
    assert 'Przywróć dane demonstracyjne' in client.get('/admin/institutions/institution/reset-demo/').content.decode()
    r = client.post('/admin/institutions/institution/reset-demo/')
    assert r.status_code == 302
    assert Assessment.objects.filter(institution__slug='urzad-demo').exists()
    assert root.is_superuser and get_user_model().objects.get(username='root').check_password('x')


@override_settings(MAILERS=OUTBOX_MAILERS)
def test_test_mode_redirects_every_email_to_test_address(org):
    from apps.institutions.models import SystemSettings
    s = SystemSettings.load()
    s.email_test_mode, s.email_test_address = True, 'tester@example.pl'
    s.save()
    mail.outbox = []
    org.head.email, org.sup.email = 'kierownik@urzad-demo.test', 'tomasz@example.pl'
    org.head.save()
    org.sup.save()
    for user in (org.head, org.sup):
        notify(user, institution=org.inst, kind=Notification.Kind.APPROVAL, title='Ocena czeka')
    # oba e-maile — także do konta demo — poszły wyłącznie na adres testowy, z oznaczeniem
    assert [m.to for m in mail.outbox] == [['tester@example.pl'], ['tester@example.pl']]
    assert all(m.subject.startswith('[TEST] ') for m in mail.outbox)
    assert 'pierwotny adresat: Head Test <kierownik@urzad-demo.test>' in mail.outbox[0].body
    assert 'Wiadomość testowa' in mail.outbox[0].alternatives[0][0]
    rows = OutgoingEmail.objects.all()
    assert {r.status for r in rows} == {OutgoingEmail.Status.REDIRECTED}
    assert {r.delivered_to for r in rows} == {'tester@example.pl'}

    s.email_test_mode = False
    s.save()
    mail.outbox = []
    notify(org.sup, institution=org.inst, kind=Notification.Kind.APPROVAL, title='Po testach')
    assert [m.to for m in mail.outbox] == [['Sup Test <tomasz@example.pl>']]


def test_settings_require_address_in_test_mode():
    from django.core.exceptions import ValidationError
    from apps.institutions.models import SystemSettings
    s = SystemSettings(email_test_mode=True)
    with pytest.raises(ValidationError):
        s.full_clean()


def test_settings_admin_opens_single_record(admin_client):
    r = admin_client.get('/admin/institutions/systemsettings/')
    assert r.status_code == 302 and r.url.endswith('/admin/institutions/systemsettings/1/change/')
    assert 'Tryb testowy poczty' in admin_client.get(r.url).content.decode()
