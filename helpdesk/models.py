import os
from datetime import date, datetime

from django.db import models
from django.forms import ValidationError
from django.middleware.csrf import get_token
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, Department, JobPosition, Tags
from employee.models import Employee
from horilla import horilla_middlewares
from horilla.horilla_middlewares import _thread_locals
from horilla.models import HorillaModel, upload_path
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from horilla_views.cbv_methods import render_template

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

    def get_update_url(self):
        """
        This method to get update url
        """

        url = reverse_lazy("department-manager-update-view", kwargs={"pk": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("department-manager-delete", kwargs={"dep_id": self.pk})
        return url

    def get_instance_id(self):
        return self.id

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

    def get_update_url(self):
        """
        This method to get update url
        """
        url = reverse_lazy("ticket-update-form", kwargs={"pk": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("generic-delete")
        return url

    def get_delete_instance(self):
        """
        to get instance for delete
        """

        return self.pk

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

    def get_raised_on(self):
        obj_id = self.raised_on
        if self.assigning_type == "department":
            raised_on = Department.objects.get(id=obj_id).department
        elif self.assigning_type == "job_position":
            raised_on = JobPosition.objects.get(id=obj_id).job_position
        elif self.assigning_type == "individual":
            raised_on = Employee.objects.get(id=obj_id).get_full_name()
        return raised_on

    def get_raised_on_object(self):
        obj_id = self.raised_on
        if self.assigning_type == "department":
            raised_on = Department.objects.get(id=obj_id)
        elif self.assigning_type == "job_position":
            raised_on = JobPosition.objects.get(id=obj_id)
        elif self.assigning_type == "individual":
            raised_on = Employee.objects.get(id=obj_id)
        return raised_on

    def get_ticket_id_col(self):
        """
        This method is used to get the ticket id
        """
        today = date.today()
        ticket_id = f"{self.ticket_type.prefix}-{self.pk:03d}"

        if self.status == "resolved":
            return ticket_id

        if self.deadline == today:
            due_text = "Due today"
        else:
            days_diff = (self.deadline - today).days
            if days_diff < 0:
                days_diff = abs(days_diff)
                due_text = f"Overdue by {days_diff} days"
            else:
                due_text = f"Due in {days_diff} days"

        if self.deadline < today:
            icon_class = "danger"
        elif self.deadline == today:
            icon_class = "warning"
        else:
            icon_class = "success"

        col = f"""
            <span
                class='
                    d-flex
                    justify-content-between
                    align-items-center
                '
            >
                {ticket_id}
                <span title='{due_text}'>
                    <ion-icon
                        class="text-{icon_class}"
                        name="time-sharp"
                    >
                    </ion-icon>
                </span>
            </span>
        """
        return col

    def get_ticket_detail_url(self):
        """
        This method is used to get the ticket detail url
        """
        return reverse_lazy("ticket-detail", kwargs={"ticket_id": self.pk})

    def get_assigned_to(self):
        """
        This method is used to get the assigned to
        """
        assigned_to = self.assigned_to.all()
        if assigned_to:
            assigned_to = ", ".join([emp.get_full_name() for emp in assigned_to])

        return assigned_to

    def get_tags_col(self):
        """
        This method is used to get the tags column
        """
        tags = self.tags.all()
        if tags:
            tags = ", ".join([tag.title for tag in tags])

        return tags

    def get_priority_stars(self):
        """
        This method is used to get the priority stars
        """
        request = getattr(_thread_locals, "request", None)
        csrf_token = get_token(request)
        rating_inputs = ""
        checked_value = {"low": "1", "medium": "2", "high": "3"}.get(self.priority, "1")

        for i in "321":
            checked = "checked" if i == checked_value else ""
            title = {"1": _("Low"), "2": _("Medium"), "3": _("High")}[i]

            rating_inputs += f"""
                <input type="radio" id="star{i}{self.id}" name="rating" class="rating-radio" value="{i}" {checked} />
                <label for="star{i}{self.id}" title="{title}"></label>
            """

        html = f"""
            <form hx-swap="none" hx-post="{reverse_lazy('update-priority', kwargs = {'ticket_id' : self.id})}" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                <div class="d-flex">
                    <div class="oh-rate" onclick="event.stopPropagation();$(this).parents().closest('form').find('button').click()">
                        {rating_inputs}
                    </div>
                    <button type="submit" hidden="true" onclick="event.stopPropagation()"></button>
                </div>
            </form>
        """
        return html

    def row_colors(self):
        """
        This method is used to get the row colors
        """
        if self.status == "new":
            return "row-status--blue"
        elif self.status == "in_progress":
            return "row-status--orange"
        elif self.status == "on_hold":
            return "row-status--red"
        elif self.status == "resolved":
            return "row-status--yellowgreen"
        elif self.status == "canceled":
            return "row-status--gray"

    def ticket_action_col(self):
        """
        This method is used to get the ticket actions
        """
        request = getattr(_thread_locals, "request", None)
        tab_name = request.GET.get("ticket_tab", "my_tickets")
        claim_request = self.claimrequest_set.filter(
            employee_id=request.user.employee_get
        ).first()
        return render_template(
            "cbv/pipeline/pipeline_action_col.html",
            {"ticket": self, "tab": tab_name, "claim_request": claim_request},
        )

    def kanban_action_method(self):
        """
        This method is used to get the ticket kanban actions
        """
        request = getattr(_thread_locals, "request", None)
        tab_name = request.GET.get("ticket_tab", "my_tickets")
        claim_request = self.claimrequest_set.filter(
            employee_id=request.user.employee_get
        ).first()
        return render_template(
            "cbv/pipeline/kanban_action_method.html",
            {"ticket": self, "tab": tab_name, "claim_request": claim_request},
        )

    def get_status_col(self):
        """
        This method is used to get the status column
        """

        from helpdesk.methods import is_department_manager

        request = getattr(_thread_locals, "request", None)
        options = ""
        for status, name in TICKET_STATUS:
            selected = "selected" if status == self.status else ""
            options += f"""
                <option value="{status}" {selected}>
                    {name}
                </option>
            """

        col = self.get_status_display()
        if (
            request.user.employee_get == self.employee_id
            or request.user.has_perm("helpdesk.change_ticket")
            or request.user.employee_get in self.assigned_to.all()
            or is_department_manager(request, self)
        ):
            col = f"""
                <div onclick="event.stopPropagation()" >
                    <select
                        hx-post="{reverse_lazy('ticket-status-change', kwargs={'ticket_id': self.id})}"
                        name="status"
                        id="status"
                        hx-swap="none"
                        hx-on-htmx-after-request="$('#reloadMessagesButton').click();$(`#offboardingStageContainer{{instance.stage_id.pk}}`).find('.reload-record').click()"
                        name="status"
                        class="w-100"
                        style="
                            border: 1px solid hsl(213deg, 22%, 84%);
                            padding: 0.3rem 0.8rem 0.3rem 0.3rem;
                            border-radius: 0rem;
                        "
                    >
                        {options}
                    </select>
                </div>
            """
        return col

    def __str__(self):
        return self.title

    def tracking(self):
        """
        This method is used to return the tracked history of the instance
        """
        return get_diff(self)


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

    def __str__(self):
        return self.comment


class Attachment(HorillaModel):
    file = models.FileField(upload_to=upload_path)
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
