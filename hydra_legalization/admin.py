from django.contrib import admin

from hydra_legalization.models import (
    LegalizationCase,
    LegalizationCaseDocument,
    LegalizationStatusHistory,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LegalizationCase)
class LegalizationCaseAdmin(ReadOnlyAdmin):
    list_display = (
        "uuid",
        "person",
        "case_type",
        "status",
        "responsible",
        "deadline",
        "valid_until",
    )
    list_filter = ("case_type", "status", "deadline", "valid_until")
    search_fields = ("uuid", "person__hydra_id", "person__passport_name", "reference_number")


@admin.register(LegalizationStatusHistory)
class LegalizationStatusHistoryAdmin(ReadOnlyAdmin):
    list_display = ("occurred_at", "case", "from_status", "to_status", "actor", "reason")
    list_filter = ("to_status", "occurred_at")


@admin.register(LegalizationCaseDocument)
class LegalizationCaseDocumentAdmin(ReadOnlyAdmin):
    list_display = ("case", "document", "role", "created_at", "created_by")
    list_filter = ("role", "created_at")
