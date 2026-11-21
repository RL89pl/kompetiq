from django.contrib import admin

from .models import Institution, Membership, OrgUnit


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'parent', 'head')
    list_filter = ('institution',)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'role', 'org_unit')
    list_filter = ('institution', 'role')
