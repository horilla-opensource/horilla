from django.db import migrations, models


def rename_source_values(apps, schema_editor):
    EmployeeConversion = apps.get_model("hydra_people", "EmployeeConversion")
    CandidateStageTransition = apps.get_model(
        "hydra_people", "CandidateStageTransition"
    )
    EmployeeConversion._base_manager.filter(source="horilla_onboarding").update(
        source="hydra_onboarding"
    )
    CandidateStageTransition._base_manager.filter(source="horilla_pipeline").update(
        source="hydra_pipeline"
    )


def restore_source_values(apps, schema_editor):
    EmployeeConversion = apps.get_model("hydra_people", "EmployeeConversion")
    CandidateStageTransition = apps.get_model(
        "hydra_people", "CandidateStageTransition"
    )
    EmployeeConversion._base_manager.filter(source="hydra_onboarding").update(
        source="horilla_onboarding"
    )
    CandidateStageTransition._base_manager.filter(source="hydra_pipeline").update(
        source="horilla_pipeline"
    )


class Migration(migrations.Migration):
    dependencies = [("hydra_people", "0005_person_duplicate_merge")]

    operations = [
        migrations.RunPython(rename_source_values, restore_source_values),
        migrations.AlterField(
            model_name="employeeconversion",
            name="source",
            field=models.CharField(
                choices=[
                    ("hydra_operator", "Hydra operator"),
                    ("hydra_onboarding", "Hydra onboarding"),
                ],
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="candidatestagetransition",
            name="source",
            field=models.CharField(
                choices=[
                    ("hydra", "Hydra"),
                    ("hydra_pipeline", "Hydra pipeline"),
                ],
                max_length=24,
            ),
        ),
    ]
