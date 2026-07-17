from copy import deepcopy

from django.db import migrations, models


ACTIVE_CASE_STATUSES = {
    "draft",
    "collecting_documents",
    "submitted",
    "additional_information",
}


def mark_unresolved_legacy_authority_policies(apps, schema_editor):
    LegalizationCase = apps.get_model("hydra_legalization", "LegalizationCase")
    for case in LegalizationCase.objects.order_by("pk").iterator(chunk_size=500):
        snapshot = case.procedure_snapshot
        if not isinstance(snapshot, dict) or snapshot.get("authorities"):
            continue
        snapshot = deepcopy(snapshot)
        pending = case.status in ACTIVE_CASE_STATUSES
        snapshot["requires_authority"] = pending
        snapshot["legacy_authority_policy_pending"] = pending
        LegalizationCase.objects.filter(pk=case.pk).update(
            procedure_snapshot=snapshot
        )


class Migration(migrations.Migration):
    dependencies = [
        ("hydra_legalization", "0008_legalization_configuration_enforce"),
    ]

    operations = [
        migrations.AlterField(
            model_name="legalizationconfigurationevent",
            name="action",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("updated", "Updated"),
                    ("adopted", "Adopted"),
                ],
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name="legalizationconfigurationevent",
            name="entity_type",
            field=models.CharField(
                choices=[
                    ("procedure", "Procedure"),
                    ("authority", "Authority"),
                    ("requirement", "Requirement"),
                    ("case_policy", "Legacy case policy"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="legalizationconfigurationevent",
            name="reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(
            mark_unresolved_legacy_authority_policies,
            migrations.RunPython.noop,
        ),
    ]
