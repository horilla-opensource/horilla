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
import uuid
from calendar import month_name
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.forms import DateTimeInput
from employee.models import Employee
from attendance.models import (
    Attendance,
    AttendanceOverTime,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
    AttendanceValidationCondition,
)


class ModelForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                label = _(field.label.title())
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
            "approved_overtime_second",
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


class AttendanceForm(ModelForm):
    """
    Model form for Attendance model
    """

    employee_id = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.filter(employee_work_info__isnull=False),
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
            "approved_overtime_second",
        )
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
        self.fields["shift_id"].widget.attrs.update({"id": str(uuid.uuid4())})
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
        exclude = ["hour_account_second", "overtime_second", "month_sequence"]
        labels = {
            "employee_id": _("Employee"),
            "year": _("Year"),
            "hour_account": _("Hour Account"),
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


class AttendanceValidationConditionForm(ModelForm):
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

        labels = {
            "validation_at_work": _(
                "Do not Auto Validate Attendance if an Employee \
                    Works More Than this Amount of Duration"
            ),
            "minimum_overtime_to_approve": _("Minimum Hour to Approve Overtime"),
            "overtime_cutoff": _("Maximum Allowed Overtime Per Day"),
        }
        fields = "__all__"
