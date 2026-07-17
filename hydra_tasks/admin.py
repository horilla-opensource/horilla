from django.contrib import admin

from hydra_tasks.models import (
    HydraTask,
    HydraTaskEvent,
    HydraTaskNotificationDelivery,
)
from hydra_tasks.selectors import tasks_for_user


class ReadOnlyScopedAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HydraTask)
class HydraTaskAdmin(ReadOnlyScopedAdmin):
    list_display = (
        "uuid",
        "person",
        "company",
        "assignee",
        "status",
        "priority",
        "due_at",
    )
    list_filter = ("status", "priority", "company")
    search_fields = ("person__hydra_id", "title", "target_label")

    def get_queryset(self, request):
        return tasks_for_user(user=request.user)


@admin.register(HydraTaskEvent)
class HydraTaskEventAdmin(ReadOnlyScopedAdmin):
    list_display = ("uuid", "task", "sequence", "action", "actor", "occurred_at")
    list_filter = ("action",)

    def get_queryset(self, request):
        visible = tasks_for_user(user=request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(task_id__in=visible)

@admin.register(HydraTaskNotificationDelivery)
class HydraTaskNotificationDeliveryAdmin(ReadOnlyScopedAdmin):
    list_display = ("uuid", "task", "recipient", "status", "attempts")
    list_filter = ("status",)

    def get_queryset(self, request):
        visible = tasks_for_user(user=request.user).values_list("pk", flat=True)
        return super().get_queryset(request).filter(task_id__in=visible)
