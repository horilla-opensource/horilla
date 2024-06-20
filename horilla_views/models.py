import json

from django.contrib.auth.models import User
from django.db import models

from horilla.horilla_middlewares import _thread_locals
from horilla.models import HorillaModel

# Create your models here.


class ToggleColumn(HorillaModel):
    """
    ToggleColumn
    """

    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_excluded_column",
        editable=False,
    )
    path = models.CharField(max_length=256)
    excluded_columns = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", {})
        user = request.user
        self.user_id = user
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.user_id.employee_get)


class ActiveTab(HorillaModel):
    """
    ActiveTab
    """

    path = models.CharField(max_length=256)
    tab_target = models.CharField(max_length=256)


class ActiveGroup(HorillaModel):
    """
    ActiveGroup
    """

    path = models.CharField(max_length=256)
    group_target = models.CharField(max_length=256)
    group_by_field = models.CharField(max_length=256)
