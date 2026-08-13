from django.contrib import admin

from report.models import (
    ReportAccess,
    ReportFavorite,
    ReportFilterPreset,
    ReportRunLog,
    ReportSubscription,
    ReportTemplate,
)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "report_slug",
        "visibility",
        "is_standard",
        "created_by",
        "company_id",
    )
    list_filter = ("visibility", "is_standard", "report_slug")
    search_fields = ("name", "report_slug")


@admin.register(ReportSubscription)
class ReportSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "report_slug",
        "frequency",
        "is_active",
        "last_run_at",
        "owner",
    )
    list_filter = ("frequency", "is_active", "report_slug")
    search_fields = ("name", "recipients", "report_slug")


@admin.register(ReportFavorite)
class ReportFavoriteAdmin(admin.ModelAdmin):
    list_display = ("report_slug", "user", "company_id", "created_at")
    list_filter = ("report_slug",)
    search_fields = ("report_slug", "user__username")


@admin.register(ReportFilterPreset)
class ReportFilterPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "report_slug", "user", "company_id", "created_at")
    list_filter = ("report_slug",)
    search_fields = ("name", "report_slug", "user__username")


@admin.register(ReportRunLog)
class ReportRunLogAdmin(admin.ModelAdmin):
    list_display = ("report_slug", "action", "user", "created_at", "company_id")
    list_filter = ("action", "report_slug")
    search_fields = ("report_slug", "user__username")
    readonly_fields = ("created_at",)


@admin.register(ReportAccess)
class ReportAccessAdmin(admin.ModelAdmin):
    list_display = (
        "report_slug",
        "domain",
        "group",
        "permission",
        "can_view",
        "can_export",
        "can_subscribe",
        "company_id",
        "is_active",
    )
    list_filter = ("domain", "can_view", "can_export", "can_subscribe", "is_active")
    search_fields = ("report_slug", "domain", "permission", "group__name")
