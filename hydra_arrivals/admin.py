from django.contrib import admin

from hydra_arrivals.models import ArrivalPlan, ArrivalStatusHistory


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
