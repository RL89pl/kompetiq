import io
import os

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from .models import Institution, Membership, OrgUnit, SystemSettings


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

    def get_urls(self):
        return [path('reset-demo/', self.admin_site.admin_view(self.reset_demo_view),
                     name='institutions_institution_reset_demo')] + super().get_urls()

    def reset_demo_view(self, request):
        """Przywraca dane demonstracyjne do stanu początkowego (do wielokrotnego pokazu pełnej ścieżki)."""
        if not request.user.is_superuser:
            raise PermissionDenied
        password = os.environ.get('DEMO_PASSWORD', '')
        if request.method == 'POST' and password:
            out = io.StringIO()
            try:
                call_command('seed_demo', reset=True, password=password, stdout=out)
            except Exception as e:  # noqa: BLE001 — pokazujemy przyczynę w panelu
                messages.error(request, f'Nie udało się przywrócić danych demo: {e}')
            else:
                messages.success(request, 'Przywrócono dane demonstracyjne. Konta: przelozony, kierownik, kadry, admin — '
                                          'hasło z DEMO_PASSWORD w pliku .env.')
            return redirect('admin:institutions_institution_changelist')
        return TemplateResponse(request, 'admin/institutions/institution/reset_demo.html',
                                {**self.admin_site.each_context(request), 'title': 'Przywróć dane demonstracyjne',
                                 'password_set': bool(password)})


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'parent', 'head')
    list_filter = ('institution',)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'role', 'org_unit')
    list_filter = ('institution', 'role')


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """Jeden rekord ustawień: lista od razu otwiera formularz."""
    fieldsets = [('Poczta e-mail', {'fields': ('email_test_mode', 'email_test_address', 'delivery'),
                                   'description': 'Na czas testów wszystkie e-maile z systemu mogą trafiać na jeden '
                                                  'wskazany adres. Kopia każdej wiadomości jest też w „Skrzynce '
                                                  'testowej” w aplikacji.'})]
    readonly_fields = ('delivery',)
    change_form_template = 'admin/institutions/systemsettings/change_form.html'

    @admin.display(description='Wysyłka poczty na serwerze')
    def delivery(self, obj):
        from kompetiq.mail import delivery_description
        return delivery_description()

    def get_urls(self):
        return [path('send-test/', self.admin_site.admin_view(self.send_test), name='institutions_systemsettings_send_test'),
                *super().get_urls()]

    def send_test(self, request):
        """Wysyła jeden e-mail próbny na adres testowy (albo adres zalogowanego) i pokazuje wynik z błędem dostawcy."""
        from django.core.mail import EmailMultiAlternatives
        from apps.deadlines.models import OutgoingEmail
        if request.method != 'POST' or not request.user.is_superuser:
            raise PermissionDenied
        obj = SystemSettings.load()
        target = obj.email_test_address or request.user.email
        if not target:
            messages.error(request, 'Wpisz adres testowy (albo uzupełnij swój e-mail w koncie), aby wysłać próbę.')
            return redirect('admin:institutions_systemsettings_change', obj.pk)
        msg = EmailMultiAlternatives('KompetIQ: e-mail próbny', 'To jest e-mail próbny z panelu ustawień KompetIQ. '
                                     'Skoro go widzisz, wysyłka poczty działa.', None, [target])
        try:
            msg.send()
        except Exception:  # noqa: BLE001 — przyczynę zapisuje skrzynka testowa (OutgoingEmail.error)
            pass
        row = OutgoingEmail.objects.order_by('-id').first()
        if row and row.status in (OutgoingEmail.Status.SENT, OutgoingEmail.Status.REDIRECTED):
            messages.success(request, f'Wysłano e-mail próbny na {row.delivered_to}. Sprawdź skrzynkę (także SPAM).')
        else:
            messages.error(request, 'Nie udało się wysłać e-maila próbnego: '
                                    f'{(row.error if row else "") or "adres w domenie testowej — e-mail został tylko zapisany w skrzynce testowej"}')
        return redirect('admin:institutions_systemsettings_change', obj.pk)

    def changelist_view(self, request, extra_context=None):
        obj = SystemSettings.load()
        return redirect('admin:institutions_systemsettings_change', obj.pk)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
