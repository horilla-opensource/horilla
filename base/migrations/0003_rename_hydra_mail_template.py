from django.db import migrations


OLD_MODEL = "horillamailtemplate"
NEW_MODEL = "hydramailtemplate"
OLD_TABLE = "base_horillamailtemplate"


def _rename_permissions(apps, old_model, new_model):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    content_type = ContentType.objects.filter(
        app_label="base", model=old_model
    ).first()
    if content_type is None:
        return

    content_type.model = new_model
    content_type.save(update_fields=("model",))
    for permission in Permission.objects.filter(content_type=content_type):
        old_fragment = old_model
        if old_fragment in permission.codename:
            permission.codename = permission.codename.replace(old_fragment, new_model)
        if "Horilla mail template" in permission.name:
            permission.name = permission.name.replace(
                "Horilla mail template", "Hydra mail template"
            )
        permission.save(update_fields=("codename", "name"))


def rename_to_hydra(apps, schema_editor):
    _rename_permissions(apps, OLD_MODEL, NEW_MODEL)


def rename_to_legacy(apps, schema_editor):
    _rename_permissions(apps, NEW_MODEL, OLD_MODEL)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("base", "0002_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("hydra_automations", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameModel(
                    old_name="HorillaMailTemplate",
                    new_name="HydraMailTemplate",
                ),
                migrations.AlterModelTable(
                    name="hydramailtemplate",
                    table=OLD_TABLE,
                ),
                migrations.AlterModelOptions(
                    name="hydramailtemplate",
                    options={
                        "verbose_name": "Hydra mail template",
                        "verbose_name_plural": "Hydra mail templates",
                    },
                ),
            ],
        ),
        migrations.RunPython(rename_to_hydra, rename_to_legacy),
    ]
