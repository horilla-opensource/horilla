"""
This module provides Horilla ModelForms for creating and managing leave-related data,
including leave type, leave request, leave allocation request, holidays and company leaves.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any

from django import forms
from django.apps import apps
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.widgets import TextInput
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm as BaseModelForm
from base.methods import filtersubordinatesemployeemodel, reload_queryset
from employee.filters import EmployeeFilter
from employee.forms import MultipleFileField
from employee.models import Employee
from horilla import horilla_middlewares
from horilla_widgets.forms import HorillaForm, HorillaModelForm
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from leave.methods import get_leave_day_attendance
from leave.models import (
    AvailableLeave,
    LeaveAllocationRequest,
    LeaveallocationrequestComment,
    LeaveRequest,
    LeaverequestComment,
    LeaverequestFile,
    LeaveType,
    RestrictLeave,
)

CHOICES = [("yes", _("Yes")), ("no", _("No"))]
LEAVE_MAX_LIMIT = 1e5


class ConditionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select,)):
                field.widget.attrs["style"] = (
                    "width:100%; height:50px;border: 1px solid hsl(213deg,22%,84%);border-radius: 0rem;padding: 0.8rem 1.25rem;"
                )
            elif isinstance(widget, forms.DateInput):
                field.initial = date.today
                widget.input_type = "date"
                widget.format = "%Y-%m-%d"
                field.input_formats = ["%Y-%m-%d"]

            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": field.label}
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": field.label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})
        try:
            self.fields["employee_id"].initial = request.user.employee_get
        except:
            pass

        try:
            self.fields["company_id"].initial = request.user.employee_get.get_company
        except:
            pass


class LeaveTypeAdminForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if f := self.fields.get("company_id"):
            from horilla_widgets.forms import default_select_option_template

            w = getattr(f.widget, "widget", f.widget)
            if isinstance(w, forms.Select):
                w.option_template_name = default_select_option_template


class LeaveTypeForm(ConditionForm):

    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.all(),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
            required=False,
        ),
        label=_("Employee"),
    )

    class Meta:
        model = LeaveType
        fields = "__all__"
        exclude = ["is_active"]
        labels = {
            "name": _("Name"),
        }
        widgets = {
            "color": TextInput(attrs={"type": "color", "style": "height:40px;"}),
            "period_in": forms.HiddenInput(),
            "total_days": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        if "employee_id" in self.errors:
            del self.errors["employee_id"]
        if "exceed_days" in self.errors:
            del self.errors["exceed_days"]
        if not cleaned_data["limit_leave"]:
            cleaned_data["total_days"] = LEAVE_MAX_LIMIT
            cleaned_data["reset"] = True
            cleaned_data["reset_based"] = "yearly"
            cleaned_data["reset_month"] = "1"
            cleaned_data["reset_day"] = "1"

        return cleaned_data

    def save(self, *args, **kwargs):
        leave_type = super().save(*args, **kwargs)
        if employees := self.data.getlist("employee_id"):
            for employee_id in employees:
                employee = Employee.objects.get(id=employee_id)
                AvailableLeave(
                    leave_type_id=leave_type,
                    employee_id=employee,
                    available_days=leave_type.total_days,
                ).save()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class UpdateLeaveTypeForm(ConditionForm):

    def __init__(self, *args, **kwargs):
        super(UpdateLeaveTypeForm, self).__init__(*args, **kwargs)

        empty_fields = []
        for field_name, field_value in self.instance.__dict__.items():
            if field_value is None or field_value == "":
                if field_name.endswith("_id"):
                    foreign_key_field_name = re.sub("_id$", "", field_name)
                    empty_fields.append(foreign_key_field_name)
                empty_fields.append(field_name)

        for index, visible in enumerate(self.visible_fields()):
            if list(self.fields.keys())[index] in empty_fields:
                visible.field.widget.attrs["style"] = (
                    "display:none;width:100%; height:50px;border: 1px solid hsl(213deg,22%,84%);border-radius: 0rem;padding: 0.8rem 1.25rem;"
                )
                visible.field.widget.attrs["data-hidden"] = True

        if expire_date := self.instance.carryforward_expire_date:
            self.fields["carryforward_expire_date"] = expire_date

    class Meta:
        model = LeaveType
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "color": TextInput(attrs={"type": "color", "style": "height:40px;"}),
            "period_in": forms.HiddenInput(),
            "total_days": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        if "exceed_days" in self.errors:
            del self.errors["exceed_days"]
        if not cleaned_data["limit_leave"]:
            cleaned_data["total_days"] = LEAVE_MAX_LIMIT
            cleaned_data["reset"] = True
            cleaned_data["reset_based"] = "yearly"
            cleaned_data["reset_month"] = "1"
            cleaned_data["reset_day"] = "1"

        return cleaned_data

    def save(self, *args, **kwargs):
        leave_type = super().save(*args, **kwargs)


class LeaveRequestCreationForm(BaseModelForm):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.fields["attachment"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"
        self.fields["leave_type_id"].widget.attrs.update(
            {
                "hx-include": "#leaveRequestCreateForm",
                "hx-target": "#availableLeaveCount",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-get": "/leave/employee-available-leave-count",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "hx-target": "#id_leave_type_id_parent_div",
                "hx-trigger": "change",
                "hx-get": "/leave/get-employee-leave-types?form=LeaveRequestCreationForm",
            }
        )
        self.fields["start_date"].widget.attrs.update(
            {
                "hx-include": "#leaveRequestCreateForm",
                "hx-target": "#availableLeaveCount",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-get": "/leave/employee-available-leave-count",
            }
        )

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    class Meta:
        model = LeaveRequest
        fields = [
            "employee_id",
            "leave_type_id",
            "start_date",
            "start_date_breakdown",
            "end_date",
            "end_date_breakdown",
            "attachment",
            "description",
        ]


class LeaveRequestUpdationForm(BaseModelForm):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        leave_request = self.instance
        employee = leave_request.employee_id
        leave_type = leave_request.leave_type_id

        if employee:
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )

            if leave_type and leave_type.id not in assigned_leave_types.values_list(
                "id", flat=True
            ):
                assigned_leave_types |= LeaveType.objects.filter(id=leave_type.id)

            self.fields["leave_type_id"].queryset = assigned_leave_types

        self.fields["leave_type_id"].widget.attrs.update(
            {
                "hx-include": "#leaveRequestUpdateForm",
                "hx-target": "#assinedLeaveAvailableCount",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-get": "/leave/employee-available-leave-count",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "hx-target": "#id_leave_type_id_parent_div",
                "hx-trigger": "change",
                "hx-get": "/leave/get-employee-leave-types?form=LeaveRequestUpdationForm",
            }
        )
        self.fields["attachment"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"

        self.fields["start_date"].widget.attrs.update(
            {
                "hx-include": "#leaveRequestUpdateForm",
                "hx-target": "#assinedLeaveAvailableCount",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-get": "/leave/employee-available-leave-count",
            }
        )

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    class Meta:
        model = LeaveRequest
        fields = [
            "leave_type_id",
            "employee_id",
            "start_date",
            "start_date_breakdown",
            "end_date",
            "end_date_breakdown",
            "attachment",
            "description",
        ]


class AvailableLeaveForm(BaseModelForm):
    """
    Form for managing available leave data.

    This form allows users to manage available leave data by specifying details such as
    the leave type and employee.

    Attributes:
        - leave_type_id: A ModelChoiceField representing the leave type associated with the available leave.
        - employee_id: A ModelChoiceField representing the employee associated with the available leave.
    """

    leave_type_id = forms.ModelChoiceField(
        queryset=LeaveType.objects.all(),
        widget=forms.SelectMultiple,
        empty_label=None,
    )
    employee_id = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple,
        empty_label=None,
    )

    class Meta:
        model = AvailableLeave
        fields = ["leave_type_id", "employee_id", "is_active"]


class LeaveOneAssignForm(HorillaModelForm):
    """
    Form for assigning available leave to employees.

    This form allows administrators to assign available leave to a single employee
    by specifying the employee and setting the is_active flag.

    Attributes:
        - employee_id: A HorillaMultiSelectField representing the employee to assign leave to.
    """

    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.all(),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
            required=True,
        ),
        label="Employee",
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = AvailableLeave
        fields = ["employee_id", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)


class AvailableLeaveUpdateForm(BaseModelForm):
    """
    Form for updating available leave data.

    This form allows users to update available leave data by modifying fields such as
    available_days, carryforward_days, and is_active.

    Attributes:
        - Meta: Inner class defining metadata options.
            - model: The model associated with the form (AvailableLeave).
            - fields: A list of fields to include in the form.
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AvailableLeave
        fields = ["available_days", "carryforward_days", "is_active"]


class UserLeaveRequestForm(BaseModelForm):
    description = forms.CharField(label=_("Description"), widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        leave_type = kwargs.pop("initial", None)
        employee = kwargs.pop("employee", None)
        super(UserLeaveRequestForm, self).__init__(*args, **kwargs)
        self.fields["attachment"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"
        if employee:
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )
            self.fields["leave_type_id"].queryset = assigned_leave_types
        if leave_type:
            self.fields["leave_type_id"].queryset = LeaveType.objects.filter(
                id=leave_type["leave_type_id"].id
            )
            self.fields["leave_type_id"].initial = leave_type["leave_type_id"].id
            self.fields["leave_type_id"].empty_label = None

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaveRequest
        fields = [
            "employee_id",
            "leave_type_id",
            "start_date",
            "start_date_breakdown",
            "end_date",
            "end_date_breakdown",
            "attachment",
            "description",
        ]
        widgets = {
            "employee_id": forms.HiddenInput(),
        }


excluded_fields = [
    "id",
    "approved_available_days",
    "approved_carryforward_days",
    "created_at",
    "attachment",
]


class AvailableLeaveColumnExportForm(forms.Form):
    """
    Form for selecting columns to export in available leave data.

    This form allows users to select specific columns from the AvailableLeave model
    for export. The available columns are dynamically generated based on the
    model's meta information, excluding specified excluded_fields.

    Attributes:
        - model_fields: A list of fields in the AvailableLeave model.
        - field_choices: A list of field choices for the form, consisting of field names
          and their verbose names, excluding specified excluded_fields.
        - selected_fields: A MultipleChoiceField representing the selected columns
          to be exported.
    """

    model_fields = AvailableLeave._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "leave_type_id",
            "available_days",
            "carryforward_days",
            "total_leave_days",
        ],
    )


class RejectForm(forms.Form):
    """
    Form for rejecting a leave request.

    This form allows administrators to provide a rejection reason when rejecting
    a leave request.

    Attributes:
        - reason: A CharField representing the reason for rejecting the leave request.
    """

    reason = forms.CharField(
        label=_("Rejection Reason"),
        widget=forms.Textarea(attrs={"rows": 4, "class": "p-4 oh-input w-100"}),
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaveRequest
        fields = ["reject_reason"]


class UserLeaveRequestCreationForm(BaseModelForm):

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop("employee", None)
        super().__init__(*args, **kwargs)
        self.fields["attachment"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"
        if employee:
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )
            self.fields["leave_type_id"].queryset = assigned_leave_types
        self.fields["leave_type_id"].widget.attrs.update(
            {
                "hx-include": "#userLeaveForm",
                "hx-target": "#availableLeaveCount",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-get": f"/leave/employee-available-leave-count",
            }
        )
        self.fields["employee_id"].initial = employee

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaveRequest
        fields = [
            "leave_type_id",
            "employee_id",
            "start_date",
            "start_date_breakdown",
            "end_date",
            "end_date_breakdown",
            "attachment",
            "description",
            "requested_days",
        ]
        widgets = {
            "employee_id": forms.HiddenInput(),
            "requested_days": forms.HiddenInput(),
        }


class LeaveAllocationRequestForm(BaseModelForm):
    """
    Form for creating a leave allocation request.

    This form allows users to create a leave allocation request by specifying
    details such as leave type, employee, requested days, description, and attachment.

    Methods:
        - as_p: Render the form fields as HTML table rows with Bootstrap styling.
    """

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaveAllocationRequest
        fields = [
            "leave_type_id",
            "employee_id",
            "requested_days",
            "description",
            "attachment",
        ]


class LeaveAllocationRequestRejectForm(forms.Form):
    """
    Form for rejecting a leave allocation request.

    This form allows administrators to provide a rejection reason when rejecting
    a leave allocation request.

    Attributes:
        - reason: A CharField representing the reason for rejecting the leave allocation request.
    """

    reason = forms.CharField(
        label=_("Rejection Reason"),
        widget=forms.Textarea(attrs={"rows": 4, "class": "p-4 oh-input w-100"}),
    )

    class Meta:
        model = LeaveAllocationRequest
        fields = ["reject_reason"]


class LeaveRequestExportForm(forms.Form):
    """
    Form for selecting fields to export in a leave request export.

    This form allows users to select specific fields from the LeaveRequest model
    for export. The available fields are dynamically generated based on the
    model's meta information, excluding certain fields specified in 'excluded_fields'.

    Attributes:
        - model_fields: A list of fields in the LeaveRequest model.
        - field_choices: A list of field choices for the form, consisting of field names
          and their verbose names, excluding specified excluded_fields.
        - selected_fields: A MultipleChoiceField representing the selected fields
          to be exported.
    """

    model_fields = LeaveRequest._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]

    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "leave_type_Assignid",
            "start_date",
            "start_date_breakdown",
            "end_date",
            "end_date_breakdown",
            "requested_days",
            "description",
            "status",
        ],
    )


class AssignLeaveForm(HorillaForm):
    """
    Form for Payslip
    """

    leave_type_id = forms.ModelChoiceField(
        queryset=LeaveType.objects.all(),
        widget=forms.SelectMultiple(
            attrs={"class": "oh-select oh-select-2 mb-2", "required": True}
        ),
        empty_label=None,
        label="Leave Type",
        required=False,
    )
    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.all(),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
            required=True,
        ),
        label="Employee",
    )

    def clean(self):
        cleaned_data = super().clean()
        employee_id = cleaned_data.get("employee_id")
        leave_type_id = cleaned_data.get("leave_type_id")

        if not employee_id:
            raise forms.ValidationError({"employee_id": "This field is required"})
        if not leave_type_id:
            raise forms.ValidationError({"leave_type_id": "This field is required"})
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["employee_id"].widget.attrs.update(
            {"required": True, "id": uuid.uuid4()}
        ),
        self.fields["leave_type_id"].label = "Leave Type"


class LeaverequestcommentForm(BaseModelForm):
    """
    LeaverequestComment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaverequestComment
        fields = ("comment",)


class LeaveCommentForm(BaseModelForm):
    """
    Leave request comment model form
    """

    verbose_name = "Add Comment"

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaverequestComment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["files"] = MultipleFileField(label="files")
        self.fields["files"].widget.attrs["accept"] = ".jpg, .jpeg, .png, .pdf"

        self.fields["files"].required = False

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        multiple_files_ids = []
        files = None
        if self.files.getlist("files"):
            files = self.files.getlist("files")
            self.instance.attachemnt = files[0]
            multiple_files_ids = []
            for attachemnt in files:
                file_instance = LeaverequestFile()
                file_instance.file = attachemnt
                file_instance.save()
                multiple_files_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.files.add(*multiple_files_ids)
        return instance, files


class LeaveallocationrequestcommentForm(BaseModelForm):
    """
    Leave Allocation Requestcomment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaveallocationrequestComment
        fields = ("comment",)


class LeaveAllocationCommentForm(BaseModelForm):
    """
    Leave request comment model form
    """

    verbose_name = "Add Comment"

    class Meta:
        """
        Meta class for additional options
        """

        model = LeaveallocationrequestComment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["files"] = MultipleFileField(label="files")
        self.fields["files"].required = False

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        multiple_files_ids = []
        files = None
        if self.files.getlist("files"):
            files = self.files.getlist("files")
            self.instance.attachemnt = files[0]
            multiple_files_ids = []
            for attachemnt in files:
                file_instance = LeaverequestFile()
                file_instance.file = attachemnt
                file_instance.save()
                multiple_files_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.files.add(*multiple_files_ids)
        return instance, files


class RestrictLeaveForm(BaseModelForm):
    def clean_end_date(self):
        start_date = self.cleaned_data.get("start_date")
        end_date = self.cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                _("End date should not be earlier than the start date.")
            )

        return end_date

    class Meta:
        model = RestrictLeave
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super(RestrictLeaveForm, self).__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["autocomplete"] = "title"
        self.fields["department"].widget.attrs.update(
            {
                "hx-include": "#leaveRestrictForm",
                "hx-target": "#restrictLeaveJobPosition",
                "hx-trigger": "change",
                "hx-get": "/leave/get-restrict-job-positions",
            }
        )


if apps.is_installed("attendance"):
    from .models import CompensatoryLeaveRequest, CompensatoryLeaverequestComment

    class CompensatoryLeaveForm(BaseModelForm):
        """
        Form for creating a leave allocation request.

        This form allows users to create a leave allocation request by specifying
        details such as leave type, employee, requested days, description, and attachment.

        Methods:
            - as_p: Render the form fields as HTML table rows with Bootstrap styling.
        """

        class Meta:
            """
            Meta class for additional options
            """

            attendance_id = forms.MultipleChoiceField(required=True)
            model = CompensatoryLeaveRequest
            fields = [
                # "leave_type_id",
                "employee_id",
                "attendance_id",
                # "requested_days",
                "description",
            ]

        def __init__(self, *args, **kwargs):
            super(CompensatoryLeaveForm, self).__init__(*args, **kwargs)

            request = getattr(horilla_middlewares._thread_locals, "request", None)
            instance_id = None
            if self.instance:
                instance_id = self.instance.id
            if (
                request
                and hasattr(request, "user")
                and hasattr(request.user, "employee_get")
            ):
                employee = request.user.employee_get
                holiday_attendance = get_leave_day_attendance(
                    employee, comp_id=instance_id
                )
                # Get a list of tuples containing (id, attendance_date)
                attendance_dates = list(
                    holiday_attendance.values_list("id", "attendance_date")
                )
                # Set the queryset of attendance_id to the attendance_dates
                self.fields["attendance_id"].choices = attendance_dates
            queryset = (
                filtersubordinatesemployeemodel(
                    request, Employee.objects.filter(is_active=True)
                )
                | Employee.objects.filter(employee_user_id=request.user)
            ).distinct()
            self.fields["employee_id"].queryset = queryset
            self.fields["employee_id"].widget.attrs.update(
                {
                    "hx-target": "#id_attendance_id_parent_div",
                    "hx-trigger": "change",
                    "hx-get": "/leave/get-leave-attendance-dates",
                }
            )

        def as_p(self, *args, **kwargs):
            """
            Render the form fields as HTML table rows with Bootstrap styling.
            """
            context = {"form": self}
            table_html = render_to_string("horilla_form.html", context)
            return table_html

        def clean(self):
            cleaned_data = super().clean()
            attendance_id = cleaned_data.get("attendance_id")
            if attendance_id is None or len(attendance_id) < 1:
                raise forms.ValidationError(
                    {"attendance_id": _("This field is required.")}
                )
            employee = cleaned_data.get("employee_id")
            attendance_repeat = False
            instance_id = None
            if self.instance:
                instance_id = self.instance.id
            for attendance in attendance_id:
                if (
                    CompensatoryLeaveRequest.objects.filter(
                        employee_id=employee, attendance_id=attendance
                    )
                    .exclude(Q(id=instance_id) | Q(status="rejected"))
                    .exists()
                ):
                    attendance_repeat = True
                    break
            if attendance_repeat:
                raise forms.ValidationError(
                    {
                        "attendance_id": "This attendance is already converted to complimentory leave"
                    }
                )
            return cleaned_data

    class CompensatoryLeaveRequestRejectForm(forms.Form):
        """
        Form for rejecting a compensatory leave request.

        This form allows administrators to provide a rejection reason when rejecting
        a compensatory leave request.

        Attributes:
            - reason: A CharField representing the reason for rejecting the  compensatory leave request.
        """

        reason = forms.CharField(
            label=_("Rejection Reason"),
            widget=forms.Textarea(attrs={"rows": 4, "class": "p-4 oh-input w-100"}),
        )

        class Meta:
            model = CompensatoryLeaveRequest
            fields = ["reject_reason"]

    class CompensatoryLeaveRequestcommentForm(BaseModelForm):
        """
        LeaverequestComment form
        """

        class Meta:
            """
            Meta class for additional options
            """

            model = CompensatoryLeaverequestComment
            fields = ("comment",)
