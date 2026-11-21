from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.assessments.models import Assessment
from apps.competencies.models import Competency


class DevelopmentPlan(models.Model):
    assessment = models.OneToOneField(Assessment, on_delete=models.CASCADE, related_name='development_plan')
    summary = models.TextField('wnioski / cel rozwojowy', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'plan rozwoju'
        verbose_name_plural = 'plany rozwoju'

    def progress(self):
        total = self.actions.exclude(status=DevelopmentAction.Status.CANCELLED).count()
        done = self.actions.filter(status=DevelopmentAction.Status.DONE).count()
        return {'total': total, 'done': done, 'percent': round(100 * done / total) if total else 0}


class DevelopmentAction(models.Model):
    class Type(models.TextChoices):
        ON_THE_JOB = 'ON_THE_JOB', 'Zadanie rozwojowe w pracy'
        MENTORING = 'MENTORING', 'Mentoring'
        COACHING = 'COACHING', 'Coaching'
        TRAINING = 'TRAINING', 'Szkolenie'
        SELF_STUDY = 'SELF_STUDY', 'Samokształcenie'
        FEEDBACK = 'FEEDBACK', 'Regularna informacja zwrotna'

    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Zaplanowane'
        IN_PROGRESS = 'IN_PROGRESS', 'W realizacji'
        DONE = 'DONE', 'Zrealizowane'
        CANCELLED = 'CANCELLED', 'Anulowane'

    plan = models.ForeignKey(DevelopmentPlan, on_delete=models.CASCADE, related_name='actions')
    competency = models.ForeignKey(Competency, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.ON_THE_JOB)
    success_measure = models.TextField('miernik sukcesu', blank=True)
    owner = models.CharField('odpowiedzialny', max_length=255, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    from_ai_suggestion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['due_date', 'created_at']


class ProgressNote(models.Model):
    action = models.ForeignKey(DevelopmentAction, on_delete=models.CASCADE, related_name='notes')
    text = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
