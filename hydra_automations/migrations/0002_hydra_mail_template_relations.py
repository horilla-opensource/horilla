import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0004_alter_employeeshiftschedule_auto_punch_out_time"),
        ("hydra_automations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mailautomation",
            name="mail_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="base.hydramailtemplate",
            ),
        ),
        migrations.AlterField(
            model_name="mailautomation",
            name="template_attachments",
            field=models.ManyToManyField(
                blank=True,
                related_name="template_attachment",
                to="base.hydramailtemplate",
            ),
        ),
    ]
