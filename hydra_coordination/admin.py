from django.contrib import admin

from hydra_coordination.models import (
    Location,
    PersonAssignment,
    ScopeGrant,
    Section,
    Team,
)


class ReadOnlyHydraAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "created_by", "modified_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Location)
class LocationAdmin(ReadOnlyHydraAdmin):
    list_display = ("code", "name", "company", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name", "company__company")


@admin.register(Section)
class SectionAdmin(ReadOnlyHydraAdmin):
    list_display = ("code", "name", "location", "department", "is_active")
    list_filter = ("location__company", "location", "is_active")


@admin.register(Team)
class TeamAdmin(ReadOnlyHydraAdmin):
    list_display = ("code", "name", "section", "is_active")
    list_filter = ("section__location", "is_active")


@admin.register(ScopeGrant)
class ScopeGrantAdmin(ReadOnlyHydraAdmin):
    list_display = ("user", "scope_type", "target", "valid_from", "valid_until", "is_active")
    list_filter = ("is_active", "valid_from")


@admin.register(PersonAssignment)
class PersonAssignmentAdmin(ReadOnlyHydraAdmin):
    list_display = ("person", "team", "department", "valid_from", "valid_until", "is_primary", "is_active")
    list_filter = ("is_primary", "is_active", "department")
