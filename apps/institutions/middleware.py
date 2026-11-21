from .models import Membership

SESSION_KEY = 'institution_id'


class InstitutionMiddleware:
    """Ustawia request.institution i request.membership dla zalogowanego użytkownika.

    Aktywna instytucja jest zapamiętywana w sesji; przy jednym członkostwie wybierana automatycznie.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.institution = None
        request.membership = None
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            memberships = Membership.objects.select_related('institution', 'org_unit').filter(
                user=user, institution__is_active=True
            )
            chosen = None
            wanted = request.session.get(SESSION_KEY)
            if wanted:
                chosen = next((m for m in memberships if m.institution_id == wanted), None)
            if chosen is None:
                ms = list(memberships)
                if len(ms) == 1:
                    chosen = ms[0]
                    request.session[SESSION_KEY] = chosen.institution_id
            if chosen is not None:
                request.membership = chosen
                request.institution = chosen.institution
        return self.get_response(request)
