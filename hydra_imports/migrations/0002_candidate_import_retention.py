from datetime import timedelta
import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def backfill_retention_deadlines(apps, schema_editor):
    CandidateImportSession = apps.get_model(
        "hydra_imports", "CandidateImportSession"
    )
    now = timezone.now()
    for session in CandidateImportSession.objects.filter(
        sensitive_data_purge_after__isnull=True
    ).iterator(chunk_size=500):
        retention_hours = 24 if session.status == "applied" else 72
        session.sensitive_data_purge_after = now + timedelta(
            hours=retention_hours
        )
        session.save(update_fields=("sensitive_data_purge_after",))


def clear_retention_deadlines(apps, schema_editor):
    CandidateImportSession = apps.get_model(
        "hydra_imports", "CandidateImportSession"
    )
    CandidateImportSession.objects.update(sensitive_data_purge_after=None)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hydra_imports", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="candidateimportsession",
            options={
                "ordering": ("-created_at", "-pk"),
                "permissions": (
                    ("import_candidate", "Can preview and apply candidate imports"),
                    (
                        "purge_candidateimportsession",
                        "Can discard candidate import source data",
                    ),
                ),
            },
        ),
        migrations.AlterField(
            model_name="candidateimportsession",
            name="fingerprint",
            field=models.CharField(editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name="candidateimportsession",
            name="status",
            field=models.CharField(
                choices=[
                    ("ready", "Ready to apply"),
                    ("blocked", "Blocked"),
                    ("applied", "Applied"),
                    ("expired", "Expired and redacted"),
                ],
                default="blocked",
                editable=False,
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="candidateimportsession",
            name="sensitive_data_purge_after",
            field=models.DateTimeField(
                db_index=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="candidateimportsession",
            name="sensitive_data_purged_at",
            field=models.DateTimeField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_retention_deadlines,
            clear_retention_deadlines,
        ),
        migrations.AlterField(
            model_name="candidateimportsession",
            name="sensitive_data_purge_after",
            field=models.DateTimeField(db_index=True, editable=False),
        ),
        migrations.AddConstraint(
            model_name="candidateimportsession",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    status__in=("ready", "blocked", "applied")
                ),
                fields=("fingerprint",),
                name="hydra_imp_active_fingerprint_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="candidateimportsession",
            constraint=models.CheckConstraint(
                check=(
                    ~models.Q(status="expired")
                    | models.Q(sensitive_data_purged_at__isnull=False)
                ),
                name="hydra_imp_expired_is_purged",
            ),
        ),
        migrations.CreateModel(
            name="CandidateImportLifecycleEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("sensitive_data_purged", "Sensitive data purged")
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("user", "User"), ("system", "System")],
                        max_length=12,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("retention_expired", "Retention expired"),
                            ("manually_discarded", "Manually discarded"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "previous_status",
                    models.CharField(
                        choices=[
                            ("ready", "Ready to apply"),
                            ("blocked", "Blocked"),
                            ("applied", "Applied"),
                            ("expired", "Expired and redacted"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "resulting_status",
                    models.CharField(
                        choices=[
                            ("ready", "Ready to apply"),
                            ("blocked", "Blocked"),
                            ("applied", "Applied"),
                            ("expired", "Expired and redacted"),
                        ],
                        max_length=16,
                    ),
                ),
                ("rows_redacted", models.PositiveIntegerField()),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="candidate_import_lifecycle_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lifecycle_events",
                        to="hydra_imports.candidateimportsession",
                    ),
                ),
            ],
            options={
                "ordering": ("-occurred_at", "-pk"),
                "default_permissions": ("view",),
            },
        ),
        migrations.AddConstraint(
            model_name="candidateimportlifecycleevent",
            constraint=models.UniqueConstraint(
                fields=("session", "event_type"),
                name="hydra_imp_lifecycle_once",
            ),
        ),
        migrations.AddConstraint(
            model_name="candidateimportlifecycleevent",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(source="user", actor__isnull=False)
                    | models.Q(source="system", actor__isnull=True)
                ),
                name="hydra_imp_lifecycle_source_actor",
            ),
        ),
    ]
