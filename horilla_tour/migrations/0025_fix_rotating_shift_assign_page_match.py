from django.db import migrations


def fix(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    Tour.objects.filter(slug="rotating-shift-assign-tour").update(
        page_match="rotating-shift-assign"
    )


def revert(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    Tour.objects.filter(slug="rotating-shift-assign-tour").update(
        page_match="rotating-shift-assign-view"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0024_seed_rotating_shift_assign_tour"),
    ]

    operations = [
        migrations.RunPython(fix, revert),
    ]
