from django.db import models
from swapper import swappable_setting

from .base.models import AbstractNotification, notify_handler  # noqa


class Notification(AbstractNotification):
    verb_en = models.CharField(max_length=255, default="", null=True)
    verb_ar = models.CharField(max_length=255, default="", null=True)
    verb_de = models.CharField(max_length=255, default="", null=True)
    verb_es = models.CharField(max_length=255, default="", null=True)
    verb_fr = models.CharField(max_length=255, default="", null=True)

    class Meta(AbstractNotification.Meta):
        abstract = False
        swappable = swappable_setting("notifications", "Notification")
