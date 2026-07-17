from django.contrib import admin

from hydra_ops.models import MaintenanceState


@admin.register(MaintenanceState)
class MaintenanceStateAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "owner_uuid",
        "heartbeat_at",
        "last_success_at",
        "last_legalization_run_at",
        "last_arrival_run_at",
        "last_portal_email_dispatch_at",
        "consecutive_failures",
        "last_error_code",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
