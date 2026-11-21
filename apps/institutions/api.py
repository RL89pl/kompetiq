from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from kompetiq import openapi as o

from .middleware import SESSION_KEY
from .models import Membership, OrgUnit
from .permissions import membership
from .scoping import InstitutionScopedMixin


class MembershipSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name')
    role_display = serializers.CharField(source='get_role_display')
    org_unit_name = serializers.CharField(source='org_unit.name', default='')

    class Meta:
        model = Membership
        fields = ['id', 'institution', 'institution_name', 'role', 'role_display', 'org_unit', 'org_unit_name', 'position']


def me_payload(request):
    user = request.user
    m = getattr(request, 'membership', None)
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name() or user.username,
        'memberships': MembershipSerializer(user.memberships.select_related('institution', 'org_unit'), many=True).data,
        'active_membership': MembershipSerializer(m).data if m else None,
    }


class LoginThrottle(AnonRateThrottle):
    rate = '20/hour'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=o.CsrfOut, tags=['Uwierzytelnianie'], summary='Token CSRF (ustawia też ciasteczko csrftoken)')
    def get(self, request):
        return Response({'csrfToken': get_token(request)})


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(request=o.LoginIn, responses={200: o.MeOut, 400: o.Detail}, tags=['Uwierzytelnianie'],
                   summary='Logowanie (sesja w ciasteczku sessionid)')
    def post(self, request):
        user = authenticate(request, username=request.data.get('username'), password=request.data.get('password'))
        if user is None:
            return Response({'detail': 'Nieprawidłowy login lub hasło.'}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        ms = list(user.memberships.filter(institution__is_active=True))
        if len(ms) >= 1:
            request.session[SESSION_KEY] = ms[0].institution_id
            request._request.membership = ms[0]
        return Response(me_payload(request._request))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    skip_institution_check = True

    @extend_schema(request=None, responses={204: None}, tags=['Uwierzytelnianie'], summary='Wylogowanie')
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    skip_institution_check = True

    @extend_schema(responses=o.MeOut, tags=['Uwierzytelnianie'], summary='Zalogowany użytkownik i jego członkostwa w instytucjach')
    def get(self, request):
        return Response(me_payload(request._request))


class SwitchInstitutionView(APIView):
    permission_classes = [IsAuthenticated]
    skip_institution_check = True

    @extend_schema(request=o.SwitchInstitutionIn, responses={200: o.MeOut, 403: o.Detail}, tags=['Uwierzytelnianie'],
                   summary='Przełączenie aktywnej instytucji')
    def post(self, request):
        m = request.user.memberships.filter(institution_id=request.data.get('institution')).first()
        if m is None:
            return Response({'detail': 'Brak dostępu do tej instytucji.'}, status=status.HTTP_403_FORBIDDEN)
        request.session[SESSION_KEY] = m.institution_id
        request._request.membership = m
        return Response(me_payload(request._request))


class OrgUnitSerializer(serializers.ModelSerializer):
    head_name = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = ['id', 'name', 'parent', 'head', 'head_name']

    def get_head_name(self, obj) -> str:
        return obj.head.get_full_name() if obj.head else ''


class OrgUnitViewSet(InstitutionScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = OrgUnit.objects.select_related('head')
    serializer_class = OrgUnitSerializer
    pagination_class = None


class InstitutionUsersView(APIView):
    """Lista osób w instytucji (np. wybór kierującego komórką)."""

    @extend_schema(responses=o.InstitutionUserOut(many=True), tags=['Instytucja'])
    def get(self, request):
        m = membership(request)
        rows = Membership.objects.filter(institution=m.institution).select_related('user', 'org_unit')
        return Response([
            {'id': r.user_id, 'full_name': r.user.get_full_name() or r.user.username, 'role': r.role,
             'role_display': r.get_role_display(), 'org_unit': r.org_unit_id, 'position': r.position}
            for r in rows
        ])
