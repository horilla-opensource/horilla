"""
forms.py

This module contains the form classes used in the application.

Each form represents a specific functionality or data input in the
application. They are responsible for validating
and processing user input data.

Classes:
- YourForm: Represents a form for handling specific data input.

Usage:
from django import forms

class YourForm(forms.Form):
    field_name = forms.CharField()

    def clean_field_name(self):
        # Custom validation logic goes here
        pass
"""

from typing import Any

from django import forms
from django.template.loader import render_to_string

from base.forms import ModelForm
from base.methods import filtersubordinatesemployeemodel, is_reportingmanager
from base.models import Department, JobPosition
from employee.forms import MultipleFileField
from employee.models import Employee
from helpdesk.models import (
    FAQ,
    Attachment,
    Comment,
    DepartmentManager,
    FAQCategory,
    Ticket,
    TicketType,
)
from horilla import horilla_middlewares


class TicketTypeForm(ModelForm):

    class Meta:
        model = TicketType
        fields = "__all__"
        exclude = ["is_active"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html


class FAQForm(ModelForm):
    class Meta:
        model = FAQ
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "category": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        """Initializes the FAQ form instance and adjusts the tags field."""
        super().__init__(*args, **kwargs)

        if "tags" in self.fields:
            self.fields["tags"].choices = list(self.fields["tags"].choices)
            self.fields["tags"].widget.attrs.update({"onchange": "updateTag(this)"})
            self.fields["tags"].choices.append(("create_new_tag", "Create new tag"))


class TicketForm(ModelForm):

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "employee_id",
            "description",
            "ticket_type",
            "priority",
            "assigning_type",
            "raised_on",
            "deadline",
            "status",
            "tags",
        ]
        widgets = {
            "raised_on": forms.Select(
                attrs={"class": "oh-select oh-select-2", "required": "true"}
            ),
            "description": forms.Textarea(
                attrs={
                    "data-summernote": True,
                    "hidden": True,
                }
            ),
        }

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields.pop("attachment", None)
        else:
            self.fields["attachment"] = MultipleFileField(
                label="Attachements", required=False
            )
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        instance = kwargs.get("instance")
        if instance:
            employee = instance.employee_id
        else:
            employee = request.user.employee_get
        # initialising employee queryset according to the user
        self.fields["employee_id"].queryset = (
            filtersubordinatesemployeemodel(
                request,
                Employee.objects.filter(is_active=True),
                perm="helpdesk.add_ticket",
            )
        ).distinct() | (
            Employee.objects.filter(employee_user_id=request.user)
        ).distinct()
        self.fields["employee_id"].initial = employee
        # appending dynamic create option according to user
        if is_reportingmanager(request) or request.user.has_perm(
            "helpdesk.add_tickettype"
        ):
            self.fields["ticket_type"].choices = list(
                self.fields["ticket_type"].choices
            )
            self.fields["ticket_type"].choices.append(
                ("create_new_ticket_type", "Create new ticket type")
            )
        if is_reportingmanager(request) or request.user.has_perm("base.add_tags"):
            self.fields["tags"].choices = list(self.fields["tags"].choices)
            self.fields["tags"].choices.append(("create_new_tag", "Create new tag"))


class TicketTagForm(ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        """
        Initializes the Ticket tag form instance.
        If an instance is provided, sets the initial value for the form's .
        """
        super().__init__(*args, **kwargs)
        request = getattr(horilla_middlewares._thread_locals, "request", None)

        if (
            request
            and request.user.is_authenticated
            and (is_reportingmanager(request) or request.user.has_perm("base.add_tags"))
        ):
            self.fields["tags"].widget.attrs.update({"onchange": "updateTag(this)"})
            self.fields["tags"].choices = list(self.fields["tags"].choices)
            self.fields["tags"].choices.append(("create_new_tag", "Create new tag"))


class TicketRaisedOnForm(ModelForm):
    class Meta:
        model = Ticket
        fields = ["assigning_type", "raised_on"]
        widgets = {
            "raised_on": forms.Select(
                attrs={"class": "oh-select oh-select-2", "required": "true"},
            ),
        }


class TicketAssigneesForm(ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "assigned_to",
        ]


class FAQCategoryForm(ModelForm):
    class Meta:
        model = FAQCategory
        fields = "__all__"
        exclude = ["is_active"]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = [
            "comment",
        ]
        exclude = ["is_active"]
        widgets = {"employee_id": forms.HiddenInput()}


class AttachmentForm(forms.ModelForm):
    file = forms.FileField(
        widget=forms.TextInput(
            attrs={
                "name": "file",
                "type": "File",
                "class": "form-control",
                "multiple": "True",
            }
        ),
        label="",
    )

    class Meta:
        model = Attachment
        fields = ["file", "comment", "ticket"]
        exclude = ["is_active"]


class DepartmentManagerCreateForm(ModelForm):
    class Meta:
        model = DepartmentManager
        fields = ["department", "manager"]
        widgets = {
            "department": forms.Select(
                attrs={
                    "onchange": "getDepartmentEmployees($(this))",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "instance" in kwargs:
            department = kwargs["instance"].department
            # Get the employees related to this department
            employees = department.employeeworkinformation_set.values_list(
                "employee_id", flat=True
            )
            # Set the manager field queryset to be those employees
            self.fields["manager"].queryset = Employee.objects.filter(id__in=employees)
