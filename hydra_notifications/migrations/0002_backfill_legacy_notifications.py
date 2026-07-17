from uuid import uuid4

from django.conf import settings
from django.db import migrations
from django.utils import timezone


def backfill_legacy_notifications(apps, schema_editor):
    app_label, model_name = settings.NOTIFICATIONS_NOTIFICATION_MODEL.split(".")
    Notification = apps.get_model(app_label, model_name)
    Envelope = apps.get_model("hydra_notifications", "HydraNotificationEnvelope")
    StateEvent = apps.get_model(
        "hydra_notifications",
        "HydraNotificationStateEvent",
    )
    database = schema_editor.connection.alias
    existing_notification_ids = set(
        Envelope.objects.using(database).values_list("notification_id", flat=True)
    )
    notifications = Notification.objects.using(database).exclude(
        pk__in=existing_notification_ids
    )
    now = timezone.now()
    envelopes = []
    for notification in notifications.iterator(chunk_size=500):
        severity = notification.level
        if severity not in ("info", "success", "warning", "error"):
            severity = "info"
        envelopes.append(
            Envelope(
                uuid=uuid4(),
                idempotency_key=f"legacy:{notification.pk}",
                notification_id=notification.pk,
                recipient_id=notification.recipient_id,
                kind="legacy",
                category="legacy",
                severity=severity,
                target_kind="general",
                occurred_at=notification.timestamp,
                read_at=None if notification.unread else notification.timestamp,
                archived_at=notification.timestamp if notification.deleted else None,
                version=1,
                created_at=now,
            )
        )
        if len(envelopes) >= 500:
            Envelope.objects.using(database).bulk_create(envelopes, batch_size=500)
            envelopes.clear()
    if envelopes:
        Envelope.objects.using(database).bulk_create(envelopes, batch_size=500)

    events = []
    for envelope_id in Envelope.objects.using(database).filter(
        kind="legacy",
        state_events__isnull=True,
    ).values_list("pk", flat=True).iterator(chunk_size=500):
        events.append(
            StateEvent(
                uuid=uuid4(),
                envelope_id=envelope_id,
                sequence=1,
                action="imported",
                occurred_at=now,
            )
        )
        if len(events) >= 500:
            StateEvent.objects.using(database).bulk_create(events, batch_size=500)
            events.clear()
    if events:
        StateEvent.objects.using(database).bulk_create(events, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("hydra_notifications", "0001_notification_center"),
    ]

    operations = [
        migrations.RunPython(backfill_legacy_notifications, migrations.RunPython.noop),
    ]
