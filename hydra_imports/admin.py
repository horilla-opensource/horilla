from django.contrib import admin

from hydra_imports.models import CandidateImportRow, CandidateImportSession


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CandidateImportSession)
class CandidateImportSessionAdmin(ReadOnlyAdmin):
    list_display = (
        "uuid",
        "source_filename",
        "recruitment",
        "job_position",
        "status",
        "row_count",
        "created_by",
        "created_at",
        "applied_at",
    )
    list_filter = ("status", "created_at", "applied_at")
    search_fields = ("uuid", "source_filename", "file_sha256", "fingerprint")


@admin.register(CandidateImportRow)
class CandidateImportRowAdmin(ReadOnlyAdmin):
    list_display = (
        "session",
        "row_number",
        "outcome",
        "passport_name",
        "email",
        "created_person",
        "created_candidate",
    )
    list_filter = ("outcome", "created_at")
    search_fields = (
        "session__uuid",
        "passport_name",
        "email",
        "source_row_hash",
    )
