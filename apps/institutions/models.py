from django.conf import settings
from django.db import models


class Institution(models.Model):
    """Urząd / instytucja — jednostka izolacji danych (tenant)."""

    name = models.CharField('nazwa urzędu', max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'instytucja'
        verbose_name_plural = 'instytucje'
        ordering = ['name']

    def __str__(self):
        return self.name


class OrgUnit(models.Model):
    """Komórka organizacyjna (drzewo)."""

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='org_units')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    name = models.CharField('nazwa komórki', max_length=255)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='headed_units', verbose_name='kierujący komórką',
    )

    class Meta:
        verbose_name = 'komórka organizacyjna'
        verbose_name_plural = 'komórki organizacyjne'
        ordering = ['name']

    def __str__(self):
        return self.name


class Role(models.TextChoices):
    SUPERVISOR = 'SUPERVISOR', 'Bezpośredni przełożony'
    UNIT_HEAD = 'UNIT_HEAD', 'Kierujący komórką organizacyjną'
    HR = 'HR', 'Kadry (HR)'
    ADMIN = 'ADMIN', 'Administrator instytucji'


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SUPERVISOR)
    org_unit = models.ForeignKey(OrgUnit, null=True, blank=True, on_delete=models.SET_NULL)
    position = models.CharField('stanowisko', max_length=255, blank=True)

    class Meta:
        verbose_name = 'członkostwo'
        verbose_name_plural = 'członkostwa'
        constraints = [models.UniqueConstraint(fields=['user', 'institution'], name='uniq_membership')]

    def __str__(self):
        return f'{self.user} @ {self.institution} ({self.get_role_display()})'

    @property
    def sees_all_employees(self):
        return self.role in (Role.HR, Role.ADMIN)
