from collections.abc import Iterable
from datetime import date
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from base import thread_local_middleware
from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from employee.models import Employee
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from notifications.signals import notify
from django.contrib.auth.models import User
from base.thread_local_middleware import _thread_locals

# Create your models here.


class Offboarding(models.Model):
    """
    Offboarding model
    """

    statuses = [("ongoing", "Ongoing"), ("completed", "Completed")]
    title = models.CharField(max_length=20)
    description = models.TextField(max_length=255)
    managers = models.ManyToManyField(Employee)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default="ongoing", choices=statuses)
    is_active = models.BooleanField(default=True)
    company_id = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, editable=False
    )
    objects = HorillaCompanyManager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            stages = [
                ("Exit interview", "interview"),
                ("Work Handover", "handover"),
                ("FNF", "fnf"),
                ("Farewell", "other"),
                ("Archived", "archived"),
            ]
            for stage in stages:
                new = OffboardingStage()
                new.offboarding_id = self
                new.title = stage[0]
                new.type = stage[1]
                new.save()

        return


class OffboardingStage(models.Model):
    """
    Offboarding model
    """

    types = [
        ("notice_period", "Notice period"),
        ("fnf", "FnF Settlement"),
        ("other", "Other"),
        ("interview", "Interview"),
        ("handover", "Work handover"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=20)
    type = models.CharField(max_length=13, choices=types)
    offboarding_id = models.ForeignKey(Offboarding, on_delete=models.CASCADE)
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
        OffboardingStage, on_delete=models.CASCADE, verbose_name="Stage", null=True
    )
    notice_period = models.IntegerField(null=True)
    unit = models.CharField(max_length=10, choices=units, default="month", null=True)
    notice_period_starts = models.DateField(null=True)
    notice_period_ends = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )
    def __str__(self) -> str:
        return self.employee_id.get_full_name()


class ResignationLetter(models.Model):
    """
    Resignation Request Employee model
    """

    statuses = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name="Employee"
    )
    title = models.CharField(max_length=30, null=True)
    description = models.TextField(
        null=True,
        max_length=255
    )
    planned_to_leave_on = models.DateField()
    status = models.CharField(max_length=10, choices=statuses, default="requested")
    offboarding_employee_id = models.ForeignKey(
        OffboardingEmployee, on_delete=models.CASCADE, editable=False, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == "approved":
            pass

        return

    def to_offboarding_employee(
        self, offboarding, notice_period_starts, notice_period_ends
    ):
        """
        This method is used to convert/add employee to offboarding
        """
        offboarding_employee = OffboardingEmployee.objects.filter(
            employee_id=self.employee_id
        ).first()
        offboarding_employee = (
            offboarding_employee if offboarding_employee else OffboardingEmployee()
        )
        offboarding_employee.employee_id = self.employee_id
        offboarding_employee.stage_id = (
            OffboardingStage.objects.order_by("created_at")
            .filter(offboarding_id=offboarding)
            .first()
        )
        offboarding_employee.notice_period_starts = notice_period_starts
        offboarding_employee.notice_period_ends = notice_period_ends
        if (
            notice_period_starts
            and notice_period_ends
            and not isinstance(notice_period_starts, str)
            and not isinstance(notice_period_ends, str)
        ):
            diffs = date(
                day=notice_period_ends.day,
                month=notice_period_ends.month,
                year=notice_period_ends.year,
            ) - date(
                day=notice_period_starts.day,
                month=notice_period_starts.month,
                year=notice_period_starts.year,
            )
            diffs = diffs.days
            offboarding_employee.notice_period = diffs if diffs > 0 else None
            offboarding_employee.unit = "day" if diffs > 0 else None
        offboarding_employee.save()


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
        ("inprogress", "In progress"),
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
    description = models.TextField(null=True, editable=False,max_length=255)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["employee_id", "task_id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        notify.send(
            request.user.employee_get,
            recipient=self.employee_id.employee_id.employee_user_id,
            verb=f'Offboarding task "{self.task_id.title}" has been assiged',
            verb_ar=f"",
            verb_de=f"",
            verb_es=f"",
            verb_fr=f"",
            redirect="offboarding/offboarding-pipeline",
            icon="information",
        )


class ExitReason(models.Model):
    """
    ExitReason model
    """

    title = models.CharField(max_length=50)
    description = models.TextField(max_length=255)
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
    description = models.TextField(null=True, blank=True,max_length=255)
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


class OffboardingGeneralSetting(models.Model):
    """
    OffboardingGeneralSettings
    """

    resignation_request = models.BooleanField(default=True)
    company_id = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
