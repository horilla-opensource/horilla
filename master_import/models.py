"""One import run: the uploaded file, how its columns were mapped, and what came of it."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def upload_path(instance, filename):
    return f"master_import/{instance.dataset}/{filename}"


class ImportJob(models.Model):
    UPLOADED = "uploaded"
    MAPPED = "mapped"
    DONE = "done"
    FAILED = "failed"
    STATUS_CHOICES = [
        (UPLOADED, _("Uploaded")),
        (MAPPED, _("Mapped")),
        (DONE, _("Imported")),
        (FAILED, _("Failed")),
    ]

    dataset = models.CharField(max_length=50)
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_path)
    columns = models.JSONField(default=list)
    row_count = models.PositiveIntegerField(default=0)
    mapping = models.JSONField(default=dict)
    # "create" adds new records; "update" changes existing ones found by match_keys.
    mode = models.CharField(max_length=10, default="create")
    match_keys = models.JSONField(default=list)
    # Values corrected on the review page: {row number: {field: value}}.
    edits = models.JSONField(default=dict)
    # Rows left out of the import by choice, by row number.
    skipped = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=UPLOADED)
    summary = models.JSONField(default=dict)
    # How far the row check has got, 0 to 100, read by the progress bar.
    check_progress = models.PositiveSmallIntegerField(default=0)
    error_file = models.FileField(upload_to="master_import/errors/", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    company_id = models.ForeignKey(
        "base.Company",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.dataset}: {self.original_name}"
