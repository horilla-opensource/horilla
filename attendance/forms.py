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
import json
import uuid, datetime
from collections import OrderedDict
from typing import Any, Dict
from calendar import month_name
from django import forms
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms import DateTimeInput
from employee.models import Employee
from base.methods import reload_queryset
from base.models import Company
from attendance.models import (
    Attendance,
    AttendanceOverTime,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
    AttendanceValidationCondition,
    strtime_seconds,
)
from django.utils.html import format_html


class ModelForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                label = _(field.label.title())

                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = _(field.label)
                field.empty_label = _("---Choose {label}---").format(label=label)
                self.fields[field_name].widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 w-100",
                        "id": uuid.uuid4(),
                        "style": "height:50px;border-radius:0;",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                label = _(field.label)
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
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
            if isinstance(widget, forms.DateInput):
                field.widget = forms.DateInput(
                    attrs={"type": "date", "class": "oh-input w-100"}
                )
            if isinstance(widget, forms.TimeInput):
                field.widget = forms.DateInput(
                    attrs={"type": "time", "class": "oh-input w-100"}
                )


class AttendanceUpdateForm(ModelForm):
    """
    This model form is used to direct save the validated query dict to attendance model
    from AttendanceForm. This form can be used to update existing attendance.
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = "__all__"
        exclude = [
            "overtime_second",
            "at_work_second",
            "attendance_day",
            "request_description",
            "approved_overtime_second",
            "request_type",
            "requested_data",
            "is_validate_request",
            "is_validate_request_approved",
            "attendance_overtime",
        ]
        model = Attendance
        widgets = {
            "attendance_clock_in": DateTimeInput(attrs={"type": "time"}),
            "attendance_clock_out": DateTimeInput(attrs={"type": "time"}),
            "attendance_clock_out_date": DateTimeInput(attrs={"type": "date"}),
            "attendance_date": DateTimeInput(attrs={"type": "date"}),
            "attendance_clock_in_date": DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            condition = AttendanceValidationCondition.objects.first()
            condition = (
                strtime_seconds(condition.minimum_overtime_to_approve)
                if condition and condition.minimum_overtime_to_approve
                else 0
            )
            initial = {
                "attendance_date": instance.attendance_date.strftime("%Y-%m-%d"),
                "attendance_clock_in": instance.attendance_clock_in.strftime("%H:%M"),
                "attendance_clock_in_date": instance.attendance_clock_in_date.strftime(
                    "%Y-%m-%d"
                ),
            }
            if instance.attendance_clock_out_date is not None:
                initial[
                    "attendance_clock_out"
                ] = instance.attendance_clock_out.strftime("%H:%M")
                initial[
                    "attendance_clock_out_date"
                ] = instance.attendance_clock_out_date.strftime("%Y-%m-%d")
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

        self.fields["attendance_overtime_approve"].label = _("Approve overtime?")
        self.fields["attendance_validated"].label = _("Validate Attendance?")
        if (
            strtime_seconds(instance.attendance_overtime) < condition
            or not instance.attendance_validated
        ):
            del self.fields["attendance_overtime_approve"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html


class AttendanceForm(ModelForm):
    """
    Model form for Attendance model
    """

    employee_id = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.filter(employee_work_info__isnull=False),
        label=_("Employees"),
    )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Attendance
        fields = "__all__"
        exclude = (
            "attendance_overtime_approve",
            "attendance_overtime_calculation",
            "at_work_second",
            "overtime_second",
            "attendance_day",
            "request_description",
            "approved_overtime_second",
            "request_type",
            "requested_data",
            "is_validate_request",
            "is_validate_request_approved",
            "attendance_overtime",
        )
        widgets = {
            "attendance_clock_in": DateTimeInput(attrs={"type": "time"}),
            "attendance_clock_out": DateTimeInput(attrs={"type": "time"}),
            "attendance_clock_out_date": DateTimeInput(attrs={"type": "date"}),
            "attendance_date": DateTimeInput(attrs={"type": "date"}),
            "attendance_clock_in_date": DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        initial = {
            "attendance_clock_out_date": datetime.datetime.today()
            .date()
            .strftime("%Y-%m-%d"),
            "attendance_clock_out": datetime.datetime.today().time().strftime("%H:%M"),
        }
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            initial = {
                "attendance_date": instance.attendance_date.strftime("%Y-%m-%d"),
                "attendance_clock_in": instance.attendance_clock_in.strftime("%H:%M"),
                "attendance_clock_in_date": instance.attendance_clock_in_date.strftime(
                    "%Y-%m-%d"
                ),
            }
            if instance.attendance_clock_out_date is not None:
                initial[
                    "attendance_clock_out"
                ] = instance.attendance_clock_out.strftime("%H:%M")
                initial[
                    "attendance_clock_out_date"
                ] = instance.attendance_clock_out_date.strftime("%Y-%m-%d")
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].widget.attrs.update({"id": str(uuid.uuid4())})
        self.fields["shift_id"].widget.attrs.update(
            {
                "id": str(uuid.uuid4()),
                "onchange": "shiftChange($(this))",
            }
        )
        self.fields["work_type_id"].widget.attrs.update({"id": str(uuid.uuid4())})

    def save(self, commit=True):
        instance = super().save(commit=False)
        for emp_id in self.data.getlist("employee_id"):
            if int(emp_id) != int(instance.employee_id.id):
                data_copy = self.data.copy()
                data_copy.update({"employee_id": str(emp_id)})
                attendance = AttendanceUpdateForm(data_copy).save(commit=False)
                attendance.save()
        if commit:
            instance.save()
        return instance

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def clean(self) -> Dict[str, Any]:
        super().clean()
        minimum_hour = strtime_seconds(self.cleaned_data["minimum_hour"])
        at_work = strtime_seconds(self.cleaned_data["attendance_worked_hour"])
        return

    def clean_employee_id(self):
        """
        Used to validate employee_id field
        """
        employee = self.cleaned_data["employee_id"]
        for emp in employee:
            attendance = Attendance.objects.filter(
                employee_id=emp, attendance_date=self.data["attendance_date"]
            ).first()
            if attendance is not None:
                raise ValidationError(
                    _(
                        "Attendance for the date is already exist for %(emp)s"
                        % {"emp": emp}
                    )
                )
        if employee.first() is None:
            raise ValidationError(_("Employee not chosen"))

        return employee.first()


class AttendanceActivityForm(ModelForm):
    """
    Model form for AttendanceActivity model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = AttendanceActivity
        fields = "__all__"
        widgets = {
            "clock_in": DateTimeInput(attrs={"type": "time"}),
            "clock_out": DateTimeInput(attrs={"type": "time"}),
            "clock_in_date": DateTimeInput(attrs={"type": "date"}),
            "clock_out_date": DateTimeInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value

            initial = {
                "attendance_date": instance.attendance_date.strftime("%Y-%m-%d"),
                "clock_in_date": instance.clock_in_date.strftime("%Y-%m-%d"),
                "clock_in": instance.clock_in.strftime("%H:%M"),
            }
            if instance.clock_out is not None:
                initial["clock_out"] = instance.clock_out.strftime("%H:%M")
                initial["clock_out_date"] = instance.clock_out_date.strftime("%Y-%m-%d")
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)


class MonthSelectField(forms.ChoiceField):
    """
    Generate month choices
    """

    def __init__(self, *args, **kwargs):
        choices = [
            (month_name[i].lower(), _(month_name[i].capitalize())) for i in range(1, 13)
        ]
        super().__init__(choices=choices, *args, **kwargs)


class AttendanceOverTimeForm(ModelForm):
    """
    Model form for AttendanceOverTime model
    """

    month = MonthSelectField(label=_("Month"))

    class Meta:
        """
        Meta class to add the additional info
        """

        model = AttendanceOverTime
        fields = "__all__"
        exclude = [
            "hour_account_second",
            "overtime_second",
            "month_sequence",
            "hour_pending_second",
        ]
        labels = {
            "employee_id": _("Employee"),
            "year": _("Year"),
            "worked_hours": _("Worked Hours"),
            "pending_hours": _("Pending Hours"),
            "overtime": _("Overtime"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"].widget.attrs.update({"id": str(uuid.uuid4())})


class AttendanceLateComeEarlyOutForm(ModelForm):
    """
    Model form for attendance AttendanceLateComeEarlyOut
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = AttendanceLateComeEarlyOut
        fields = "__all__"


class AttendanceValidationConditionForm(forms.ModelForm):
    """
    Model form for AttendanceValidationCondition
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = AttendanceValidationCondition
        validation_at_work = forms.DurationField()
        approve_overtime_after = forms.DurationField()
        overtime_cutoff = forms.DurationField()
        company_id = forms.ModelMultipleChoiceField(
            queryset=Company.objects.all(),
            widget=forms.SelectMultiple(attrs={"class": "oh-select oh-select-2 w-100"}),
        )
        widgets = {
            "validation_at_work": forms.TextInput(
                attrs={"class": "oh-input w-100", "placeholder": "09:00"}
            ),
            "minimum_overtime_to_approve": forms.TextInput(
                attrs={"class": "oh-input w-100", "placeholder": "00:30"}
            ),
            "overtime_cutoff": forms.TextInput(
                attrs={"class": "oh-input w-100", "placeholder": "02:00"}
            ),
            "company_id": forms.SelectMultiple(attrs={"class": "oh-select w-100"}),
        }

        labels = {
            "validation_at_work": format_html(
                _(
                    "<span title='Do not Auto Validate Attendance if an Employee Works More Than this Amount of Duration'>{}</span>"
                ),
                _("Maximum Allowed working hours"),
            ),
            "minimum_overtime_to_approve": _("Minimum Hour to Approve Overtime"),
            "overtime_cutoff": _("Maximum Allowed Overtime Per Day"),
        }
        fields = "__all__"


class AttendanceRequestForm(ModelForm):
    """
    AttendanceRequestForm
    """

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            initial = {
                "attendance_date": instance.attendance_date.strftime("%Y-%m-%d"),
                "attendance_clock_in": instance.attendance_clock_in.strftime("%H:%M"),
                "attendance_clock_in_date": instance.attendance_clock_in_date.strftime(
                    "%Y-%m-%d"
                ),
            }
            if instance.attendance_clock_out_date is not None:
                initial[
                    "attendance_clock_out"
                ] = instance.attendance_clock_out.strftime("%H:%M")
                initial[
                    "attendance_clock_out_date"
                ] = instance.attendance_clock_out_date.strftime("%Y-%m-%d")
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["attendance_clock_out_date"].required = False
        self.fields["attendance_clock_out"].required = False

    class Meta:
        """
        Meta class for additional options
        """

        model = Attendance
        fields = [
            "attendance_date",
            "shift_id",
            "work_type_id",
            "attendance_clock_in_date",
            "attendance_clock_in",
            "attendance_clock_out_date",
            "attendance_clock_out",
            "attendance_worked_hour",
            "minimum_hour",
            "request_description",
        ]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def save(self, commit: bool = ...) -> Any:
        # No need to save the changes to the actual modal instance
        return super().save(False)


class NewRequestForm(AttendanceRequestForm):
    """
    NewRequestForm class
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add the new model choice field to the form at the beginning
        old_dict = self.fields
        new_dict = {
            "employee_id": forms.ModelChoiceField(
                queryset=Employee.objects.all(),
                label=_("Employee"),
                widget=forms.Select(attrs={"class": "oh-select oh-select-2 w-100"}),
            ),
        }
        self.fields["request_description"].label = _("Request description")
        new_dict.update(old_dict)
        self.fields = new_dict

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        form_html = render_to_string(
            "requests/attendance/request_new_form.html", context
        )
        return form_html

    def clean(self) -> Dict[str, Any]:
        super().clean()

        employee = self.cleaned_data["employee_id"]
        attendance_date = self.cleaned_data["attendance_date"]
        attendances = Attendance.objects.filter(
            employee_id=employee, attendance_date=attendance_date
        )
        data = {
            "employee_id": employee,
            "attendance_date": attendance_date,
            "attendance_clock_in_date": self.cleaned_data["attendance_clock_in_date"],
            "attendance_clock_in": self.cleaned_data["attendance_clock_in"],
            "attendance_clock_out": self.cleaned_data["attendance_clock_out"],
            "attendance_clock_out_date": self.cleaned_data["attendance_clock_out_date"],
            "shift_id": self.cleaned_data["shift_id"],
            "work_type_id": self.cleaned_data["work_type_id"],
            "attendance_worked_hour": self.cleaned_data["attendance_worked_hour"],
            "minimum_hour": self.data["minimum_hour"],
        }
        if attendances.exists():
            data["employee_id"] = employee.id
            data["attendance_date"] = str(attendance_date)
            data["attendance_clock_in_date"] = self.data["attendance_clock_in_date"]
            data["attendance_clock_in"] = self.data["attendance_clock_in"]
            data["attendance_clock_out"] = (
                None
                if data["attendance_clock_out"] == "None"
                else data["attendance_clock_out"]
            )
            data["attendance_clock_out_date"] = (
                None
                if data["attendance_clock_out_date"] == "None"
                else data["attendance_clock_out_date"]
            )
            data["work_type_id"] = self.data["work_type_id"]
            data["shift_id"] = self.data["shift_id"]
            attendance = attendances.first()
            attendance.requested_data = json.dumps(data)
            attendance.is_validate_request = True
            if attendance.request_type != "create_request":
                attendance.request_type = "update_request"
            attendance.request_description = self.data["request_description"]
            attendance.save()
            self.new_instance = None
            return

        new_instance = Attendance(**data)
        new_instance.is_validate_request = True
        new_instance.attendance_validated = False
        new_instance.request_description = self.data["request_description"]
        new_instance.request_type = "create_request"
        self.new_instance = new_instance
        return


excluded_fields = [
    "id",
    "attendance_id__employee_id",
    "requested_data",
    "at_work_second",
    "approved_overtime_second",
    "is_validate_request",
    "is_validate_request_approved",
    "request_description",
    "request_type",
    "month_sequence",
    "objects",
]


class AttendanceExportForm(forms.Form):
    model_fields = Attendance._meta.get_fields()
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
            "shift_id",
            "work_type_id",
            "attendance_date",
            "attendance_clock_in",
            "attendance_clock_in_date",
            "attendance_clock_out",
            "attendance_clock_out_date",
            "attendance_worked_hour",
            "attendance_validated",
        ],
    )


class LateComeEarlyOutExportForm(forms.Form):
    model_fields = AttendanceLateComeEarlyOut._meta.get_fields()
    field_choices_1 = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    model_fields_2 = Attendance._meta.get_fields()
    field_choices_2 = [
        ("attendance_id__" + field.name, field.verbose_name)
        for field in model_fields_2
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    field_choices = field_choices_1 + field_choices_2
    field_choices = list(OrderedDict.fromkeys(field_choices))
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "type",
            "attendance_id__attendance_date",
            "attendance_id__attendance_clock_in_date",
            "attendance_id__attendance_clock_in",
            "attendance_id__attendance_clock_out_date",
            "attendance_id__attendance_clock_out",
        ],
    )


class AttendanceActivityExportForm(forms.Form):
    model_fields = AttendanceActivity._meta.get_fields()
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
            "attendance_date",
            "clock_in_date",
            "clock_in",
            "clock_out_date",
            "clock_out",
        ],
    )


class AttendanceOverTimeExportForm(forms.Form):
    model_fields = AttendanceOverTime._meta.get_fields()
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
            "month",
            "year",
            "worked_hours",
            "pending_hours",
            "overtime",
        ],
    )
