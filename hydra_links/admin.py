from django.contrib import admin

from hydra_links.models import PublicHydraLink


@admin.register(PublicHydraLink)
class PublicHydraLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "kind", "location", "order", "is_active")
    list_filter = ("kind", "location__company", "location", "is_active")
    search_fields = ("label", "base_url", "location__name")
    readonly_fields = ("uuid", "created_at", "created_by", "modified_by")

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
