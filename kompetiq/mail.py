"""Backend poczty ze skrzynką testową.

Każda wiadomość jest zapisywana w `OutgoingEmail`. Adresy w domenach testowych (`EMAIL_CAPTURE_DOMAINS`, domyślnie
`.test`, czyli konta demonstracyjne) są tylko przechwytywane; pozostałe trafiają do właściwego dostawcy
(mailer `delivery`: EmailLabs, SMTP albo konsola).

Tryb testowy poczty (Ustawienia systemu w /admin/): każda wiadomość, także do kont demo, idzie wyłącznie na adres
testowy — z oznaczeniem „[TEST]” w temacie i informacją, do kogo była skierowana.
"""
import re
import logging
from email.utils import parseaddr
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mailers
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)


def test_recipient() -> str:
    from apps.institutions.models import SystemSettings
    try:
        return SystemSettings.load().test_recipient
    except Exception:  # noqa: BLE001 — np. tabela jeszcze nie istnieje (migracje); wtedy bez trybu testowego
        return ''


def mark_as_test(subject, text, html, original_to):
    banner = (f'<div style="background:#fdf2e1;border-bottom:2px solid #8f5600;padding:10px 16px;'
              f'font-family:Arial,sans-serif;font-size:13px;color:#8f5600;">'
              f'<strong>Wiadomość testowa</strong> — pierwotny adresat: {escape(original_to)}</div>')
    html = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + banner, html, count=1) if html else ''
    return f'[TEST] {subject}', f'[Wiadomość testowa — pierwotny adresat: {original_to}]\n\n{text}', html


def is_captured(address: str) -> bool:
    domain = parseaddr(address)[1].rpartition('@')[2].lower()
    return any(domain == d.lstrip('.') or domain.endswith(d if d.startswith('.') else '.' + d)
               for d in getattr(settings, 'EMAIL_CAPTURE_DOMAINS', ['.test']))


class OutboxBackend(BaseEmailBackend):
    def __init__(self, *, deliver_via='delivery', **kwargs):
        super().__init__(**kwargs)
        self.deliver_via = deliver_via

    def send_messages(self, email_messages):
        from apps.deadlines.models import OutgoingEmail
        sent = 0
        redirect_to = test_recipient()
        for m in email_messages:
            html = next((c for c, t in (getattr(m, 'alternatives', None) or []) if t == 'text/html'), '')
            headers = m.extra_headers or {}
            subject, body, out_html = m.subject, m.body, html
            if redirect_to:
                targets, ok = [redirect_to], OutgoingEmail.Status.REDIRECTED
                subject, body, out_html = mark_as_test(subject, body, html, ', '.join(m.to))
            else:
                targets, ok = [r for r in m.to if not is_captured(r)], OutgoingEmail.Status.SENT
            status, error = OutgoingEmail.Status.CAPTURED, ''
            if targets:
                try:
                    out = EmailMultiAlternatives(subject, body, m.from_email, targets, reply_to=m.reply_to,
                                                 connection=mailers.create_connection(self.deliver_via))
                    if out_html:
                        out.attach_alternative(out_html, 'text/html')
                    out.send()
                    status = ok
                except Exception as e:  # noqa: BLE001 — zapisujemy błąd, decyzję o przerwaniu podejmuje fail_silently
                    status, error = OutgoingEmail.Status.FAILED, str(e)[:1000]
            OutgoingEmail.objects.create(
                institution_id=headers.get('X-KompetIQ-Institution') or None,
                recipient_id=headers.get('X-KompetIQ-Recipient') or None,
                from_email=m.from_email or settings.DEFAULT_FROM_EMAIL, to=', '.join(m.to)[:1000],
                delivered_to=', '.join(targets)[:1000] if status != OutgoingEmail.Status.CAPTURED else '',
                subject=m.subject[:255], body_text=m.body, body_html=html, status=status, error=error)
            if status == OutgoingEmail.Status.FAILED and not self.fail_silently:
                raise RuntimeError(error)
            sent += 1
        return sent
