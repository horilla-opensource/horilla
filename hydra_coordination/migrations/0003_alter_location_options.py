from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("hydra_coordination", "0002_alter_team_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="location",
            options={
                "ordering": ("company__company", "name"),
                "permissions": (
                    (
                        "view_coordinator_panel",
                        "Can view the Hydra coordinator panel",
                    ),
                ),
            },
        ),
    ]
