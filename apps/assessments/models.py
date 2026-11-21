from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.competencies.models import LEVELS, BehavioralIndicator, Competency, CompetencyModel
from apps.employees.models import Employee
from apps.institutions.models import Institution

from . import scoring
from .forms_config import FormType, get_form


class Status(models.TextChoices):
    DRAFT = 'DRAFT', 'Szkic — dobór kryteriów'
    CRITERIA_SET = 'CRITERIA_SET', 'Kryteria ustalone — ocena w toku'
    INTERVIEW_DONE = 'INTERVIEW_DONE', 'Rozmowa oceniająca przeprowadzona'
    FINALIZED = 'FINALIZED', 'Ocena sporządzona'
    APPROVED = 'APPROVED', 'Potwierdzona przez kierującego komórką'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Oceniany zapoznał się z oceną'
    CANCELLED = 'CANCELLED', 'Anulowana'


class ExamStatus(models.TextChoices):
    PASSED = 'PASSED', 'Tak'
    FAILED = 'FAILED', 'Nie'
    NOT_APPLICABLE = 'NA', 'Nie dotyczy'


class Result(models.TextChoices):
    POSITIVE = scoring.POSITIVE, 'Pozytywna'
    NEGATIVE = scoring.NEGATIVE, 'Negatywna'


class Assessment(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='assessments')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='assessments')
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name='assessments_as_evaluator', verbose_name='oceniający')
    unit_head = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='assessments_as_unit_head', verbose_name='kierujący komórką')
    competency_model = models.ForeignKey(CompetencyModel, on_delete=models.PROTECT)
    form_type = models.CharField(max_length=20, choices=FormType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Ustalenie kryteriów: rozmowa § 5 (okresowa) / rozmowa wstępna § 3 (pierwsza)
    criteria_interview_date = models.DateField('data rozmowy ustalającej kryteria / wstępnej', null=True, blank=True)
    due_date = models.DateField('termin sporządzenia oceny', null=True, blank=True)
    expectations = models.TextField('oczekiwania przełożonego', blank=True)
    goals = models.TextField('cele na okres oceny', blank=True)

    # Pierwsza ocena
    report_deadline_from = models.DateField('termin sprawozdania — od', null=True, blank=True)
    report_deadline_to = models.DateField('termin sprawozdania — do', null=True, blank=True)
    window_from = models.DateField('okres dokonania pierwszej oceny — od', null=True, blank=True)
    window_to = models.DateField('okres dokonania pierwszej oceny — do', null=True, blank=True)
    report_text = models.TextField('sprawozdanie ocenianego', blank=True)
    report_on_time = models.BooleanField('sprawozdanie złożone w terminie', null=True, blank=True)
    prep_exam = models.CharField('egzamin ze służby przygotowawczej', max_length=10,
                                 choices=ExamStatus.choices, blank=True)

    # Rozmowa oceniająca i wynik
    period_from = models.DateField('okres podlegania ocenie — od', null=True, blank=True)
    period_to = models.DateField('okres podlegania ocenie — do', null=True, blank=True)
    evaluation_interview_date = models.DateField('data rozmowy oceniającej', null=True, blank=True)
    interview_notes = models.TextField('notatki z rozmowy oceniającej', blank=True)
    interview_plan = models.JSONField('scenariusz rozmowy (zatwierdzony przez przełożonego)', null=True, blank=True)
    average = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    level = models.PositiveSmallIntegerField(null=True, blank=True)
    result = models.CharField(max_length=10, choices=Result.choices, blank=True)
    justification = models.TextField('uzasadnienie przyznanej oceny', blank=True)
    development_conclusions = models.TextField('wnioski dotyczące rozwoju zawodowego', blank=True)

    # Okresowa — dane poprzedniej oceny i wniosek o stopień (część III)
    previous_result = models.CharField(max_length=10, choices=Result.choices, blank=True)
    previous_level = models.CharField(max_length=40, blank=True)
    previous_date = models.DateField(null=True, blank=True)
    promotion_request = models.BooleanField('wniosek o kolejny stopień służbowy', null=True, blank=True)
    promotion_grade = models.CharField(max_length=50, blank=True)
    promotion_motivation = models.TextField(blank=True)

    finalized_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')
    acknowledged_on = models.DateField('data zapoznania się z oceną', null=True, blank=True)
    objection_filed_on = models.DateField('data wniesienia sprzeciwu', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'ocena'
        verbose_name_plural = 'oceny'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['institution', 'status'])]

    def __str__(self):
        return f'{self.get_form_type_display()} — {self.employee}'

    @property
    def form(self):
        return get_form(self.form_type)

    @property
    def is_first(self):
        return self.form_type == FormType.FIRST

    @property
    def is_locked(self):
        return self.status in (Status.FINALIZED, Status.APPROVED, Status.ACKNOWLEDGED, Status.CANCELLED)

    def ordered_criteria(self):
        return self.criteria.select_related('competency').order_by('-is_mandatory', 'order')

    def summary(self) -> scoring.ScoreSummary:
        scores = [c.score for c in self.criteria.all()]
        if self.is_first:
            exam = {ExamStatus.PASSED: True, ExamStatus.FAILED: False}.get(self.prep_exam, None)
            if not self.prep_exam:
                summary = scoring.first_summary(scores, exam_passed=None, report_on_time=self.report_on_time)
                if summary.complete:
                    summary.complete = False
                    summary.reasons.append('Nie określono wyniku egzaminu ze służby przygotowawczej.')
                return summary
            return scoring.first_summary(scores, exam_passed=exam, report_on_time=self.report_on_time)
        return scoring.periodic_summary(scores)


class AssessmentCriterion(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='criteria')
    competency = models.ForeignKey(Competency, on_delete=models.PROTECT)
    is_mandatory = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    selected_indicators = models.ManyToManyField(BehavioralIndicator, blank=True, related_name='+')
    score = models.PositiveSmallIntegerField('ocena cząstkowa (pkt)', null=True, blank=True)
    justification = models.TextField('uzasadnienie oceny cząstkowej', blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-is_mandatory', 'order']
        constraints = [models.UniqueConstraint(fields=['assessment', 'competency'], name='uniq_assessment_comp')]

    def __str__(self):
        return f'{self.competency} ({self.assessment_id})'


class BehavioralEvidence(models.Model):
    """Konkretny przykład zachowania z okresu oceny: sytuacja — działanie — rezultat."""

    criterion = models.ForeignKey(AssessmentCriterion, on_delete=models.CASCADE, related_name='evidence')
    indicator = models.ForeignKey(BehavioralIndicator, null=True, blank=True, on_delete=models.SET_NULL)
    situation = models.TextField('sytuacja')
    action = models.TextField('działanie', blank=True)
    result = models.TextField('rezultat', blank=True)
    occurred_on = models.DateField(null=True, blank=True)
    is_positive = models.BooleanField(null=True, blank=True, help_text='mocna strona / obszar do rozwoju')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['occurred_on', 'created_at']


class IndicatorRating(models.Model):
    """Pomocnicza ocena przełożonego na poziomie wskaźnika (1–5) albo „brak podstaw do oceny”."""

    criterion = models.ForeignKey(AssessmentCriterion, on_delete=models.CASCADE, related_name='ratings')
    indicator = models.ForeignKey(BehavioralIndicator, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField(choices=LEVELS, null=True, blank=True)
    no_basis = models.BooleanField('brak podstaw do oceny', default=False)
    history = HistoricalRecords()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['criterion', 'indicator'], name='uniq_rating')]
