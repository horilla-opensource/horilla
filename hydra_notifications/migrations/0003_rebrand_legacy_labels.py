from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hydra_notifications", "0002_backfill_legacy_notifications")
    ]

    operations = [
        migrations.AlterField(
            model_name="hydranotificationenvelope",
            name="category",
            field=models.CharField(
                choices=[
                    ("legacy", "Hydra"),
                    ("organization", "Organization"),
                    ("arrivals", "Arrivals"),
                    ("legalization", "Legalization"),
                    ("tasks", "Tasks"),
                    ("onboarding", "Onboarding"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="hydranotificationenvelope",
            name="kind",
            field=models.CharField(
                choices=[
                    ("legacy", "Hydra notification"),
                    ("organization_scope_end", "Scope end scheduled"),
                    ("organization_scope_revoked", "Scope revoked"),
                    ("organization_assignment_end", "Assignment end scheduled"),
                    ("organization_assignment_ended", "Assignment ended"),
                    ("arrival_upcoming", "Arrival approaching"),
                    ("arrival_overdue", "Arrival overdue"),
                    ("legalization_deadline", "Legalization deadline"),
                    ("legalization_overdue", "Legalization overdue"),
                    ("legalization_validity", "Validity ending"),
                    ("legalization_expired", "Legalization expired"),
                    ("legalization_assigned", "Responsibility assigned"),
                    ("legalization_transferred", "Responsibility transferred"),
                    ("legalization_deputy", "Deputy appointed"),
                    ("legalization_deputy_revoked", "Deputy appointment revoked"),
                    ("task_assigned", "Task assigned"),
                    ("task_updated", "Task updated"),
                    ("task_reassigned", "Task reassigned"),
                    ("task_status_changed", "Task status changed"),
                    ("task_completed", "Task completed"),
                    ("task_cancelled", "Task cancelled"),
                    ("task_reopened", "Task reopened"),
                    ("onboarding_ready", "Onboarding ready"),
                    ("onboarding_task_changed", "Onboarding task changed"),
                ],
                max_length=48,
            ),
        ),
        migrations.AlterField(
            model_name="hydranotificationstateevent",
            name="action",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("imported", "Imported from Hydra"),
                    ("read", "Marked as read"),
                    ("unread", "Marked as unread"),
                    ("opened", "Opened"),
                    ("archived", "Archived"),
                    ("restored", "Restored"),
                ],
                max_length=16,
            ),
        ),
    ]
