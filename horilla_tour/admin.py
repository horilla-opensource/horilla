"""Django admin registration for the tour engine (support/debugging)."""

from django.contrib import admin

from horilla_tour.models import Tour, TourProgress, TourStep


class TourStepInline(admin.TabularInline):
    model = TourStep
    extra = 0
    ordering = ("sequence",)


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "audience",
        "trigger",
        "is_published",
        "company_id",
    )
    list_filter = ("audience", "trigger", "is_published", "match_type")
    search_fields = ("title", "slug", "page_match")
    inlines = [TourStepInline]


@admin.register(TourProgress)
class TourProgressAdmin(admin.ModelAdmin):
    list_display = ("tour", "user", "status", "last_step", "completed_at")
    list_filter = ("status",)
    search_fields = ("tour__title", "user__username")
