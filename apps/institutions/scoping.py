"""Izolacja danych między instytucjami."""
from .permissions import membership


class InstitutionScopedMixin:
    """Mixin dla ViewSetów: filtruje queryset po aktywnej instytucji.

    Model musi mieć ścieżkę do instytucji wskazaną w `institution_lookup`.
    """

    institution_lookup = 'institution'

    def get_membership(self):
        return membership(self.request)

    def get_institution(self):
        return self.get_membership().institution

    def scope(self, qs):
        return qs.filter(**{self.institution_lookup: self.get_institution()})

    def get_queryset(self):
        return self.scope(super().get_queryset())
