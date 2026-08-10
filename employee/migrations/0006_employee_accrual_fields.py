# Generated migration for Royal Falcon Security Leave Policy - Employee fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0005_alter_employee_phone_and_more"),
    ]

    operations = [
        # Add fields to Employee for Royal Falcon Leave Accrual Policy
        migrations.AddField(
            model_name="employee",
            name="original_joining_date",
            field=models.DateField(
                blank=True,
                editable=False,
                help_text="Preserved original joining date for leave accrual calculations",
                null=True,
                verbose_name="Original Joining Date",
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="adjusted_service_start_date",
            field=models.DateField(
                blank=True,
                editable=False,
                help_text="Joining date adjusted for unpaid/unauthorized leave exclusions",
                null=True,
                verbose_name="Adjusted Service Start Date",
            ),
        ),
    ]
