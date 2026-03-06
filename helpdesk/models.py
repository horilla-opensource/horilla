import os
from datetime import datetime

from django import apps
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, Department, JobPosition, Tags
from employee.models import Employee
from horilla import horilla_middlewares
from horilla.models import HorillaModel
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog

PRIORITY = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]
MANAGER_TYPES = [
    ("department", "Department"),
    ("job_position", "Job Position"),
    ("individual", "Individual"),
]

TICKET_TYPES = [
    ("suggestion", "Suggestion"),
    ("complaint", "Complaint"),
    ("service_request", "Service Request"),
    ("meeting_request", "Meeting Request"),
    ("anounymous_complaint", "Anonymous Complaint"),
    ("others", "Others"),
]

TICKET_STATUS = [
    ("new", "New"),
    ("in_progress", "In Progress"),
    ("on_hold", "On Hold"),
    ("resolved", "Resolved"),
    ("canceled", "Canceled"),
]

PASSWORD_RESET_PLATFORMS = [
    ("Microsoft", "Microsoft"),
    ("Passbolt", "Passbolt"),
    ("Plane", "Plane"),
    ("Other", "Other"),
]

ISO_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
]


class DepartmentManager(HorillaModel):
    manager = models.ForeignKey(
        Employee,
        verbose_name=_("Manager"),
        related_name="dep_manager",
        on_delete=models.CASCADE,
    )
    department = models.ForeignKey(
        Department,
        verbose_name=_("Department"),
        related_name="dept_manager",
        on_delete=models.CASCADE,
    )
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager("manager__employee_work_info__company_id")

    class Meta:
        unique_together = ("department", "manager")
        verbose_name = _("Department Manager")
        verbose_name_plural = _("Department Managers")

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if not self.manager.get_department() == self.department:
            raise ValidationError(_(f"This employee is not from {self.department} ."))


class TicketType(HorillaModel):
    title = models.CharField(max_length=100, unique=True, verbose_name=_("Title"))
    type = models.CharField(choices=TICKET_TYPES, max_length=50, verbose_name=_("Type"))
    prefix = models.CharField(max_length=3, unique=True, verbose_name=_("Prefix"))
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager(related_company_field="company_id")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Ticket Type")
        verbose_name_plural = _("Ticket Types")


class Ticket(HorillaModel):

    title = models.CharField(max_length=50)
    employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="ticket", verbose_name="Owner"
    )
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.PROTECT,
        verbose_name="Ticket Type",
    )
    description = models.TextField(max_length=255)
    priority = models.CharField(choices=PRIORITY, max_length=100, default="low")
    created_date = models.DateField(auto_now_add=True)
    resolved_date = models.DateField(blank=True, null=True)
    assigning_type = models.CharField(
        choices=MANAGER_TYPES, max_length=100, verbose_name=_("Assigning Type")
    )
    raised_on = models.CharField(max_length=100, verbose_name=_("Forward To"))
    assigned_to = models.ManyToManyField(
        Employee, blank=True, related_name="ticket_assigned_to"
    )
    deadline = models.DateField(null=True, blank=True)
    tags = models.ManyToManyField(Tags, blank=True, related_name="ticket_tags")
    status = models.CharField(choices=TICKET_STATUS, default="new", max_length=50)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        ordering = ["-created_date"]
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        deadline = self.deadline
        today = datetime.today().date()
        if deadline and deadline < today:
            raise ValidationError(_("Deadline should be greater than today"))

    def get_raised_on(self):
        obj_id = self.raised_on
        raised_on = ""
        if obj_id:
            try:
                if self.assigning_type == "department":
                    raised_on = Department.objects.get(id=obj_id).department
                elif self.assigning_type == "job_position":
                    raised_on = JobPosition.objects.get(id=obj_id).job_position
                elif self.assigning_type == "individual":
                    raised_on = Employee.objects.get(id=obj_id).get_full_name()
            except (ValueError, Department.DoesNotExist, JobPosition.DoesNotExist, Employee.DoesNotExist):
                raised_on = _("Unknown/Deleted Entity")
        return raised_on

    def get_raised_on_object(self):
        obj_id = self.raised_on
        raised_on_obj = None
        if obj_id:
            try:
                if self.assigning_type == "department":
                    raised_on_obj = Department.objects.get(id=obj_id)
                elif self.assigning_type == "job_position":
                    raised_on_obj = JobPosition.objects.get(id=obj_id)
                elif self.assigning_type == "individual":
                    raised_on_obj = Employee.objects.get(id=obj_id)
            except (ValueError, Department.DoesNotExist, JobPosition.DoesNotExist, Employee.DoesNotExist):
                raised_on_obj = None
        return raised_on_obj

    def __str__(self):
        return self.title or f"Ticket {self.id}"

    def tracking(self):
        """
        This method is used to return the tracked history of the instance
        """
        return get_diff(self)


class PasswordResetRequest(HorillaModel):
    """
    Stores the extra details for a Password Reset ticket.
    Linked 1-to-1 with a Ticket via the `ticket` field.
    """

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name="password_reset_request",
    )
    platform = models.CharField(
        max_length=50,
        choices=PASSWORD_RESET_PLATFORMS,
        verbose_name=_("Platform"),
    )
    user_id = models.EmailField(verbose_name=_("User ID (Email)"))
    reason = models.TextField(verbose_name=_("Reason for Request"))

    iso_status = models.CharField(
        max_length=20,
        choices=ISO_STATUS_CHOICES,
        default="PENDING",
        verbose_name=_("ISO Status"),
    )
    iso_feedback = models.TextField(blank=True, null=True, verbose_name=_("ISO Feedback"))
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_password_resets",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Password Reset Request")
        verbose_name_plural = _("Password Reset Requests")

    def __str__(self):
        return f"Password Reset – {self.platform} – {self.ticket}"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if self.iso_status == "REJECTED" and not self.iso_feedback:
            raise ValidationError(
                {"iso_feedback": _("Feedback is required when rejecting a request.")}
            )


class ClaimRequest(HorillaModel):
    ticket_id = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        unique_together = ("ticket_id", "employee_id")

    def __str__(self) -> str:
        return f"{self.ticket_id}|{self.employee_id}"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if not self.ticket_id:
            raise ValidationError({"ticket_id": _("This field is required.")})
        if not self.employee_id:
            raise ValidationError({"employee_id": _("This field is required.")})


class Comment(HorillaModel):
    comment = models.TextField(null=True, blank=True)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comment")
    employee_id = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING, related_name="employee_comment"
    )
    date = models.DateTimeField(auto_now_add=True)
    xss_exempt_fields = ["comment"]  # 850

    def __str__(self):
        return self.comment or ""


class Attachment(HorillaModel):
    file = models.FileField(upload_to="Tickets/Attachment")
    description = models.CharField(max_length=100, blank=True, null=True)
    format = models.CharField(max_length=50, blank=True, null=True)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ticket_attachment",
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comment_attachment",
    )

    def get_file_format(self):
        image_format = [".jpg", ".jpeg", ".png", ".svg"]
        audio_format = [".m4a", ".mp3"]
        file_extension = os.path.splitext(self.file.url)[1].lower()
        if file_extension in audio_format:
            self.format = "audio"
        elif file_extension in image_format:
            self.format = "image"
        else:
            self.format = "file"

    def save(self, *args, **kwargs):
        self.get_file_format()
        super().save(*args, **kwargs)

    def __str__(self):
        return os.path.basename(self.file.name)


class FAQCategory(HorillaModel):
    title = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True, max_length=255)
    company_id = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Company"),
        on_delete=models.CASCADE,
    )
    objects = HorillaCompanyManager()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        if request:
            selected_company = request.session.get("selected_company")
            if (
                not self.id
                and not self.company_id
                and selected_company
                and selected_company != "all"
            ):
                self.company_id = Company.find(selected_company)
        super().save()

    class Meta:
        verbose_name = _("FAQ Category")
        verbose_name_plural = _("FAQ Categories")


class FAQ(HorillaModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    tags = models.ManyToManyField(Tags, blank=True)
    category = models.ForeignKey(FAQCategory, on_delete=models.PROTECT)
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager()

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        if request:
            selected_company = request.session.get("selected_company")
            if (
                not self.id
                and not self.company_id
                and selected_company
                and selected_company != "all"
            ):
                self.company_id = Company.find(selected_company)
        super().save()

    class Meta:
        verbose_name = _("FAQ")
        verbose_name_plural = _("FAQs")