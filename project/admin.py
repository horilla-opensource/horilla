from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'project_owner', 'start_date', 'estimated_cost', 'attachment_link')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'description1', 'project_owner__first_name', 'project_owner__last_name')
    filter_horizontal = ('team_members',)

    fieldsets = (
        (None, {
            'fields': ('name', 'description1', 'status', 'attachment')
        }),
        (_('Timeline'), {
            'fields': ('start_date',)
        }),
        (_('Team'), {
            'fields': ('project_owner', 'team_members')
        }),
        (_('Financial'), {
            'fields': ('estimated_cost', 'estimated_revenue'),
            'classes': ('collapse',)
        }),
    )

    def attachment_link(self, obj):
        if obj.attachment:
            return f'<a href="{obj.attachment.url}" target="_blank">View File</a>'
        return "-"
    attachment_link.allow_tags = True
    attachment_link.short_description = _('Attachment')
