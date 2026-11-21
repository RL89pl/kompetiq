from django.contrib import admin

from .models import BehavioralIndicator, Competency, CompetencyModel, IndicatorLevelDescription


class LevelInline(admin.TabularInline):
    model = IndicatorLevelDescription
    extra = 0


@admin.register(CompetencyModel)
class CompetencyModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'institution', 'is_active')


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'model', 'order')
    list_filter = ('model',)


@admin.register(BehavioralIndicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'competency')
    list_filter = ('competency__model', 'competency')
    inlines = [LevelInline]
