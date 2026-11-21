from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.institutions.models import Institution, OrgUnit


class FormOfAddress(models.TextChoices):
    UNSPECIFIED = '', 'Nieokreślona (forma neutralna)'
    PANI = 'PANI', 'Pani'
    PAN = 'PAN', 'Pan'


class Employee(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='employees')
    org_unit = models.ForeignKey(OrgUnit, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='komórka')
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='subordinates', verbose_name='bezpośredni przełożony',
    )
    first_name = models.CharField('imię', max_length=100)
    last_name = models.CharField('nazwisko', max_length=100)
    position = models.CharField('stanowisko', max_length=255)
    form_of_address = models.CharField(
        'forma zwracania się', max_length=4, choices=FormOfAddress.choices, blank=True, default='',
        help_text='Wypełnia kadra (np. z systemu kadrowego). Używana w scenariuszach rozmowy i podpowiedziach AI.')
    employment_date = models.DateField('data nawiązania stosunku pracy', null=True, blank=True)
    contract_end_date = models.DateField('data zakończenia umowy (czas określony)', null=True, blank=True)
    is_civil_servant = models.BooleanField('urzędnik służby cywilnej (mianowany)', default=False)
    service_grade = models.CharField('stopień służbowy', max_length=50, blank=True)
    appointment_year = models.PositiveSmallIntegerField('rok mianowania', null=True, blank=True)
    service_grade_date = models.DateField('data przyznania stopnia służbowego', null=True, blank=True)
    is_managerial = models.BooleanField('stanowisko kierownicze (kieruje pracownikami)', default=False)
    is_office_head = models.BooleanField('kierownik urzędu', default=False)
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'pracownik'
        verbose_name_plural = 'pracownicy'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def full_name(self) -> str:
        return str(self)


class JobDescription(models.Model):
    """Opis stanowiska pracy — podstawa doboru formularza, kryteriów i wskaźników."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='job_descriptions')
    symbol = models.CharField('symbol stanowiska', max_length=64, blank=True)
    purpose = models.TextField('cel istnienia stanowiska', blank=True)
    main_duties = models.TextField('główne obowiązki')
    responsibilities = models.TextField('zakres odpowiedzialności i uprawnień', blank=True)
    requirements = models.TextField('wymagania / kompetencje', blank=True)
    subordinates = models.CharField('liczba podległych pracowników', max_length=255, blank=True)
    manages_people = models.BooleanField('stanowisko polega na kierowaniu pracownikami', null=True, blank=True)
    soft_competencies = models.JSONField('kompetencje wskazane w OSP (kody modelu)', default=list, blank=True)
    source_name = models.CharField('plik źródłowy', max_length=255, blank=True)
    file = models.FileField(upload_to='job_descriptions/', blank=True)
    valid_from = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'opis stanowiska'
        verbose_name_plural = 'opisy stanowisk'
        ordering = ['-created_at']

    def as_text(self):
        parts = []
        if self.purpose:
            parts.append(f'Cel istnienia stanowiska:\n{self.purpose}')
        if self.subordinates:
            parts.append(f'Liczba podległych pracowników: {self.subordinates}')
        parts.append(f'Główne zadania:\n{self.main_duties}')
        if self.responsibilities:
            parts.append(f'Zakres odpowiedzialności:\n{self.responsibilities}')
        if self.requirements:
            parts.append(f'Wymagania:\n{self.requirements}')
        return '\n\n'.join(parts)
