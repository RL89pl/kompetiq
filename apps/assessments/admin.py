from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Assessment, AssessmentCriterion, BehavioralEvidence


class CriterionInline(admin.TabularInline):
    model = AssessmentCriterion
    extra = 0
    fields = ('competency', 'is_mandatory', 'score')


@admin.register(Assessment)
class AssessmentAdmin(SimpleHistoryAdmin):
    list_display = ('employee', 'form_type', 'status', 'evaluator', 'result', 'due_date', 'institution')
    list_filter = ('institution', 'form_type', 'status', 'result')
    inlines = [CriterionInline]


@admin.register(BehavioralEvidence)
class EvidenceAdmin(SimpleHistoryAdmin):
    list_display = ('criterion', 'indicator', 'occurred_on')
