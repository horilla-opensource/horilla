from django.contrib import admin

from hydra_automations.models import MailAutomation

# Register your models here.


admin.site.register(
    [
        MailAutomation,
    ]
)
