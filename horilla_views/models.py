import json
from django.db import models
from django.contrib.auth.models import User
from horilla.models import HorillaModel
from base.thread_local_middleware import _thread_locals

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


class ParentModel(models.Model):
    """ """

    title = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.title


class DemoCompany(models.Model):
    title = models.CharField(max_length=20)

    def __str__(self) -> str:
        return self.title


class DemoDepartment(models.Model):
    """
    DemoDepartment
    """

    title = models.CharField(max_length=20)
    company_id = models.ForeignKey(
        DemoCompany,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Company",
    )

    def __str__(self) -> str:
        return self.title


class childModel(models.Model):
    """ """

    title_id = models.ForeignKey(
        ParentModel, on_delete=models.CASCADE, verbose_name="Title"
    )
    department_id = models.ForeignKey(
        DemoDepartment, on_delete=models.CASCADE, null=True, verbose_name="Department"
    )
    description = models.TextField()
