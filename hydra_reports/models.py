from uuid import uuid4

from django.conf import settings
from django.db import models


class AppendOnlyReportExportQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Operational report export history is append-only.")

    def delete(self):
        raise TypeError("Operational report export history is append-only.")


class OperationalReportExport(models.Model):
    class Format(models.TextChoices):
        CSV = "csv", "CSV"

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hydra_operational_report_exports",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    format = models.CharField(max_length=8, choices=Format.choices)
    filename = models.CharField(max_length=255)
    row_count = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    filters = models.JSONField(default=dict)
    scope_location_ids = models.JSONField(default=list)
    scope_team_ids = models.JSONField(default=list)

    objects = AppendOnlyReportExportQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-pk")
        default_permissions = ()
        permissions = (
            ("view_operational_report", "Can view the Hydra operational report"),
            ("export_operational_report", "Can export the Hydra operational report"),
            (
                "view_operationalreportexport",
                "Can view operational report export audit",
            ),
        )
        indexes = (
            models.Index(
                fields=("actor", "occurred_at"),
                name="hyd_report_actor_time_idx",
            ),
        )

    def __str__(self):
        return f"{self.filename} / {self.row_count} / {self.sha256[:12]}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise TypeError("Operational report export history is append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Operational report export history is append-only.")
