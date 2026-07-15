from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("hydra_coordination", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="team",
            options={
                "ordering": (
                    "section__location__company__company",
                    "section__location__name",
                    "section__name",
                    "name",
                ),
                "permissions": (
                    (
                        "view_brigadier_panel",
                        "Can view the Hydra brigadier panel",
                    ),
                ),
            },
        ),
    ]
