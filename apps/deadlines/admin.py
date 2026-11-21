from django.contrib import admin
from django.utils.html import format_html

from .models import Notification, OutgoingEmail


@admin.register(OutgoingEmail)
class OutgoingEmailAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'subject', 'to', 'status', 'institution')
    list_filter = ('status', 'institution')
    search_fields = ('subject', 'to')
    readonly_fields = ('created_at', 'institution', 'recipient', 'from_email', 'to', 'subject', 'status', 'error',
                       'preview', 'body_text')
    exclude = ('body_html',)

    @admin.display(description='Podgląd')
    def preview(self, obj):
        # srcdoc w izolowanej ramce (sandbox bez skryptów) — treść HTML nie wykonuje się w panelu.
        return format_html('<iframe sandbox srcdoc="{}" style="width:680px;height:640px;border:1px solid #ccc"></iframe>',
                           obj.body_html)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'kind', 'title', 'recipient', 'email_sent', 'read_at')
    list_filter = ('kind', 'institution')
    search_fields = ('title',)
