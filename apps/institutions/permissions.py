from rest_framework.permissions import BasePermission

from .models import Role


class HasInstitution(BasePermission):
    """Każde żądanie API (poza auth) wymaga aktywnej instytucji."""

    message = 'Brak aktywnej instytucji dla użytkownika.'

    def has_permission(self, request, view):
        if getattr(view, 'skip_institution_check', False):
            return True
        return getattr(request._request, 'membership', None) is not None


def membership(request):
    return getattr(request._request, 'membership', None) if hasattr(request, '_request') else getattr(request, 'membership', None)


class HasRole(BasePermission):
    roles: tuple = ()

    def has_permission(self, request, view):
        m = membership(request)
        return m is not None and m.role in self.roles


class IsInstitutionAdmin(HasRole):
    roles = (Role.ADMIN,)


class IsHROrAdmin(HasRole):
    roles = (Role.HR, Role.ADMIN)
