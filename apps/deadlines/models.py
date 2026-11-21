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
