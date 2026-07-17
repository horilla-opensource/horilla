from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from hydra_arrivals.models import (
    ArrivalAutomationEvent,
    ArrivalPlan,
    ArrivalStatusHistory,
    OnboardingHandoff,
    OnboardingHandoffEvent,
    OnboardingPortalDelivery,
    OnboardingPortalDeliveryEvent,
)
from hydra_arrivals.portal_email import (
    PORTAL_EMAIL_QUEUE_PERMISSIONS,
    retry_portal_delivery,
)
from hydra_people.recruitment_selectors import linked_candidates_for_user


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArrivalPlan)
class ArrivalPlanAdmin(ReadOnlyAdmin):
    list_display = (
        "uuid",
        "person",
        "destination_location",
        "planned_at",
        "coordinator",
        "status",
        "actual_arrived_at",
    )
    list_filter = ("status", "transport_type", "destination_location", "planned_at")
    search_fields = (
        "uuid",
        "person__hydra_id",
        "person__passport_name",
        "candidate__email",
        "transport_reference",
    )


@admin.register(ArrivalStatusHistory)
class ArrivalStatusHistoryAdmin(ReadOnlyAdmin):
    list_display = (
        "occurred_at",
        "plan",
        "from_status",
        "to_status",
        "actor",
        "reason",
    )
    list_filter = ("to_status", "occurred_at")


@admin.register(ArrivalAutomationEvent)
class ArrivalAutomationEventAdmin(ReadOnlyAdmin):
    list_display = (
        "occurred_at",
        "plan",
        "event_type",
        "planned_at",
        "threshold_minutes",
        "recipient",
        "notification_status",
        "notification_attempts",
    )
    list_filter = ("event_type", "notification_status", "occurred_at")
    search_fields = ("uuid", "plan__uuid", "recipient__username")


@admin.register(OnboardingHandoff)
class OnboardingHandoffAdmin(ReadOnlyAdmin):
    list_display = (
        "initiated_at",
        "person",
        "arrival",
        "status",
        "employee_conversion",
        "person_assignment",
        "completed_at",
    )
    list_filter = ("status", "initiated_at", "completed_at")
    search_fields = ("uuid", "person__hydra_id", "candidate__email")


@admin.register(OnboardingHandoffEvent)
class OnboardingHandoffEventAdmin(ReadOnlyAdmin):
    list_display = ("occurred_at", "handoff", "event_type", "source", "actor")
    list_filter = ("event_type", "source", "occurred_at")


@admin.register(OnboardingPortalDelivery)
class OnboardingPortalDeliveryAdmin(ReadOnlyAdmin):
    list_display = (
        "requested_at",
        "uuid",
        "candidate",
        "status",
        "attempts",
        "last_attempt_at",
        "sent_at",
        "onboarding_started_at",
        "last_error_code",
    )
    list_filter = ("status", "requested_at", "sent_at")
    search_fields = ("uuid", "candidate__email")
    exclude = (
        "recipient",
        "sender",
        "reply_to",
        "subject",
        "body_html",
        "portal_token",
    )
    actions = ("retry_selected_deliveries",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(
            candidate__in=linked_candidates_for_user(user=request.user)
        )

    @admin.action(description="Retry selected failed portal emails")
    def retry_selected_deliveries(self, request, queryset):
        retried = rejected = 0
        for delivery in queryset.only("uuid"):
            try:
                retry_portal_delivery(delivery_uuid=delivery.uuid, actor=request.user)
            except (PermissionDenied, ValidationError):
                rejected += 1
            else:
                retried += 1
        if retried:
            self.message_user(request, f"Queued {retried} portal email(s) for retry.")
        if rejected:
            self.message_user(
                request,
                f"Could not retry {rejected} portal email(s).",
                level=messages.WARNING,
            )

    retry_selected_deliveries.allowed_permissions = ("retry",)

    def has_retry_permission(self, request):
        return request.user.has_perms(
            PORTAL_EMAIL_QUEUE_PERMISSIONS
            + ("hydra_arrivals.retry_onboardingportaldelivery",)
        )


@admin.register(OnboardingPortalDeliveryEvent)
class OnboardingPortalDeliveryEventAdmin(ReadOnlyAdmin):
    list_display = (
        "occurred_at",
        "delivery",
        "event_type",
        "attempt",
        "actor",
        "error_code",
    )
    list_filter = ("event_type", "occurred_at")
    search_fields = ("delivery__uuid",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(
            delivery__candidate__in=linked_candidates_for_user(user=request.user)
        )
