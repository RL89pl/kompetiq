"""Treść e-maili z powiadomień: wersja HTML (układ tabelaryczny, style inline — działa w Outlooku i Gmailu)
i wersja tekstowa.

Minimalizacja danych: e-mail zawiera tylko tytuł powiadomienia i odesłanie do aplikacji. Nie zawiera ocen,
uzasadnień ani treści wiadomości — te są widoczne dopiero po zalogowaniu.
"""
from html import escape

from django.conf import settings

from .models import Notification

INTRO = {
    Notification.Kind.REMINDER: 'Przypominamy o terminie w procesie oceny.',
    Notification.Kind.APPROVAL: 'Ocena czeka na potwierdzenie.',
    Notification.Kind.STATUS: 'Zmienił się etap oceny, w której Pani/Pan uczestniczy.',
    Notification.Kind.MESSAGE: 'W sprawie oceny przesłano nową wiadomość.',
}
ACTION = {
    Notification.Kind.REMINDER: 'Przejdź do oceny',
    Notification.Kind.APPROVAL: 'Potwierdź ocenę',
    Notification.Kind.STATUS: 'Zobacz ocenę',
    Notification.Kind.MESSAGE: 'Przeczytaj wiadomość',
}
PRIVACY = ('Ze względu na ochronę danych osobowych wiadomość nie zawiera treści oceny. '
           'Szczegóły są dostępne po zalogowaniu do aplikacji.')


def link_for(n: Notification) -> str:
    path = f'/oceny/{n.assessment_id}' if n.assessment_id else '/powiadomienia'
    return settings.APP_URL + path


def render(n: Notification):
    """Zwraca (temat, tekst, html)."""
    subject = f'KompetIQ: {n.title}'
    intro = INTRO.get(n.kind, '')
    action = ACTION.get(n.kind, 'Otwórz KompetIQ')
    url = link_for(n)
    sender = n.sender.get_full_name() if n.sender else ''
    inst = n.institution.name
    kind_label = n.get_kind_display()

    text = '\n'.join(x for x in [
        'Dzień dobry,', '', intro, '', n.title, f'Nadawca: {sender}' if sender else '', '',
        f'{action}: {url}', '', PRIVACY, '', '—',
        f'KompetIQ · {inst}', 'Wiadomość wysłana automatycznie. Prosimy na nią nie odpowiadać.',
    ] if x is not None)

    e = escape
    sender_row = (f'<tr><td style="padding:0 0 4px;font-size:14px;color:#4a5670;">Nadawca: '
                  f'<strong style="color:#17233b;">{e(sender)}</strong></td></tr>' if sender else '')
    html = f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(subject)}</title></head>
<body style="margin:0;padding:0;background:#f2f4f8;">
<div style="display:none;max-height:0;overflow:hidden;color:#f2f4f8;">{e(intro)} {e(n.title)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f4f8;">
<tr><td align="center" style="padding:32px 16px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#ffffff;border:1px solid #dde2ea;border-radius:10px;overflow:hidden;font-family:Segoe UI,Arial,Helvetica,sans-serif;color:#17233b;">
    <tr><td style="background:#17233b;padding:22px 32px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:bold;color:#ffffff;">KompetIQ</td>
        <td align="right" style="font-size:13px;color:#c9d3e6;">{e(inst)}</td>
      </tr></table>
    </td></tr>
    <tr><td style="height:4px;background:#1e5fa8;line-height:4px;font-size:0;">&nbsp;</td></tr>
    <tr><td style="padding:32px 32px 8px;">
      <p style="margin:0 0 6px;font-size:12px;font-weight:bold;letter-spacing:1.5px;text-transform:uppercase;color:#1e5fa8;">{e(kind_label)}</p>
      <p style="margin:0 0 10px;font-size:16px;line-height:1.5;">Dzień dobry,</p>
      <p style="margin:0 0 18px;font-size:16px;line-height:1.5;">{e(intro)}</p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f7f8fb;border-left:4px solid #1e5fa8;border-radius:4px;">
        <tr><td style="padding:16px 18px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr><td style="padding:0 0 6px;font-family:Georgia,'Times New Roman',serif;font-size:19px;line-height:1.35;font-weight:bold;color:#17233b;">{e(n.title)}</td></tr>
            {sender_row}
          </table>
        </td></tr>
      </table>
    </td></tr>
    <tr><td style="padding:22px 32px 8px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td style="border-radius:6px;background:#17233b;">
          <a href="{e(url)}" style="display:inline-block;padding:13px 24px;font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:6px;">{e(action)}</a>
        </td></tr></table>
      <p style="margin:14px 0 0;font-size:13px;line-height:1.5;color:#4a5670;">Jeśli przycisk nie działa, skopiuj adres do przeglądarki:<br>
        <a href="{e(url)}" style="color:#1e5fa8;word-break:break-all;">{e(url)}</a></p>
    </td></tr>
    <tr><td style="padding:22px 32px 30px;">
      <p style="margin:0;padding:14px 16px;background:#e7f4ec;border-radius:6px;font-size:13px;line-height:1.5;color:#2e7d4f;">{e(PRIVACY)}</p>
    </td></tr>
    <tr><td style="padding:18px 32px;border-top:1px solid #dde2ea;background:#f7f8fb;font-size:12px;line-height:1.6;color:#4a5670;">
      KompetIQ · Kompas Kompetencji — ocena kompetencji w służbie cywilnej<br>
      Wiadomość wysłana automatycznie. Prosimy na nią nie odpowiadać.
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""
    return subject, text, html
