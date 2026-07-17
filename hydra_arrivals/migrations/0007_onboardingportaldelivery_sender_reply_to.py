from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hydra_arrivals", "0006_onboardingportaldelivery_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingportaldelivery",
            name="reply_to",
            field=models.EmailField(default="", editable=False, max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="onboardingportaldelivery",
            name="sender",
            field=models.CharField(default="", editable=False, max_length=320),
            preserve_default=False,
        ),
    ]
