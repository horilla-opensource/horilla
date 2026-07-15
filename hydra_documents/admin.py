from django.contrib import admin

from hydra_documents.models import DocumentAccessLog, PrivateDocument


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PrivateDocument)
class PrivateDocumentAdmin(ReadOnlyAdmin):
    list_display = ("uuid", "person", "candidate", "title", "category", "size", "created_at")
    search_fields = ("uuid", "person__hydra_id", "title", "original_filename")
    list_filter = ("category", "verified_content_type", "created_at")


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(ReadOnlyAdmin):
    list_display = ("occurred_at", "document_uuid", "actor", "action", "outcome", "reason")
    search_fields = ("document_uuid", "actor__username", "reason")
    list_filter = ("action", "outcome", "occurred_at")
