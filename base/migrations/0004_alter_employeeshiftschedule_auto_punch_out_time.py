from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("base", "0003_rename_hydra_mail_template")]

    operations = [
        migrations.AlterField(
            model_name="employeeshiftschedule",
            name="auto_punch_out_time",
            field=models.TimeField(
                blank=True,
                help_text=(
                    "Time at which Hydra will automatically check out employee "
                    "attendance if they forget."
                ),
                null=True,
                verbose_name="Automatic Check Out Time",
            ),
        )
    ]
