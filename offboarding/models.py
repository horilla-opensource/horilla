from collections.abc import Iterable
from typing import Any
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from base import thread_local_middleware
from employee.models import Employee
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog

# Create your models here.


class Offboarding(models.Model):
    """
    Offboarding model
    """

    statuses = [("ongoing", "Ongoing"), ("completed", "Completed")]
    title = models.CharField(max_length=20)
    description = models.TextField()
    managers = models.ManyToManyField(Employee)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default="ongoing", choices=statuses)
    is_active = models.BooleanField(default=True)


class OffboardingStage(models.Model):
    """
    Offboarding model
    """

    types = [
        ("notice_period", "Notice period"),
        ("fnf", "FnF Settlement"),
        ("other", "Other"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=20)
    type = models.CharField(max_length=13, choices=types)
    offboarding_id = models.ForeignKey(Offboarding, on_delete=models.PROTECT)
    managers = models.ManyToManyField(Employee)
    sequence = models.IntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.title)

    def is_archived_stage(self):
        """
        This method is to check the stage is archived or not
        """
        return self.type == "archived"


@receiver(post_save, sender=Offboarding)
def create_initial_stage(sender, instance, created, **kwargs):
    """
    This is post save method, used to create initial stage for the recruitment
    """
    if created:
        initial_stage = OffboardingStage()
        initial_stage.title = "Notice Period"
        initial_stage.offboarding_id = instance
        initial_stage.type = "notice_period"
        initial_stage.save()


class OffboardingStageMultipleFile(models.Model):
    """
    OffboardingStageMultipleFile
    """

    attachment = models.FileField(upload_to="offboarding/attachments")
    created_at = models.DateTimeField(auto_now_add=True)


class OffboardingEmployee(models.Model):
    """
    OffboardingEmployee model / Employee on stage
    """

    units = [("day", "days"), ("month", "Month")]
    employee_id = models.OneToOneField(
        Employee, on_delete=models.CASCADE, verbose_name="Employee"
    )
    stage_id = models.ForeignKey(
        OffboardingStage, on_delete=models.PROTECT, verbose_name="Stage"
    )
    notice_period = models.IntegerField()
    unit = models.CharField(max_length=10, choices=units)
    notice_period_starts = models.DateField()
    notice_period_ends = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.employee_id.get_full_name()


class OffboardingTask(models.Model):
    """
    OffboardingTask model
    """

    title = models.CharField(max_length=30)
    managers = models.ManyToManyField(Employee)
    stage_id = models.ForeignKey(
        OffboardingStage,
        on_delete=models.PROTECT,
        verbose_name="Stage",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ["title", "stage_id"]

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class EmployeeTask(models.Model):
    """
    EmployeeTask model
    """

    statuses = [
        ("todo", "Todo"),
        ("inprogress", "Inprogress"),
        ("stuck", "Stuck"),
        ("completed", "Completed"),
    ]
    employee_id = models.ForeignKey(
        OffboardingEmployee,
        on_delete=models.CASCADE,
        verbose_name="Employee",
        null=True,
    )
    status = models.CharField(max_length=10, choices=statuses, default="todo")
    task_id = models.ForeignKey(OffboardingTask, on_delete=models.CASCADE)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["employee_id", "task_id"]


class ExitReason(models.Model):
    """
    ExitReason model
    """

    title = models.CharField(max_length=50)
    description = models.TextField()
    offboarding_employee_id = models.ForeignKey(
        OffboardingEmployee, on_delete=models.PROTECT
    )
    attacments = models.ManyToManyField(OffboardingStageMultipleFile)


class OffboardingNote(models.Model):
    """
    OffboardingNote
    """

    attachments = models.ManyToManyField(
        OffboardingStageMultipleFile, blank=True, editable=False
    )
    title = models.CharField(max_length=20, null=True)
    description = models.TextField(null=True, blank=True)
    note_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, editable=False
    )
    employee_id = models.ForeignKey(
        OffboardingEmployee, on_delete=models.PROTECT, null=True, editable=False
    )
    stage_id = models.ForeignKey(
        OffboardingStage, on_delete=models.PROTECT, null=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        request = getattr(thread_local_middleware._thread_locals, "request", None)
        if request:
            updated_by = request.user.employee_get
            self.note_by = updated_by
        if self.employee_id:
            self.stage_id = self.employee_id.stage_id
        return super().save(*args, **kwargs)
