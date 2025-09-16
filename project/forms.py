from typing import Any

from django import forms
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm
from horilla.horilla_middlewares import _thread_locals

from .models import *


class ProjectForm(ModelForm):
    """
    Form for Project model
    """

    cols = {"description": 12}

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Project
        fields = "__all__"


class ProjectTimeSheetForm(ModelForm):
    """
    Form for Project model in Time sheet form
    """

    def __init__(self, *args, **kwargs):
        super(ProjectTimeSheetForm, self).__init__(*args, **kwargs)
        self.fields["status"].widget.attrs.update(
            {
                "style": "width: 100%; height: 47px;",
                "class": "oh-select",
            }
        )

    def __init__(self, *args, request=None, **kwargs):
        super(ProjectTimeSheetForm, self).__init__(*args, **kwargs)
        self.fields["managers"].widget.attrs.update({"id": "managers_id"})
        self.fields["status"].widget.attrs.update({"id": "status_id"})
        self.fields["members"].widget.attrs.update({"id": "members_id"})
        self.fields["title"].widget.attrs.update({"id": "id_project"})

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Project
        fields = "__all__"


class TaskForm(ModelForm):
    """
    Form for Task model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"
        # exclude = ("project_id",)

        widgets = {
            "project": forms.HiddenInput(),
            "stage": forms.HiddenInput(),
            "sequence": forms.HiddenInput(),
        }


class QuickTaskForm(ModelForm):
    class Meta:
        model = Task
        fields = ["title", "task_managers", "project", "stage", "end_date"]
        widgets = {
            "project": forms.HiddenInput(),
            "stage": forms.HiddenInput(),
            "end_date": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(QuickTaskForm, self).__init__(*args, **kwargs)

        self.fields["title"].widget.attrs.update(
            {"class": "oh-input w-100 mb-2", "placeholder": _("Task Title")}
        )
        self.fields["task_managers"].required = True


class TaskFormCreate(ModelForm):
    """
    Form for Task model in create button inside task view
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"
        # exclude = ("project_id",)

        widgets = {
            "project": forms.HiddenInput(),
            "sequence": forms.HiddenInput(),
            "stage": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2",
                    "onchange": "keyResultChange($(this))",
                }
            ),
        }

    def __init__(self, *args, request=None, **kwargs):
        super(TaskFormCreate, self).__init__(*args, **kwargs)
        self.fields["stage"].widget.attrs.update({"id": "project_stage"})

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class TaskAllForm(ModelForm):
    """
    Form for Task model in task all view
    """

    cols = {
        "description": 12,
    }

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"

        widgets = {
            "sequence": forms.HiddenInput(),
        }

    def __init__(self, *args, request=None, **kwargs):
        super(TaskAllForm, self).__init__(*args, **kwargs)
        request = getattr(_thread_locals, "request")

        self.fields["stage"].widget.attrs.update({"id": "project_stage"})
        self.fields["project"].widget.attrs.update(
            {
                "onchange": """
        $('[name=dynamic_project]').val(this.value);
        setTimeout(() => {
            $('#getStageButton').click();
        }, 100);
"""
            }
        )

        request = getattr(_thread_locals, "request", None)
        employee = request.user.employee_get
        if not self.instance.pk:
            if request.user.is_superuser or request.user.has_perm("project.add_task"):
                projects = Project.objects.all()
            elif Project.objects.filter(managers=employee).exists():
                projects = Project.objects.filter(managers=employee)
            else:
                projects = Project.objects.none()
            self.fields["project"].queryset = projects

        else:
            task = self.instance
            if request.user.is_superuser:
                projects = Project.objects.all()
            elif employee in task.project.managers.all():
                projects = Project.objects.filter(managers=employee)
            elif employee in task.task_managers.all():
                # Limit fields accessible to task managers
                projects = Project.objects.filter(id=self.instance.project.id)
                self.fields["project"].disabled = True
                self.fields["stage"].disabled = True
                self.fields["task_managers"].disabled = True
            else:
                projects = Project.objects.filter(id=self.instance.project.id)
            self.fields["project"].queryset = projects


class TimeSheetForm(ModelForm):
    """
    Form for Time Sheet model
    """

    cols = {"description": 12}

    class Meta:
        """
        Meta class to add the additional info
        """

        model = TimeSheet
        fields = "__all__"

    def __init__(self, *args, request=None, **kwargs):
        super(TimeSheetForm, self).__init__(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        employee = request.user.employee_get
        hx_trigger_value = "change" if self.instance.id else "load,change"
        if not self.initial.get("project_id") == "dynamic_create":
            self.fields["project_id"].widget.attrs.update(
                {
                    "hx-target": "#id_task_id_parent_div",
                    "hx-trigger": hx_trigger_value,
                    "hx-include": "#id_task_id",
                    "hx-swap": "innerHTML",
                    "hx-get": "/project/get-tasks-of-project/",
                }
            )
        self.fields["task_id"].widget.attrs.update(
            {
                "hx-target": "#id_employee_id_parent_div",
                "hx-include": "#id_project_id",
                "hx-trigger": hx_trigger_value,
                "hx-swap": "innerHTML",
                "hx-get": "/project/get-members-of-project/",
            }
        )

        if not request.user.has_perm("project.add_timesheet"):
            projects = Project.objects.filter(
                Q(managers=employee)
                | Q(members=employee)
                | Q(task__task_members=employee)
                | Q(task__task_managers=employee)
            ).distinct()
            self.fields["project_id"].queryset = projects


class TimesheetInTaskForm(ModelForm):
    class Meta:
        """
        Meta class to add the additional info
        """

        model = TimeSheet
        fields = "__all__"
        widgets = {
            "project_id": forms.HiddenInput(),
            "task_id": forms.HiddenInput(),
        }


class ProjectStageForm(ModelForm):
    """
    Form for Project stage model
    """

    cols = {
        "title": 12,
    }

    class Meta:
        """
        Meta class to add the additional info
        """

        model = ProjectStage
        fields = "__all__"
        # exclude = ("project",)

        widgets = {"project": forms.HiddenInput()}


class TaskTimeSheetForm(ModelForm):
    """
    Form for Task model in timesheet form
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Task
        fields = "__all__"
        widgets = {
            "project": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(TaskTimeSheetForm, self).__init__(*args, **kwargs)
        # Add style to the start_date and end_date fields
        # self.fields["stage"].choices.append(
        #         ("create_new_project", "Create a new project")
        #     )
        self.fields["status"].widget.attrs.update(
            {
                "style": "width: 100%; height: 47px;",
                "class": "oh-select",
            }
        )
        self.fields["description"].widget.attrs.update(
            {
                "style": "width: 100%; height: 130px;",
                "class": "oh-select",
            }
        )
        self.fields["description"].widget.attrs.update(
            {
                "style": "width: 100%; height: 130px;",
                "class": "oh-select",
            }
        )

        self.fields["stage"].widget.attrs.update({"id": "project_stage"})
