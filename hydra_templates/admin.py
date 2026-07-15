from django.contrib import admin

from hydra_templates.models import MessageTemplate, TemplateDataExport


class ReadOnlyHydraTemplateAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MessageTemplate)
class MessageTemplateAdmin(ReadOnlyHydraTemplateAdmin):
    list_display = ("code", "name", "company", "language", "is_active")
    list_filter = ("company", "language", "is_active")
    search_fields = ("code", "name", "subject")


@admin.register(TemplateDataExport)
class TemplateDataExportAdmin(ReadOnlyHydraTemplateAdmin):
    list_display = ("filename", "actor", "row_count", "occurred_at", "sha256")
    search_fields = ("filename", "actor__username", "sha256")
    readonly_fields = (
        "uuid",
        "actor",
        "occurred_at",
        "filename",
        "row_count",
        "sha256",
        "filters",
        "scope_company_ids",
    )
