from uuid import uuid4

from django.db import models


class MaintenanceState(models.Model):
    key = models.CharField(max_length=40, primary_key=True, default="primary", editable=False)
    owner_uuid = models.UUIDField(default=uuid4, editable=False)
    started_at = models.DateTimeField()
    heartbeat_at = models.DateTimeField(db_index=True)
    last_cycle_started_at = models.DateTimeField(null=True, blank=True)
    last_cycle_completed_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_notification_dispatch_at = models.DateTimeField(null=True, blank=True)
    last_legalization_run_at = models.DateTimeField(null=True, blank=True)
    last_arrival_run_at = models.DateTimeField(null=True, blank=True)
    last_housing_run_at = models.DateTimeField(null=True, blank=True)
    last_onboarding_reconcile_at = models.DateTimeField(null=True, blank=True)
    last_portal_email_dispatch_at = models.DateTimeField(null=True, blank=True)
    last_document_purge_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
    last_error_code = models.CharField(max_length=120, blank=True)

    class Meta:
        default_permissions = ()
        permissions = (("view_maintenancestate", "Can view Hydra maintenance state"),)

    def __str__(self):
        return f"{self.key}: {self.heartbeat_at}"
