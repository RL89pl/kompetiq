"""Backend poczty Django wysyłający przez EmailLabs REST API (https://api.emaillabs.net.pl/api/new_sendmail)."""
import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parseaddr

from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)

API_URL = 'https://api.emaillabs.net.pl/api/new_sendmail'


class EmailLabsBackend(BaseEmailBackend):
    def __init__(self, *, smtp_account='', app_key='', secret_key='', timeout=15, **kwargs):
        super().__init__(**kwargs)
        self.smtp_account = smtp_account
        self.timeout = timeout
        token = base64.b64encode(f'{app_key}:{secret_key}'.encode()).decode()
        self.auth_header = f'Basic {token}'

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            self._send(message)
            sent += 1
        return sent

    def _send(self, message):
        from_name, from_email = parseaddr(message.from_email)
        data = {
            'smtp_account': self.smtp_account,
            'subject': message.subject,
            'text': message.body,
            'from': from_email,
        }
        if from_name:
            data['from_name'] = from_name
        for alt in getattr(message, 'alternatives', None) or []:
            if alt[1] == 'text/html':
                data['html'] = alt[0]
        if message.reply_to:
            data['reply_to'] = parseaddr(message.reply_to[0])[1]
        for addr in message.recipients():
            name, email = parseaddr(addr)
            data[f'to[{email}]'] = name

        req = urllib.request.Request(
            API_URL, data=urllib.parse.urlencode(data).encode(), method='POST',
            headers={'Authorization': self.auth_header, 'Content-Type': 'application/x-www-form-urlencoded'},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read() or b'{}')
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'EmailLabs HTTP {e.code}: {e.read()[:300]!r}') from e
        if result.get('status') not in (None, 'success'):
            raise RuntimeError(f'EmailLabs: {result}')
        log.info('E-mail wysłany przez EmailLabs: %s', result.get('data'))
