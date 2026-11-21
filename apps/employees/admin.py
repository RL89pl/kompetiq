from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Employee, JobDescription


class JobDescriptionInline(admin.StackedInline):
    model = JobDescription
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(SimpleHistoryAdmin):
    list_display = ('last_name', 'first_name', 'form_of_address', 'position', 'institution', 'org_unit', 'supervisor')
    list_filter = ('institution', 'is_managerial', 'is_civil_servant')
    search_fields = ('last_name', 'first_name', 'position')
    inlines = [JobDescriptionInline]
