from django.contrib import admin

from hydra_reports.models import OperationalReportExport


@admin.register(OperationalReportExport)
class OperationalReportExportAdmin(admin.ModelAdmin):
    list_display = ("filename", "actor", "format", "row_count", "occurred_at")
    search_fields = ("filename", "actor__username", "sha256")
    readonly_fields = (
        "uuid",
        "actor",
        "occurred_at",
        "format",
        "filename",
        "row_count",
        "sha256",
        "filters",
        "scope_location_ids",
        "scope_team_ids",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
