from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import DevelopmentAction, DevelopmentPlan


class ActionInline(admin.TabularInline):
    model = DevelopmentAction
    extra = 0


@admin.register(DevelopmentPlan)
class PlanAdmin(SimpleHistoryAdmin):
    list_display = ('assessment', 'updated_at')
    inlines = [ActionInline]
