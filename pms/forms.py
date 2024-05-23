"""
forms.py

This module is used to register the forms for pms models
"""

import datetime
import uuid
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.db.models.base import Model
from django.forms import ModelForm
from django.forms.utils import ErrorList
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm as BaseForm
from base.methods import reload_queryset
from employee.filters import EmployeeFilter
from employee.models import Department, JobPosition
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from pms.models import (
    AnonymousFeedback,
    Comment,
    Employee,
    EmployeeKeyResult,
    EmployeeObjective,
    Feedback,
    KeyResult,
    Meetings,
    Objective,
    Period,
    Question,
    QuestionOptions,
    QuestionTemplate,
)


def validate_date(start_date, end_date):
    """
    Validates that the start date is before or equal to the end date.
    """
    if start_date and end_date and start_date > end_date:
        raise forms.ValidationError("The start date must be before the end date.")


def set_date_field_initial(instance):
    """this is used to update change the date value format"""
    initial = {}
    if instance.start_date is not None:
        initial["start_date"] = instance.start_date.strftime("%Y-%m-%d")
    if instance.end_date is not None:
        initial["end_date"] = instance.end_date.strftime("%Y-%m-%d")
    return initial


class ObjectiveForm(BaseForm):
    """
    A form to create or update instances of the Objective, model.
    """

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "oh-input w-100", "type": "date"}),
    )
    add_assignees = forms.BooleanField(required=False)

    class Meta:
        """
        A nested class that specifies the model,fields and style of fields for the form.
        """

        model = Objective
        fields = [
            "title",
            "managers",
            "duration_unit",
            "duration",
            "key_result_id",
            "description",
            "add_assignees",
            "assignees",
            "start_date",
        ]
        exclude = ["is_active"]
        widgets = {
            "key_result_id": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                    "onchange": "keyResultChange($(this))",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Constructor for ObjectiveForm. If an instance is provided, set initial values for date fields
        """

        employee = kwargs.pop(
            "employee", None
        )  # access the logged-in user's information
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields["assignees"] = HorillaMultiSelectField(
                queryset=Employee.objects.all(),
                widget=HorillaMultiSelectWidget(
                    filter_route_name="employee-widget-filter",
                    filter_class=EmployeeFilter,
                    filter_instance_contex_name="f",
                    filter_template_path="employee_filters.html",
                    required=False,
                ),
                label="Assignees",
            )
        reload_queryset(self.fields)
        self.fields["key_result_id"].choices = list(
            self.fields["key_result_id"].choices
        )
        self.fields["key_result_id"].choices.append(
            ("create_new_key_result", "Create new Key result")
        )

    def clean(self):
        """
        Validates form fields and raises a validation error if any fields are invalid
        """
        cleaned_data = super().clean()
        add_assignees = cleaned_data.get("add_assignees")
        for field_name, field_instance in self.fields.items():
            if isinstance(field_instance, HorillaMultiSelectField):
                self.errors.pop(field_name, None)
                if (
                    add_assignees
                    and len(self.data.getlist(field_name)) < 1
                    and add_assignees
                ):
                    raise forms.ValidationError({field_name: "This field is required"})
                cleaned_data = super().clean()
                data = self.fields[field_name].queryset.filter(
                    id__in=self.data.getlist(field_name)
                )
                cleaned_data[field_name] = data
        cleaned_data = super().clean()
        add_assignees = cleaned_data.get("add_assignees")
        assignees = cleaned_data.get("assignees")
        start_date = cleaned_data.get("start_date")
        managers = cleaned_data.get("managers")
        if not managers or managers == None:
            raise forms.ValidationError("Managers is a required field")
        if add_assignees:
            if not assignees.exists() or start_date is None:
                raise forms.ValidationError("Assign employees and start date")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        # Check that start date is before end date
        validate_date(start_date, end_date)
        return cleaned_data

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class AddAssigneesForm(BaseForm):
    """
    A form to create or update instances of the EmployeeObjective, model.
    """

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "oh-input w-100", "type": "date"}),
    )

    class Meta:
        """
        A nested class that specifies the model,fields and style of fields for the form.
        """

        model = Objective
        fields = [
            "assignees",
        ]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["assignees"].queryset = self.fields[
                "assignees"
            ].queryset.exclude(id__in=self.instance.assignees.all())

    def clean(self):
        cleaned_data = super().clean()
        assignees = cleaned_data.get("assignees")
        if len(assignees) == 0:
            raise forms.ValidationError({"assignees": _("This field is required.")})
        return cleaned_data


class EmployeeObjectiveForm(BaseForm):
    """
    A form to create or update instances of the EmployeeObjective, model.
    """

    key_result_id = forms.ModelChoiceField(
        queryset=KeyResult.objects.all(),
        label=_("Key result"),
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select-2 select2-hidden-accessible",
                "onchange": "keyResultChange($(this))",
            }
        ),
    )

    class Meta:
        """
        A nested class that specifies the model,fields and style of fields for the form.
        """

        model = EmployeeObjective
        fields = [
            "objective_id",
            "start_date",
            "end_date",
            "status",
            "archive",
        ]
        exclude = ["is_active"]
        widgets = {
            "objective_id": forms.HiddenInput(),
            "start_date": forms.DateInput(
                attrs={"class": "oh-input w-100", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "oh-input w-100", "type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        try:
            del self.fields["key_result_id"]
        except Exception as _err:
            pass

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class EmployeeKeyResultForm(BaseForm):
    """
    A form to create or update instances of the EmployeeKeyResult, model.
    """

    key_result_id = forms.ModelChoiceField(
        queryset=KeyResult.objects.all(),
        label=_("Key result"),
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select-2 select2-hidden-accessible",
                "onchange": "keyResultChange($(this))",
            }
        ),
    )

    class Meta:
        """
        A nested class that specifies the model,fields and style of fields for the form.
        """

        model = EmployeeKeyResult
        fields = [
            "employee_objective_id",
            "key_result_id",
            "start_value",
            "current_value",
            "target_value",
            "start_date",
            "end_date",
            # 'archive',
        ]
        widgets = {
            "employee_objective_id": forms.HiddenInput(),
            "start_date": forms.DateInput(
                attrs={"class": "oh-input w-100", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "oh-input w-100", "type": "date"}
            ),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get("employee_objective_id"):
            if type(self.initial.get("employee_objective_id")) == int:
                self.verbose_name = EmployeeObjective.objects.get(
                    id=(self.initial.get("employee_objective_id"))
                ).employee_id
            else:
                self.verbose_name = self.initial.get(
                    "employee_objective_id"
                ).employee_id

        reload_queryset(self.fields)
        self.fields["key_result_id"].choices = list(
            self.fields["key_result_id"].choices
        )
        self.fields["key_result_id"].choices.append(
            ("create_new_key_result", "Create new Key result")
        )


from base.forms import ModelForm as MF


class KRForm(MF):
    """
    A form used for creating KeyResult object
    """

    class Meta:
        """
        A nested class that specifies the model,fields and exclude fields for the form.
        """

        model = KeyResult
        fields = "__all__"
        exclude = [
            "history",
            "objects",
            "is_active",
        ]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        duration = cleaned_data.get("duration")
        target_value = cleaned_data.get("target_value")
        progress_type = cleaned_data.get("progress_type")

        if duration is None or duration == "":
            raise ValidationError({"duration": "This field is required"})
        if target_value is None or target_value == "":
            raise ValidationError({"target_value": "This field is required"})
        if duration <= 0:
            raise ValidationError(
                {"duration": "Duration cannot be less than or equal to zero"}
            )
        if target_value <= 0:
            raise ValidationError(
                {"target_value": "Duration cannot be less than or equal to zero"}
            )
        if progress_type == "%" and target_value > 100:
            raise ValidationError(
                {
                    "target_value": 'Target value cannot be greater than hundred for progress type "percentage"'
                }
            )


class KeyResultForm(ModelForm):
    """
    A form used for creating and updating EmployeeKeyResult objects.

    Includes fields for title, description, current value, target value,
    start date, end date, progress type, and the associated period and employee.

    Excludes fields for status, progress_boolean, progress_integer,
    employee_objective_id, and start value.

    """

    period = forms.ModelChoiceField(
        queryset=Period.objects.all(),
        empty_label="",
        widget=forms.Select(attrs={"style": "width:100%; display:none;"}),
        required=False,
    )

    class Meta:
        """
        A nested class that specifies the model,fields and exclude fields for the form.
        """

        model = EmployeeKeyResult
        fields = "__all__"
        exclude = [
            "status",
            "progress_boolean",
            "progress_integer",
            "employee_objective_id",
            "start_value",
        ]

        widgets = {
            "key_result": forms.TextInput(
                attrs={
                    "placeholder": _("Enter a title"),
                    "class": "oh-input w-100",
                    "required": True,
                }
            ),
            "key_result_description": forms.Textarea(
                attrs={
                    "placeholder": _("Enter a description"),
                    "class": "oh-input oh-input--textarea w-100",
                    "required": True,
                    "rows": 3,
                    "cols": 40,
                }
            ),
            "employee_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                    "style": "display:none;",
                }
            ),
            "current_value": forms.NumberInput(
                attrs={"class": "oh-input w-100", "required": True}
            ),
            "target_value": forms.NumberInput(
                attrs={"class": "oh-input w-100", "required": True}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input w-100", "required": True}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input w-100", "required": True}
            ),
            "progress_type": forms.Select(
                attrs={
                    "class": "oh-select oh-select--lg oh-select-no-search w-100",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance:
            kwargs["initial"] = set_date_field_initial(instance)
        employee = kwargs.pop(
            "employee", None
        )  # access the logged-in user's information
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        employees = Employee.objects.filter(
            is_active=True, employee_work_info__reporting_manager_id=employee
        )
        if employee and employees:
            # manager level access
            self.fields["employee_id"].queryset = employees

        # Set unique IDs for employee_id fields to prevent conflicts with other forms on the same page
        self.fields["employee_id"].widget.attrs.update({"id": str(uuid.uuid4())})

    def clean_value(self, value_type):
        """
        Validate the 'current_value' and 'target_value' field of model EmployeeKeyResult.
        """
        value = self.cleaned_data.get(value_type)
        other_value = self.cleaned_data.get(
            "current_value" if value_type == "target_value" else "target_value"
        )
        if (
            value is not None
            and other_value is not None
            and value_type == "current_value"
            and value > other_value
        ):
            raise forms.ValidationError(
                "Current value cannot be greater than target value"
            )
        elif (
            value is not None
            and other_value is not None
            and value_type == "target_value"
            and value < other_value
        ):
            raise forms.ValidationError(
                "Target value cannot be less than current value"
            )
        return value

    def clean(self):
        cleaned_data = super().clean()
        employee_objective_id = self.initial.get("employee_objective_id")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        target_value = cleaned_data.get("target_value")
        current_value = cleaned_data.get("current_value")

        validate_date(start_date, end_date)
        # date comparing with objective start and end date
        if employee_objective_id and start_date and end_date:
            if start_date < employee_objective_id.start_date:
                raise ValidationError("Start date should be after Objective start date")

            if end_date > employee_objective_id.end_date:
                raise ValidationError("End date should be below Objective end date")
        else:
            raise forms.ValidationError("Employee Objective not found")
        # target value and current value comparison
        if target_value <= 0:
            raise ValidationError("Target value should be greater than zero")
        if current_value > target_value:
            raise forms.ValidationError(
                "Current value cannot be greater than target value"
            )
        return cleaned_data


class FeedbackForm(ModelForm):
    """
    A form used for creating and updating Feedback objects.
    """

    period = forms.ModelChoiceField(
        queryset=Period.objects.all(),
        empty_label="",
        widget=forms.Select(
            attrs={
                "class": " oh-select--period-change ",
                "style": "width:100%; display:none;",
            }
        ),
        required=False,
    )

    class Meta:
        """
        A nested class that specifies the model,fields and exclude fields for the form.
        """

        model = Feedback
        fields = "__all__"
        exclude = ["status", "archive", "is_active"]

        widgets = {
            "review_cycle": forms.TextInput(
                attrs={"placeholder": _("Enter a title"), "class": "oh-input w-100"}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "employee_id": forms.Select(
                attrs={
                    "class": " oh-select--employee-change",
                    "style": "width:100%; display:none;",
                    "required": "false",
                },
            ),
            "manager_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select-2 ",
                    "style": "width:100%; display:none;",
                    "required": "false",
                },
            ),
            "colleague_id": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 w-100",
                    "multiple": "multiple",
                    "style": "width:100%; display:none;",
                }
            ),
            "subordinate_id": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select-2 w-100",
                    "multiple": "multiple",
                    "style": "width:100%; display:none;",
                }
            ),
            "question_template_id": forms.Select(
                attrs={
                    "class": "oh-select oh-select--lg oh-select-no-search",
                    "style": "width:100%; display:none;",
                    "required": "false",
                }
            ),
            "cyclic_feedback": forms.CheckboxInput(
                attrs={
                    "class": "oh-switch__checkbox",
                }
            ),
            "cyclic_feedback_period": forms.Select(
                attrs={
                    "class": "oh-select oh-select--lg oh-select-no-search",
                    "style": "width:100%; display:none;",
                }
            ),
            "cyclic_feedback_days_count": forms.NumberInput(
                attrs={
                    "class": "oh-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes the feedback form instance.
        If an instance is provided, sets the initial value for the form's date fields.
        """

        instance = kwargs.get("instance")
        employee = kwargs.pop(
            "employee", None
        )  # access the logged-in user's information
        if instance:
            kwargs["initial"] = set_date_field_initial(instance)
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["period"].choices = list(self.fields["period"].choices)
        self.fields["period"].choices.append(("create_new_period", "Create new period"))

        if instance:
            self.fields["employee_id"].widget.attrs.update(
                {"class": "oh-select oh-select-2"}
            )
        employees = Employee.objects.filter(
            is_active=True, employee_work_info__reporting_manager_id=employee
        )
        if employee and employees:
            department = employee.employee_work_info.department_id
            employees = Employee.objects.filter(
                is_active=True, employee_work_info__department_id=department
            )
            # manager level access
            self.fields["employee_id"].queryset = employees
            self.fields["manager_id"].queryset = employees
            self.fields["colleague_id"].queryset = employees
            self.fields["subordinate_id"].queryset = employees

    def clean(self):
        """
        Cleans and validates the feedback form data.
        Ensures that the start date is before the end date and validates the start date.
        """
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if "employee_key_results_id" in self.errors:
            del self.errors["employee_key_results_id"]

        self.instance
        validate_date(start_date, end_date)
        return cleaned_data


class QuestionTemplateForm(ModelForm):
    """
    Form for creating or updating a question template instance
    """

    question_template = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "oh-input oh-input--small oh-input--res-height w-100",
                "placeholder": _("For Developer"),
            }
        )
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the form.
        """

        model = QuestionTemplate
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["company_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2 w-100",
            }
        )

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class QuestionForm(ModelForm):
    """
    Form for creating or updating a question  instance
    """

    question = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "oh-input oh-input--small oh-input--res-height w-100",
                "placeholder": _("Enter question"),
            }
        ),
        required=True,
    )
    options = forms.ModelChoiceField(
        queryset=QuestionOptions.objects.all(), required=False
    )
    option_a = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )
    option_b = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )
    option_c = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )
    option_d = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "oh-input oh-input--res-height w-100", "type": "text"}
        ),
        max_length=240,
        required=False,
    )

    class Meta:
        """
        A nested class that specifies the model,exclude fields and style of fields for the form.
        """

        model = Question
        exclude = ["question_option_id", "template_id", "is_active"]
        widgets = {
            "question_type": forms.Select(
                attrs={
                    "class": "oh-select oh-select--sm oh-select-no-search oh-select--qa-change w-100",
                    "required": True,
                }
            )
        }
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["question_type"].widget.attrs.update({"id": str(uuid.uuid4())})
        if (
            self.instance.pk
            and self.instance.question_type == "4"
            and self.instance.question_options.first()
        ):
            self.fields["option_a"].initial = (
                self.instance.question_options.first().option_a
            )
            self.fields["option_b"].initial = (
                self.instance.question_options.first().option_b
            )
            self.fields["option_c"].initial = (
                self.instance.question_options.first().option_c
            )
            self.fields["option_d"].initial = (
                self.instance.question_options.first().option_d
            )


class ObjectiveCommentForm(ModelForm):
    """
    A form used to add a comment to an employee's objective.
    Excludes fields for the employee and employee objective and uses a textarea widget for the comment field.
    """

    class Meta:
        """
        A nested class that specifies the model,exclude fields and style of fields for the form.
        """

        model = Comment
        exclude = ["employee_id", "employee_objective_id"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "oh-input oh-input--small oh-input--textarea",
                    "rows": "4",
                    "placeholder": _("Add a comment..."),
                }
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)


class PeriodForm(ModelForm):
    """
    A form for creating or updating a Period object.
    """

    class Meta:
        """
        A nested class that specifies the model,fields and style of fields for the form.
        """

        model = Period
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "period_name": forms.TextInput(
                attrs={"placeholder": "Q1.", "class": "oh-input w-100"}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        django forms not showing value inside the date, time html element.
        so here overriding default forms instance method to set initial value
        """
        if instance := kwargs.get("instance"):
            kwargs["initial"] = set_date_field_initial(instance)
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["company_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2 w-100",
            }
        )

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        validate_date(start_date, end_date)


class AnonymousFeedbackForm(BaseForm):
    class Meta:
        model = AnonymousFeedback
        fields = "__all__"
        exclude = ["status", "archive"]


class MeetingsForm(BaseForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "oh-input w-100", "type": "datetime-local"}
        ),
    )

    class Meta:
        model = Meetings
        fields = "__all__"
        exclude = ["response", "is_active"]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()

        answerable_employees = self.data.getlist("answer_employees", [])
        employees = Employee.objects.filter(id__in=answerable_employees)
        cleaned_data["answer_employees"] = employees

        employee_id = self.data.getlist("employee_id", [])
        employees = Employee.objects.filter(id__in=employee_id)
        cleaned_data["employee_id"] = employees

        if isinstance(self.fields["employee_id"], HorillaMultiSelectField):
            ids = self.data.getlist("employee_id")
            if ids:
                self.errors.pop("employee_id", None)
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            employees = Employee.objects.filter(id__in=self.instance.employee_id.all())
            self.fields["answer_employees"].queryset = employees
        else:
            self.fields["employee_id"] = HorillaMultiSelectField(
                queryset=Employee.objects.filter(employee_work_info__isnull=False),
                widget=HorillaMultiSelectWidget(
                    filter_route_name="employee-widget-filter",
                    filter_class=EmployeeFilter,
                    filter_instance_contex_name="f",
                    filter_template_path="employee_filters.html",
                ),
                label=_("Employees"),
            )
        try:
            if self.data.getlist("employee_id"):
                employees = Employee.objects.filter(
                    id__in=self.data.getlist("employee_id")
                )
                self.fields["answer_employees"].queryset = employees
        except:
            pass
