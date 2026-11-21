import logging

from django.core.mail import send_mail
from django.db.models import Q

from apps.institutions.models import Membership, Role

from .models import Notification

log = logging.getLogger(__name__)


def notify(recipient, *, institution, kind, title, body='', assessment=None, sender=None, dedupe_key='',
           email=True):
    if recipient is None:
        return None
    if dedupe_key and Notification.objects.filter(recipient=recipient, dedupe_key=dedupe_key).exists():
        return None
    n = Notification.objects.create(institution=institution, recipient=recipient, sender=sender, kind=kind,
                                    title=title, body=body, assessment=assessment, dedupe_key=dedupe_key)
    if email and recipient.email:
        try:
            # Bez danych oceny w treści e-maila — tylko informacja i odesłanie do aplikacji (minimalizacja danych).
            send_mail(f'Kompas Kompetencji: {title}', f'{title}\n\nSzczegóły w aplikacji Kompas Kompetencji.',
                      None, [recipient.email])
            n.email_sent = True
            n.save(update_fields=['email_sent'])
        except Exception as e:  # noqa: BLE001 — poczta nie może blokować procesu
            log.warning('Nie wysłano e-maila do %s: %s', recipient.pk, e)
    return n


def unit_head_for(a):
    if a.unit_head_id:
        return a.unit_head
    if a.employee.org_unit_id and a.employee.org_unit.head_id:
        return a.employee.org_unit.head
    return None


def hr_users(institution):
    return [m.user for m in Membership.objects.filter(institution=institution).filter(
        Q(role=Role.HR) | Q(role=Role.ADMIN)).select_related('user')]


def on_transition(a, action, user):
    """Komunikacja w procesie po zmianie statusu."""
    who = user.get_full_name() or user.username
    emp = a.employee.full_name
    if action == 'finalize' and a.is_first:
        notify(unit_head_for(a), institution=a.institution, kind=Notification.Kind.APPROVAL, assessment=a, sender=user,
               title=f'Pierwsza ocena: {emp} czeka na Twoje potwierdzenie',
               body=f'{who} dokonał(a) pierwszej oceny. Potwierdź jej dokonanie w arkuszu.')
    elif action == 'approve':
        notify(a.evaluator, institution=a.institution, kind=Notification.Kind.STATUS, assessment=a, sender=user,
               title=f'Pierwsza ocena: {emp} została potwierdzona',
               body=f'{who} potwierdził(a) dokonanie oceny. Zapoznaj ocenianego z oceną.')
    elif action in ('finalize', 'acknowledge'):
        label = 'sporządzona' if action == 'finalize' else 'przekazana ocenianemu'
        for hr in hr_users(a.institution):
            if hr.id != user.id:
                notify(hr, institution=a.institution, kind=Notification.Kind.STATUS, assessment=a, sender=user,
                       title=f'Ocena {label}: {emp}', email=False)
