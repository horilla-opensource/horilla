from django.contrib import admin

from hydra_documents.models import (
    DocumentAccessLog,
    PrivateDocument,
    PrivateDocumentType,
    QuarantinedUpload,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PrivateDocumentType)
class PrivateDocumentTypeAdmin(ReadOnlyAdmin):
    list_display = (
        "name",
        "code",
        "company",
        "category",
        "max_size_bytes",
        "retention_days",
        "requires_expiry_date",
        "single_current",
        "is_active",
    )
    search_fields = ("uuid", "code", "name", "company__company")
    list_filter = ("category", "requires_expiry_date", "single_current", "is_active")


@admin.register(PrivateDocument)
class PrivateDocumentAdmin(ReadOnlyAdmin):
    list_display = (
        "uuid",
        "person",
        "candidate",
        "document_type",
        "version_number",
        "title",
        "category",
        "scanner",
        "retention_until",
        "legal_hold",
        "deleted_at",
        "created_at",
    )
    search_fields = ("uuid", "person__hydra_id", "title", "original_filename")
    list_filter = (
        "category",
        "verified_content_type",
        "legal_hold",
        "deleted_at",
        "created_at",
    )


@admin.register(QuarantinedUpload)
class QuarantinedUploadAdmin(ReadOnlyAdmin):
    list_display = (
        "uuid",
        "person",
        "candidate",
        "status",
        "scanner",
        "purge_after",
        "purged_at",
        "created_at",
    )
    search_fields = ("uuid", "person__hydra_id", "original_filename", "sha256")
    list_filter = ("status", "scanner", "purged_at", "created_at")


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(ReadOnlyAdmin):
    list_display = ("occurred_at", "document_uuid", "actor", "action", "outcome", "reason")
    search_fields = ("document_uuid", "actor__username", "reason")
    list_filter = ("action", "outcome", "occurred_at")
