from django.db import models

from apps.institutions.models import Institution

LEVELS = [
    (1, 'Znacznie poniżej oczekiwań'),
    (2, 'Poniżej oczekiwań'),
    (3, 'Na poziomie oczekiwań'),
    (4, 'Powyżej oczekiwań'),
    (5, 'Znacznie powyżej oczekiwań'),
]
LEVEL_LABELS = dict(LEVELS)


class CompetencyModel(models.Model):
    """Wersja modelu kompetencji. institution=None oznacza model wspólny (globalny)."""

    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    institution = models.ForeignKey(Institution, null=True, blank=True, on_delete=models.CASCADE,
                                    related_name='competency_models')
    is_active = models.BooleanField(default=True)
    guidance = models.TextField('wskazówki stosowania', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'model kompetencji'
        verbose_name_plural = 'modele kompetencji'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} {self.version}'

    @classmethod
    def active_for(cls, institution):
        own = cls.objects.filter(institution=institution, is_active=True).first()
        return own or cls.objects.filter(institution__isnull=True, is_active=True).first()


class Competency(models.Model):
    model = models.ForeignKey(CompetencyModel, on_delete=models.CASCADE, related_name='competencies')
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'kompetencja'
        verbose_name_plural = 'kompetencje'
        ordering = ['order']
        constraints = [models.UniqueConstraint(fields=['model', 'code'], name='uniq_competency_code')]

    def __str__(self):
        return self.name


class BehavioralIndicator(models.Model):
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE, related_name='indicators')
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'wskaźnik behawioralny'
        verbose_name_plural = 'wskaźniki behawioralne'
        ordering = ['competency__order', 'order']

    def __str__(self):
        return self.text[:80]


class IndicatorLevelDescription(models.Model):
    indicator = models.ForeignKey(BehavioralIndicator, on_delete=models.CASCADE, related_name='levels')
    level = models.PositiveSmallIntegerField(choices=LEVELS)
    text = models.TextField()

    class Meta:
        ordering = ['level']
        constraints = [models.UniqueConstraint(fields=['indicator', 'level'], name='uniq_indicator_level')]
