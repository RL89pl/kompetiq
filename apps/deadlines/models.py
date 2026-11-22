from django.conf import settings
from django.db import models

from apps.assessments.models import Assessment
from apps.institutions.models import Institution


class Notification(models.Model):
    """Powiadomienie w aplikacji (opcjonalnie także e-mail): przypomnienia o terminach i komunikacja w procesie."""

    class Kind(models.TextChoices):
        REMINDER = 'REMINDER', 'Przypomnienie o terminie'
        APPROVAL = 'APPROVAL', 'Prośba o potwierdzenie'
        STATUS = 'STATUS', 'Zmiana statusu oceny'
        MESSAGE = 'MESSAGE', 'Wiadomość'

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='+')
    assessment = models.ForeignKey(Assessment, null=True, blank=True, on_delete=models.CASCADE,
                                   related_name='notifications')
    kind = models.CharField(max_length=10, choices=Kind.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    dedupe_key = models.CharField(max_length=120, blank=True, db_index=True)
    email_sent = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class OutgoingEmail(models.Model):
    """Skrzynka testowa: kopia każdego e-maila wysłanego przez system.

    Wiadomości do adresów w domenach testowych (EMAIL_CAPTURE_DOMAINS, domyślnie `.test` — konta demo) nie wychodzą
    na zewnątrz, tylko trafiają tutaj. Pozostałe są wysyłane normalnie, a kopia zostaje do podglądu.
    """

    class Status(models.TextChoices):
        CAPTURED = 'CAPTURED', 'Przechwycony (adres testowy)'
        SENT = 'SENT', 'Wysłany'
        REDIRECTED = 'REDIRECTED', 'Wysłany na adres testowy'
        FAILED = 'FAILED', 'Błąd wysyłki'

    institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='+')
    # kto spowodował wysyłkę (np. autor wiadomości) — widzi ten e-mail w swojej skrzynce testowej
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='+')
    from_email = models.CharField(max_length=255)
    to = models.CharField('adresaci', max_length=1000)
    delivered_to = models.CharField('faktycznie wysłano do', max_length=1000, blank=True)
    subject = models.CharField('temat', max_length=255)
    body_text = models.TextField('treść (tekst)')
    body_html = models.TextField('treść (HTML)', blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'e-mail (skrzynka testowa)'
        verbose_name_plural = 'skrzynka testowa e-mail'

    def __str__(self):
        return f'{self.subject} → {self.to}'
