from django.conf import settings
from django.db import models

from apps.assessments.models import Assessment
from apps.institutions.models import Institution


class AIInteraction(models.Model):
    """Rejestr użycia asystenta AI — rozliczalność: co zasugerowano, czy przełożony przyjął sugestię."""

    class Outcome(models.TextChoices):
        PENDING = 'PENDING', 'Oczekuje'
        ACCEPTED = 'ACCEPTED', 'Przyjęta'
        EDITED = 'EDITED', 'Przyjęta po edycji'
        REJECTED = 'REJECTED', 'Odrzucona'

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    assessment = models.ForeignKey(Assessment, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='ai_interactions')
    feature = models.CharField(max_length=50)
    model = models.CharField(max_length=64)
    request_digest = models.CharField(max_length=64)
    response = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class LegalChunk(models.Model):
    """Fragment bazy wiedzy asystenta: ustawa, rozporządzenia, poradniki, model kompetencji, pytania i odpowiedzi."""

    class Kind(models.TextChoices):
        ACT = 'ACT', 'Ustawa'
        REGULATION = 'REGULATION', 'Rozporządzenie'
        GUIDE = 'GUIDE', 'Poradnik'
        MODEL = 'MODEL', 'Model kompetencji'
        FAQ = 'FAQ', 'Pytania i odpowiedzi'
        OTHER = 'OTHER', 'Inne'

    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.OTHER)
    source = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    page = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ['source', 'page']


class GuidingQuestionCache(models.Model):
    indicator = models.OneToOneField('competencies.BehavioralIndicator', on_delete=models.CASCADE)
    questions = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class Conversation(models.Model):
    """Rozmowa przełożonego z asystentem — tryb formalny albo przygotowanie do rozmowy z pracownikiem."""

    class Mode(models.TextChoices):
        FORMAL = 'FORMAL', 'Zasady i wymagania formalne'
        INTERVIEW = 'INTERVIEW', 'Przygotowanie do rozmowy z pracownikiem'

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations')
    assessment = models.ForeignKey(Assessment, null=True, blank=True, on_delete=models.CASCADE,
                                   related_name='ai_conversations')
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.FORMAL)
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'Przełożony'
        ASSISTANT = 'assistant', 'Asystent'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    citations = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    grounded = models.BooleanField(default=True, help_text='False = brak informacji w bazie wiedzy')
    interaction = models.ForeignKey(AIInteraction, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
