import json
import urllib.parse
from unittest import mock

from django.core.mail import EmailMultiAlternatives

from kompetiq.emaillabs import API_URL, EmailLabsBackend


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps({'status': 'success', 'data': [{'message_id': 'x'}]}).encode()


def test_emaillabs_backend_posts_form():
    backend = EmailLabsBackend(smtp_account='1.acc.smtp', app_key='k', secret_key='s', alias='default')
    msg = EmailMultiAlternatives('Temat', 'Treść', 'KompetIQ <noreply@example.pl>', ['Jan <jan@example.pl>'],
                                 connection=backend)
    msg.attach_alternative('<p>Treść</p>', 'text/html')
    with mock.patch('urllib.request.urlopen', return_value=_Resp()) as urlopen:
        assert msg.send() == 1
    req = urlopen.call_args.args[0]
    assert req.full_url == API_URL
    assert req.get_header('Authorization') == 'Basic azpz'
    form = urllib.parse.parse_qs(req.data.decode())
    assert form['to[jan@example.pl]'] == ['Jan']
    assert form['smtp_account'] == ['1.acc.smtp']
    assert form['from'] == ['noreply@example.pl'] and form['from_name'] == ['KompetIQ']
    assert form['html'] == ['<p>Treść</p>'] and form['text'] == ['Treść']
