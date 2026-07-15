from django.contrib import admin

from hydra_people.models import EmployeeConversion, Person, PersonApplication


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "hydra_id",
        "passport_name",
        "date_of_birth",
        "citizenship",
        "lifecycle_state",
        "employee",
        "is_active",
    )
    list_filter = ("lifecycle_state", "citizenship", "preferred_language", "is_active")
    search_fields = ("hydra_id", "passport_name", "first_name", "last_name", "email")
    readonly_fields = (
        "uuid",
        "hydra_id",
        "employee",
        "created_at",
        "created_by",
        "modified_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PersonApplication)
class PersonApplicationAdmin(admin.ModelAdmin):
    list_display = ("person", "candidate", "created_at", "created_by")
    search_fields = (
        "person__hydra_id",
        "person__passport_name",
        "candidate__name",
        "candidate__email",
    )
    readonly_fields = ("created_at", "created_by", "modified_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmployeeConversion)
class EmployeeConversionAdmin(admin.ModelAdmin):
    list_display = ("person", "employee", "candidate", "source", "actor", "occurred_at")
    search_fields = (
        "person__hydra_id",
        "person__passport_name",
        "employee__email",
        "candidate__email",
    )
    readonly_fields = (
        "person",
        "employee",
        "candidate",
        "source",
        "actor",
        "source_snapshot",
        "field_decisions",
        "occurred_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
