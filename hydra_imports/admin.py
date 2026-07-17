from django.contrib import admin

from hydra_imports.models import (
    CandidateImportLifecycleEvent,
    CandidateImportRow,
    CandidateImportSession,
)
from hydra_imports.selectors import candidate_import_sessions_for_user


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ScopedSessionAdmin(ReadOnlyAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        visible = candidate_import_sessions_for_user(user=request.user).values_list(
            "pk", flat=True
        )
        return queryset.filter(pk__in=visible)

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        return obj is None or candidate_import_sessions_for_user(
            user=request.user
        ).filter(pk=obj.pk).exists()


class ScopedRelatedAdmin(ReadOnlyAdmin):
    session_field = "session_id"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        visible = candidate_import_sessions_for_user(user=request.user).values_list(
            "pk", flat=True
        )
        return queryset.filter(**{f"{self.session_field}__in": visible})

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        return obj is None or candidate_import_sessions_for_user(
            user=request.user
        ).filter(pk=getattr(obj, self.session_field)).exists()


@admin.register(CandidateImportSession)
class CandidateImportSessionAdmin(ScopedSessionAdmin):
    list_display = (
        "uuid",
        "source_filename_for_display",
        "recruitment",
        "job_position",
        "status",
        "row_count",
        "created_by",
        "created_at",
        "applied_at",
        "sensitive_data_purge_after",
        "sensitive_data_purged_at",
    )
    exclude = ("source_filename",)
    list_filter = ("status", "created_at", "applied_at", "sensitive_data_purged_at")
    search_fields = ("uuid", "file_sha256", "fingerprint")


@admin.register(CandidateImportRow)
class CandidateImportRowAdmin(ScopedRelatedAdmin):
    list_display = (
        "session",
        "row_number",
        "outcome",
        "created_person",
        "created_candidate",
    )
    list_filter = ("outcome", "created_at")
    search_fields = (
        "session__uuid",
        "source_row_hash",
    )
    exclude = (
        "error_message",
        "duplicate_reason",
        "passport_name",
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "citizenship",
        "preferred_language",
        "email",
        "phone",
        "whatsapp_viber",
        "candidate_mobile",
    )


@admin.register(CandidateImportLifecycleEvent)
class CandidateImportLifecycleEventAdmin(ScopedRelatedAdmin):
    list_display = (
        "occurred_at",
        "session",
        "event_type",
        "reason",
        "source",
        "actor",
        "rows_redacted",
    )
    list_filter = ("event_type", "reason", "source", "occurred_at")
    search_fields = ("uuid", "session__uuid", "session__fingerprint")
