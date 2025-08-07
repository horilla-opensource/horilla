"""
models.py

This module is used to register models for project app

"""

import datetime
from datetime import date

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from employee.models import Employee
from horilla import horilla_middlewares
from horilla.horilla_middlewares import _thread_locals
from horilla.models import HorillaModel, upload_path
from horilla_views.cbv_methods import render_template

# Create your models here.


def validate_time_format(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 5:
        raise ValidationError(_("Invalid format, it should be HH:MM format"))
    try:
        hour, minute = value.split(":")

        if len(hour) < 2 or len(minute) < 2:
            raise ValidationError(_("Invalid format, it should be HH:MM format"))

        minute = int(minute)
        if len(hour) > 2 or minute not in range(60):
            raise ValidationError(_("Invalid time"))
    except ValueError as error:
        raise ValidationError(_("Invalid format")) from error


class Project(HorillaModel):
    PROJECT_STATUS = [
        ("new", _("New")),
        ("in_progress", _("In Progress")),
        ("completed", _("Completed")),
        ("on_hold", _("On Hold")),
        ("cancelled", _("Cancelled")),
        ("expired", _("Expired")),
    ]
    title = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    managers = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="project_managers",
        verbose_name=_("Project Managers"),
    )
    members = models.ManyToManyField(
        Employee,
        blank=True,
        related_name="project_members",
        verbose_name=_("Project Members"),
    )
    status = models.CharField(
        choices=PROJECT_STATUS, max_length=250, default="new", verbose_name=_("Status")
    )
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End Date"))
    document = models.FileField(
        upload_to=upload_path, blank=True, null=True, verbose_name=_("Project File")
    )
    description = models.TextField(verbose_name=_("Description"))
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager("company_id")

    def get_description(self, length=50):
        """
        Returns a truncated version of the description attribute.

        Parameters:
        length (int): The maximum length of the returned description.
        """
        return (
            self.description
            if len(self.description) <= length
            else self.description[:length] + "..."
        )

    def get_managers(self):
        """
        managers column
        """
        employees = self.managers.all()
        if employees:
            employee_names_string = "<br>".join(
                [str(employee) for employee in employees]
            )
            return employee_names_string

    def get_members(self):
        """
        members column
        """
        employees = self.members.all()
        if employees:
            employee_names_string = "<br>".join(
                [str(employee) for employee in employees]
            )
            return employee_names_string

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.title}&background=random"
        return url

    def get_document_html(self):
        if self.document:
            document_url = self.document.url
            image_url = static("images/ui/project/document.png")
            return format_html(
                '<a href="{0}" style="text-decoration: none" rel="noopener noreferrer" class="oh-btn oh-btn--light" target="_blank" onclick="event.stopPropagation();">'
                '<span class="oh-file-icon oh-file-icon--pdf"></span>'
                "&nbsp View"
                "</a>",
                document_url,
                image_url,
            )

    def redirect(self):
        """
        This method generates an onclick URL for task viewing.
        """
        request = getattr(_thread_locals, "request", None)
        employee = request.user.employee_get
        url = reverse_lazy("task-view", kwargs={"project_id": self.pk})

        if (
            employee in self.managers.all()
            or employee in self.members.all()
            or any(employee in task.task_managers.all() for task in self.task_set.all())
            or any(employee in task.task_members.all() for task in self.task_set.all())
            or request.user.has_perm("project.view_project")
        ):
            return f"onclick=\"window.location.href='{url}?view=list'\""
        return ""

    def get_detail_url(self):
        """
        This method to get detail  url
        """
        url = reverse_lazy("project-detailed-view", kwargs={"pk": self.pk})
        return url

    def get_update_url(self):
        """
        This method to get update url
        """
        url = reverse_lazy("update-project", kwargs={"pk": self.pk})
        return url

    def get_archive_url(self):
        """
        This method to get archive url
        """
        url = reverse_lazy("project-archive", kwargs={"project_id": self.pk})
        return url

    def get_task_badge_html(self):
        task_count = self.task_set.count()
        title = self.title
        return format_html(
            '<div style="display: flex; align-items: center;">'
            '    <div class="oh-tabs__input-badge-container">'
            '        <span class="oh-badge oh-badge--secondary oh-badge--small oh-badge--round mr-1" title="{1} Tasks">'
            "            {1}"
            "        </span>"
            "    </div>"
            "    <div>{0}</div>"
            "</div>",
            title,
            task_count,
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("delete-project", kwargs={"project_id": self.pk})
        message = _("Are you sure you want to delete this project?")
        return f"'{url}'" + "," + f"'{message}'"

    def actions(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="cbv/projects/actions.html",
            context={"instance": self},
        )

    def archive_status(self):
        """
        archive status
        """
        if self.is_active:
            return "Archive"
        else:
            return "Un-Archive"

    def clean(self) -> None:
        # validating end date
        if self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValidationError({"document": "End date is less than start date"})
            if self.end_date < date.today():
                self.status = "expired"

    def save(self, *args, **kwargs):
        is_new, request = self.pk is None, getattr(
            horilla_middlewares._thread_locals, "request", None
        )
        if is_new and (cid := request.session.get("selected_company")) and cid != "all":
            self.company_id = Company.find(cid)
        super().save(*args, **kwargs)
        if is_new:
            ProjectStage.objects.create(
                title="Todo", project=self, sequence=1, is_end_stage=False
            )

    def __str__(self):
        return self.title

    class Meta:
        """
        Meta class to add the additional info
        """

        verbose_name = _("Project")
        verbose_name_plural = _("Projects")


class ProjectStage(HorillaModel):
    """
    ProjectStage model
    """

    title = models.CharField(max_length=200, verbose_name=_("Title"))
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="project_stages",
        verbose_name=_("Project"),
    )
    sequence = models.IntegerField(null=True, blank=True, editable=False)
    is_end_stage = models.BooleanField(default=False, verbose_name=_("Is end stage"))
    objects = HorillaCompanyManager("project__company_id")

    def __str__(self) -> str:
        return f"{self.title}"

    def clean(self) -> None:
        if self.is_end_stage:
            project = self.project
            existing_end_stage = project.project_stages.filter(
                is_end_stage=True
            ).exclude(id=self.id)

            if existing_end_stage:
                end_stage = project.project_stages.filter(is_end_stage=True).first()
                raise ValidationError(
                    _(f"Already exist an end stage - {end_stage.title}.")
                )

    def save(self, *args, **kwargs):
        if self.sequence is None:
            last_stage = (
                ProjectStage.objects.filter(project=self.project)
                .order_by("sequence")
                .last()
            )
            if last_stage:
                self.sequence = last_stage.sequence + 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        project_stages_after = ProjectStage.objects.filter(
            project=self.project, sequence__gt=self.sequence
        )

        # Decrement the sequence of the following stages
        for stage in project_stages_after:
            stage.sequence -= 1
            stage.save()

        super().delete(*args, **kwargs)

    class Meta:
        """
        Meta class to add the additional info
        """

        unique_together = ["project", "title"]
        verbose_name = _("Project Stage")
        verbose_name_plural = _("Project Stages")


class Task(HorillaModel):
    """
    Task model
    """

    TASK_STATUS = [
        ("to_do", _("To Do")),
        ("in_progress", _("In Progress")),
        ("completed", _("Completed")),
        ("expired", _("Expired")),
    ]
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, verbose_name=_("Project")
    )
    stage = models.ForeignKey(
        ProjectStage,
        on_delete=models.CASCADE,
        null=True,
        related_name="tasks",
        verbose_name=_("Project Stage"),
    )
    task_managers = models.ManyToManyField(
        Employee,
        blank=True,
        verbose_name=_("Task Managers"),
    )
    task_members = models.ManyToManyField(
        Employee, blank=True, related_name="tasks", verbose_name=_("Task Members")
    )
    status = models.CharField(
        choices=TASK_STATUS, max_length=250, default="to_do", verbose_name=_("Status")
    )
    start_date = models.DateField(null=True, blank=True, verbose_name=_("Start Date"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End Date"))
    document = models.FileField(
        upload_to=upload_path, blank=True, null=True, verbose_name=_("Task File")
    )
    description = models.TextField(verbose_name=_("Description"))
    sequence = models.IntegerField(default=0)
    objects = HorillaCompanyManager("project__company_id")

    def clean(self) -> None:
        if self.end_date is not None and self.project.end_date is not None:
            if (
                self.project.end_date < self.end_date
                or self.project.start_date > self.end_date
            ):
                raise ValidationError(
                    {
                        "end_date": _(
                            "The task end date must be between the project's start and end dates."
                        )
                    }
                )
        if self.end_date < date.today():
            self.status = "expired"

    class Meta:
        """
        Meta class to add the additional info
        """

        unique_together = ["project", "title"]
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")

    def __str__(self):
        return f"{self.title}"

    def if_project(self):
        """
        Return project if have,otherwise return none
        """

        return self.project if self.project else "None"

    def task_detail_view(self):
        """
        detail view of task
        """

        url = reverse("task-detail-view", kwargs={"pk": self.pk})
        return url

    def status_column(self):
        """
        to get status
        """
        return dict(self.TASK_STATUS).get(self.status)

    def get_managers(self):
        """
        return task managers
        """
        managers = self.task_managers.all()
        if managers:
            managers_name_string = "<br>".join([str(manager) for manager in managers])
            return managers_name_string
        else:
            return ""

    def get_members(self):
        """
        return task members
        """
        members = self.task_members.all()
        if members:
            members_name_string = "<br>".join([str(member) for member in members])
            return members_name_string
        else:
            return ""

    def actions(self):
        """
        This method for get custom column for action.
        """
        # request = getattr(_thread_locals, "request", None)
        # is_task_manager = self.task_manager == request.user
        # print(self.title)
        # is_project_manager = self.project.manager == request.user if self.project else False
        # print(self.project)
        # has_permission = request.user.has_perm('project.view_task')  # Replace 'your_app' with your app name

        # if is_task_manager or is_project_manager or has_permission:
        #     return render_template(
        #         "cbv/tasks/task_actions.html",
        #         {"instance": self}
        #     )
        # else:
        #     return ""

        return render_template(
            path="cbv/tasks/task_actions.html",
            context={"instance": self},
        )

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.title}&background=random"
        return url

    def document_col(self):
        """
        This method for get custom document coloumn .
        """

        return render_template(
            path="cbv/tasks/task_document.html",
            context={"instance": self},
        )

    def detail_view_actions(self):
        """
        This method for get detail view actions.
        """

        return render_template(
            path="cbv/tasks/task_detail_actions.html",
            context={"instance": self},
        )

    def get_update_url(self):
        """
        to get the update url
        """
        url = reverse("update-task-all", kwargs={"pk": self.pk})
        return url

    def archive_status(self):
        """
        archive status
        """
        if self.is_active:
            return "Archive"
        else:
            return "Un-Archive"

    def get_archive_url(self):
        """
        to get archive url
        """

        url = reverse("task-all-archive", kwargs={"task_id": self.pk})
        return url

    def get_delete_url(self):
        """
        to get delete url
        """

        url = reverse("delete-task", kwargs={"task_id": self.pk})
        url_with_params = f"{url}?task_all=true"
        message = _("Are you sure you want to delete this task?")
        return f"'{url_with_params}'" + "," + f"'{message}'"


class TimeSheet(HorillaModel):
    """
    TimeSheet model
    """

    TIME_SHEET_STATUS = [
        ("in_Progress", _("In Progress")),
        ("completed", _("Completed")),
    ]
    project_id = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        related_name="project_timesheet",
        verbose_name=_("Project"),
    )
    task_id = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        related_name="task_timesheet",
        verbose_name=_("Task"),
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        verbose_name=_("Employee"),
    )
    date = models.DateField(default=timezone.now, verbose_name=_("Date"))
    time_spent = models.CharField(
        null=True,
        default="00:00",
        max_length=10,
        validators=[validate_time_format],
        verbose_name=_("Hours Spent"),
    )
    status = models.CharField(
        choices=TIME_SHEET_STATUS,
        max_length=250,
        default="in_Progress",
        verbose_name=_("Status"),
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    objects = HorillaCompanyManager("project_id__company_id")

    class Meta:
        ordering = ("-id",)

    def clean(self):
        if self.project_id is None:
            raise ValidationError({"project_id": "Project name is Required."})
        if self.description is None or self.description == "":
            raise ValidationError(
                {"description": "Please provide a description to your Time sheet"}
            )
        if self.employee_id:
            employee = self.employee_id
            if self.task_id:
                task = self.task_id
                if (
                    not employee in task.task_managers.all()
                    and not employee in task.task_members.all()
                    and not employee in task.project.managers.all()
                    and not employee in task.project.members.all()
                ):
                    raise ValidationError(_("Employee not included in this task"))
            elif self.project_id:
                if (
                    not employee in self.project_id.managers.all()
                    and not employee in self.project_id.members.all()
                ):
                    raise ValidationError(_("Employee not included in this project"))
            if self.date > datetime.datetime.today().date():
                raise ValidationError({"date": _("You cannot choose a future date.")})

    def __str__(self):
        return f"{self.employee_id} {self.project_id} {self.task_id} {self.date} {self.time_spent}"

    def status_column(self):
        return dict(self.TIME_SHEET_STATUS).get(self.status)

    def actions(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="cbv/timesheet/actions.html",
            context={"instance": self},
        )

    def detail_actions(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="cbv/timesheet/detail_actions.html",
            context={"instance": self},
        )

    def get_update_url(self):
        """
        This method to get update url
        """
        url = reverse_lazy("update-time-sheet", kwargs={"pk": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("delete-time-sheet", kwargs={"time_sheet_id": self.pk})
        message = _("Are you sure you want to delete this time sheet?")
        return f"'{url}'" + "," + f"'{message}'"

    def detail_view(self):
        """
        for detail view of page
        """
        url = reverse("time-sheet-detail-view", kwargs={"pk": self.pk})
        return url

    class Meta:
        verbose_name = _("Time Sheet")
        verbose_name_plural = _("Time Sheets")
