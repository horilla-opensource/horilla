from django.contrib import admin

from hydra_notifications.models import (
    HydraNotificationEmailDelivery,
    HydraNotificationEnvelope,
    HydraNotificationPreference,
    HydraNotificationStateEvent,
)


class ReadOnlyNotificationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)


@admin.register(HydraNotificationEnvelope)
class HydraNotificationEnvelopeAdmin(ReadOnlyNotificationAdmin):
    list_display = (
        "uuid",
        "recipient",
        "kind",
        "severity",
        "read_at",
        "archived_at",
        "occurred_at",
    )
    list_filter = ("kind", "category", "severity", "read_at", "archived_at")
    search_fields = ("uuid", "idempotency_key", "recipient__username")


@admin.register(HydraNotificationStateEvent)
class HydraNotificationStateEventAdmin(ReadOnlyNotificationAdmin):
    list_display = ("envelope", "sequence", "action", "actor", "occurred_at")
    list_filter = ("action",)


@admin.register(HydraNotificationEmailDelivery)
class HydraNotificationEmailDeliveryAdmin(ReadOnlyNotificationAdmin):
    list_display = ("uuid", "recipient", "status", "attempts", "sent_at")
    list_filter = ("status",)
    search_fields = ("uuid", "recipient__username", "error_code")


@admin.register(HydraNotificationPreference)
class HydraNotificationPreferenceAdmin(ReadOnlyNotificationAdmin):
    list_display = (
        "user",
        "email_enabled",
        "email_min_severity",
        "browser_sound_enabled",
        "version",
    )
