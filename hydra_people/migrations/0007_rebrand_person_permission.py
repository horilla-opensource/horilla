from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("hydra_people", "0006_rebrand_source_values")]

    operations = [
        migrations.AlterModelOptions(
            name="person",
            options={
                "ordering": ("passport_name", "hydra_id"),
                "permissions": (
                    (
                        "link_candidate",
                        "Can link recruitment applications to Hydra person",
                    ),
                    (
                        "review_person_duplicates",
                        "Can review Hydra Person duplicate suggestions",
                    ),
                    (
                        "dismiss_person_duplicate",
                        "Can dismiss Person duplicate suggestions",
                    ),
                    ("merge_person", "Can merge duplicate Hydra Person records"),
                    (
                        "convert_person_to_employee",
                        "Can convert Hydra person to Hydra employee",
                    ),
                ),
                "verbose_name": "Hydra person",
                "verbose_name_plural": "Hydra people",
            },
        )
    ]
