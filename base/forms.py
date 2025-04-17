"""
forms.py

This module is used to register forms for base module
"""

import calendar
import datetime
import ipaddress
import os
import uuid
from datetime import date, timedelta
from typing import Any

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, _unicode_ci_compare
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_ipv46_address
from django.forms import DateInput, HiddenInput, TextInput
from django.template import loader
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _trans

from base.methods import reload_queryset
from base.models import (
    Announcement,
    AnnouncementComment,
    AnnouncementExpire,
    Attachment,
    AttendanceAllowedIP,
    BaserequestFile,
    Company,
    CompanyLeaves,
    Department,
    DriverViewed,
    DynamicEmailConfiguration,
    DynamicPagination,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeShiftSchedule,
    EmployeeType,
    Holidays,
    HorillaMailTemplate,
    JobPosition,
    JobRole,
    MultipleApprovalCondition,
    PenaltyAccounts,
    RotatingShift,
    RotatingShiftAssign,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    ShiftRequest,
    ShiftRequestComment,
    Tags,
    TrackLateComeEarlyOut,
    WorkType,
    WorkTypeRequest,
    WorkTypeRequestComment,
)
from employee.filters import EmployeeFilter
from employee.forms import MultipleFileField
from employee.models import Employee
from horilla import horilla_middlewares
from horilla.horilla_middlewares import _thread_locals
from horilla.methods import get_horilla_model_class
from horilla_audit.models import AuditTag
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget

# your form here


def validate_time_format(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 6:
        raise ValidationError(_("Invalid format, it should be HH:MM format"))
    try:
        hour, minute = value.split(":")
        hour = int(hour)
        minute = int(minute)
        if len(str(hour)) > 3 or minute not in range(60):
            raise ValidationError(_("Invalid format, it should be HH:MM format"))
    except ValueError as error:
        raise ValidationError(_("Invalid format, it should be HH:MM format")) from error


BASED_ON = [
    ("after", _trans("After")),
    ("weekly", _trans("Weekend")),
    ("monthly", _trans("Monthly")),
]


def get_next_week_date(target_day, start_date):
    """
    Calculates the date of the next occurrence of the target day within the next week.

    Parameters:
        target_day (int): The target day of the week (0-6, where Monday is 0 and Sunday is 6).
        start_date (datetime.date): The starting date.

    Returns:
        datetime.date: The date of the next occurrence of the target day within the next week.
    """
    if start_date.weekday() == target_day:
        return start_date
    days_until_target_day = (target_day - start_date.weekday()) % 7
    if days_until_target_day == 0:
        days_until_target_day = 7
    return start_date + timedelta(days=days_until_target_day)


def get_next_monthly_date(start_date, rotate_every):
    """
    Given a start date and a rotation day (specified as an integer between 1 and 31, or
    the string 'last'),calculates the next rotation date for a monthly rotation schedule.

    If the rotation day has not yet occurred in the current month, the next rotation date
    will be on the rotation day of the current month. If the rotation day has already
    occurred in the current month, the next rotation date will be on the rotation day of
    the next month.

    If 'last' is specified as the rotation day, the next rotation date will be on the
    last day of the current month.

    Parameters:
    - start_date: The start date of the rotation schedule, as a datetime.date object.
    - rotate_every: The rotation day, specified as an integer between 1 and 31, or the
      string 'last'.

    Returns:
    - A datetime.date object representing the next rotation date.
    """

    if rotate_every == "last":
        # Set rotate_every to the last day of the current month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        rotate_every = str(last_day)
    rotate_every = int(rotate_every)

    # Calculate the next change date
    if start_date.day <= rotate_every or rotate_every == 0:
        # If the rotation day has not occurred yet this month, or if it's the last-
        # day of the month, set the next change date to the rotation day of this month
        try:
            next_change = datetime.date(start_date.year, start_date.month, rotate_every)
        except ValueError:
            next_change = datetime.date(
                start_date.year, start_date.month + 1, 1
            )  # Advance to next month
            # Set day to rotate_every
            next_change = datetime.date(
                next_change.year, next_change.month, rotate_every
            )
    else:
        # If the rotation day has already occurred this month, set the next change
        # date to the rotation day of the next month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        next_month_start = start_date.replace(day=last_day) + timedelta(days=1)
        try:
            next_change = next_month_start.replace(day=rotate_every)
        except ValueError:
            next_change = (
                next_month_start.replace(month=next_month_start.month + 1)
                + timedelta(days=1)
            ).replace(day=rotate_every)

    return next_change


class ModelForm(forms.ModelForm):
    """
    Override django model's form to add initial styling
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.DateInput)):
                field.initial = date.today()

            if isinstance(
                widget,
                (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput),
            ):
                label = ""
                if field.label is not None:
                    label = _(field.label.title())
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.empty_label = None
                if not isinstance(field, forms.ModelMultipleChoiceField):
                    label = ""
                    if field.label is not None:
                        label = _(field.label)
                    field.empty_label = _("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": _(field.label),
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
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


class Form(forms.Form):
    """
    Overrides to add initial styling to the django Form instance
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                if field.label is not None:
                    label = _(field.label)
                    field.widget.attrs.update(
                        {"class": "oh-input w-100", "placeholder": label}
                    )
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = field.label.replace("id", " ")
                field.empty_label = _("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
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


class UserGroupForm(ModelForm):
    """
    Django user groups form
    """

    try:
        permissions = forms.MultipleChoiceField(
            choices=[(perm.codename, perm.name) for perm in Permission.objects.all()],
            required=False,
            error_messages={
                "required": "Please choose a permission.",
            },
        )
    except:
        pass

    class Meta:
        """
        Meta class for additional options
        """

        model = Group
        fields = ["name", "permissions"]

    def save(self, commit=True):
        """
        ModelForm save override
        """
        group = super().save(commit=False)
        if self.instance:
            group = self.instance
        group.save()

        # Convert the selected codenames back to Permission instances
        permissions_codenames = self.cleaned_data["permissions"]
        permissions = Permission.objects.filter(codename__in=permissions_codenames)

        # Set the associated permissions
        group.permissions.set(permissions)

        if commit:
            group.save()

        return group


class AssignUserGroup(Form):
    """
    Form to assign groups
    """

    employee = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(), required=False
    )
    group = forms.ModelChoiceField(queryset=Group.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)

    def save(self):
        """
        Save method to assign group to employees
        """
        employees = self.cleaned_data["employee"]
        group = self.cleaned_data["group"]
        group.user_set.clear()
        for employee in employees:
            employee.employee_user_id.groups.add(group)
        return group


class AssignPermission(Form):
    """
    Forms to assign user permision
    """

    employee = HorillaMultiSelectField(
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
    try:
        permissions = forms.MultipleChoiceField(
            choices=[(perm.codename, perm.name) for perm in Permission.objects.all()],
            error_messages={
                "required": "Please choose a permission.",
            },
        )
    except:
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)

    def clean(self):
        emps = self.data.getlist("employee")
        if emps:
            self.errors.pop("employee", None)
        super().clean()
        return

    def save(self):
        """
        Save method to assign permission to employee
        """
        user_ids = Employee.objects.filter(
            id__in=self.data.getlist("employee")
        ).values_list("employee_user_id", flat=True)
        permissions = self.cleaned_data["permissions"]
        permissions = Permission.objects.filter(codename__in=permissions)
        users = User.objects.filter(id__in=user_ids)
        for user in users:
            user.user_permissions.set(permissions)

        return self


class CompanyForm(ModelForm):
    """
    Company model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Company
        fields = "__all__"
        excluded_fields = ["date_format", "time_format", "is_active"]

    def validate_image(self, file):
        max_size = 5 * 1024 * 1024

        if file.size > max_size:
            raise ValidationError("File size should be less than 5MB.")

        # Check file extension
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp", ".svg"]
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in valid_extensions:
            raise ValidationError("Unsupported file extension.")

    def clean_icon(self):
        icon = self.cleaned_data.get("icon")
        if icon:
            self.validate_image(icon)
        return icon


class DepartmentForm(ModelForm):
    """
    Department model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Department
        fields = "__all__"
        exclude = ["is_active"]


class JobPositionForm(ModelForm):
    """
    JobPosition model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = JobPosition
        fields = "__all__"
        exclude = ["is_active"]


class JobPositionMultiForm(ModelForm):
    """
    JobPosition model's form
    """

    department_id = HorillaMultiSelectField(queryset=Department.objects.all())

    class Meta:
        model = JobPosition
        fields = "__all__"
        exclude = ["department_id", "is_active"]
        widgets = {
            "department_id": forms.SelectMultiple(
                attrs={
                    "class": "oh-select oh-select2 w-100",
                    "style": "height:45px;",
                }
            ),
        }

    def clean(self):
        """
        Validate that the job position does not already exist in the selected departments.
        """
        cleaned_data = super().clean()
        department_ids = self.data.getlist("department_id")
        job_position = self.data.get("job_position")

        existing_positions = JobPosition.objects.filter(
            department_id__in=department_ids, job_position=job_position
        )

        if existing_positions.exists():
            existing_deps = existing_positions.values_list("department_id", flat=True)
            dep_names = Department.objects.filter(id__in=existing_deps).values_list(
                "department", flat=True
            )
            raise ValidationError(
                {
                    "department_id": _("Job position already exists under {}").format(
                        ", ".join(dep_names)
                    )
                }
            )
        return cleaned_data

    def save(self, *args, **kwargs):
        """
        Save the job positions for each selected department.
        """
        if not self.instance.pk:
            request = getattr(_thread_locals, "request")
            department_ids = self.data.getlist("department_id")
            job_position = self.data.get("job_position")
            positions = []

            for dep_id in department_ids:
                dep = Department.objects.get(id=dep_id)
                if JobPosition.objects.filter(
                    department_id=dep, job_position=job_position
                ).exists():
                    messages.error(request, f"Job position already exists under {dep}")
                else:
                    position = JobPosition(department_id=dep, job_position=job_position)
                    position.save()
                    positions.append(position.pk)

            return JobPosition.objects.filter(id__in=positions)
        return super().save(*args, **kwargs)


class JobRoleForm(ModelForm):
    """
    JobRole model's form
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["job_position_id"] = forms.ModelMultipleChoiceField(
                queryset=self.fields["job_position_id"].queryset
            )
            attrs = self.fields["job_position_id"].widget.attrs
            attrs["class"] = "oh-select oh-select2 w-100"
            attrs["style"] = "height:45px;"

    class Meta:
        """
        Meta class for additional options
        """

        model = JobRole
        fields = "__all__"
        exclude = ["is_active"]

    def save(self, commit, *args, **kwargs) -> Any:
        if not self.instance.pk:
            request = getattr(_thread_locals, "request")
            job_positions = JobPosition.objects.filter(
                id__in=self.data.getlist("job_position_id")
            )
            roles = []
            for position in job_positions:
                role = JobRole()
                role.job_position_id = position
                role.job_role = self.data["job_role"]
                try:
                    role.save()
                except:
                    messages.info(request, f"Role already exists under {position}")
                roles.append(role.pk)
            return JobRole.objects.filter(id__in=roles)
        super().save(commit, *args, **kwargs)


class WorkTypeForm(ModelForm):
    """
    WorkType model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = WorkType
        fields = "__all__"
        exclude = ["is_active"]


class RotatingWorkTypeForm(ModelForm):
    """
    RotatingWorkType model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingWorkType
        fields = "__all__"
        exclude = ["employee_id", "is_active"]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
            "additional_data": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        work_type_counts = 0

        def create_work_type_field(work_type_key, required, initial=None):
            self.fields[work_type_key] = forms.ModelChoiceField(
                queryset=WorkType.objects.all(),
                widget=forms.Select(
                    attrs={
                        "class": "oh-select oh-select-2 mb-3",
                        "name": work_type_key,
                        "id": f"id_{work_type_key}",
                    }
                ),
                required=required,
                empty_label=_("---Choose Work Type---"),
                initial=initial,
            )

        for key in self.data.keys():
            if key.startswith("work_type"):
                work_type_counts += 1
                create_work_type_field(key, work_type_counts <= 2)

        additional_data = self.initial.get("additional_data")
        additional_work_types = (
            additional_data.get("additional_work_types") if additional_data else None
        )
        if additional_work_types:
            work_type_counts = 3
            for work_type_id in additional_work_types:
                create_work_type_field(
                    f"work_type{work_type_counts}",
                    work_type_counts <= 2,
                    initial=work_type_id,
                )
                work_type_counts += 1

        self.work_type_counts = work_type_counts

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string(
            "base/rotating_work_type/htmx/rotating_work_type_as_p.html", context
        )

    def clean(self):
        cleaned_data = super().clean()
        additional_work_types = []
        model_fields = list(self.instance.__dict__.keys())

        for key, value in self.data.items():
            if (
                f"{key}_id" not in model_fields
                and key.startswith("work_type")
                and value
            ):
                additional_work_types.append(value)

        if additional_work_types:
            if (
                "additional_data" not in cleaned_data
                or cleaned_data["additional_data"] is None
            ):
                cleaned_data["additional_data"] = {}
            cleaned_data["additional_data"][
                "additional_work_types"
            ] = additional_work_types

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("additional_data"):
            if instance.additional_data is None:
                instance.additional_data = {}
            instance.additional_data["additional_work_types"] = self.cleaned_data[
                "additional_data"
            ].get("additional_work_types")
        else:
            instance.additional_data = None

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class RotatingWorkTypeAssignForm(ModelForm):
    """
    RotatingWorkTypeAssign model's form
    """

    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.filter(employee_work_info__isnull=False),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
        ),
        label=_trans("Employees"),
    )
    based_on = forms.ChoiceField(
        choices=BASED_ON, initial="daily", label=_trans("Based on")
    )
    rotate_after_day = forms.IntegerField(initial=5, label=_trans("Rotate after day"))
    start_date = forms.DateField(
        initial=datetime.date.today, widget=forms.DateInput, label=_trans("Start date")
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingWorkTypeAssign
        fields = "__all__"
        exclude = [
            "next_change_date",
            "current_work_type",
            "next_work_type",
            "is_active",
            "additional_data",
        ]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
            "is_active": HiddenInput(),
        }
        labels = {
            "is_active": _trans("Is Active"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            if field.required:
                self.fields[field_name].label_suffix = " *"

        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_work_type_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def clean_employee_id(self):
        employee_ids = self.cleaned_data.get("employee_id")
        if employee_ids:
            return employee_ids[0]
        else:
            return ValidationError(_("This field is required"))

    def clean(self):
        super().clean()
        self.instance.employee_id = Employee.objects.filter(
            id=self.data.get("employee_id")
        ).first()

        self.errors.pop("employee_id", None)
        if self.instance.employee_id is None:
            raise ValidationError({"employee_id": _("This field is required")})
        super().clean()
        cleaned_data = super().clean()
        if "rotate_after_day" in self.errors:
            del self.errors["rotate_after_day"]
        return cleaned_data

    def save(self, commit=False, manager=None):
        employee_ids = self.data.getlist("employee_id")
        rotating_work_type = RotatingWorkType.objects.get(
            id=self.data["rotating_work_type_id"]
        )

        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())

        for employee_id in employee_ids:
            employee = Employee.objects.filter(id=employee_id).first()
            rotating_work_type_assign = RotatingWorkTypeAssign()
            rotating_work_type_assign.rotating_work_type_id = rotating_work_type
            rotating_work_type_assign.employee_id = employee
            rotating_work_type_assign.based_on = self.cleaned_data["based_on"]
            rotating_work_type_assign.start_date = self.cleaned_data["start_date"]
            rotating_work_type_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_work_type_assign.rotate_after_day = self.data.get(
                "rotate_after_day"
            )
            rotating_work_type_assign.rotate_every = self.cleaned_data["rotate_every"]
            rotating_work_type_assign.rotate_every_weekend = self.cleaned_data[
                "rotate_every_weekend"
            ]
            rotating_work_type_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_work_type_assign.current_work_type = (
                employee.employee_work_info.work_type_id
            )
            rotating_work_type_assign.next_work_type = rotating_work_type.work_type1
            rotating_work_type_assign.additional_data["next_shift_index"] = 1
            based_on = self.cleaned_data["based_on"]
            start_date = self.cleaned_data["start_date"]
            if based_on == "weekly":
                next_date = get_next_week_date(target_day, start_date)
                rotating_work_type_assign.next_change_date = next_date
            elif based_on == "monthly":
                # 0, 1, 2, ..., 31, or "last"
                rotate_every = self.cleaned_data["rotate_every"]
                start_date = self.cleaned_data["start_date"]
                next_date = get_next_monthly_date(start_date, rotate_every)
                rotating_work_type_assign.next_change_date = next_date
            elif based_on == "after":
                rotating_work_type_assign.next_change_date = (
                    rotating_work_type_assign.start_date
                    + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
                )

            rotating_work_type_assign.save()


class RotatingWorkTypeAssignUpdateForm(forms.ModelForm):
    """
    RotatingWorkTypeAssign model's form
    """

    based_on = forms.ChoiceField(
        choices=BASED_ON, initial="daily", label=_trans("Based on")
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingWorkTypeAssign
        fields = "__all__"
        exclude = [
            "next_change_date",
            "current_work_type",
            "next_work_type",
            "is_active",
            "additional_data",
        ]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "start_date": _trans("Start date"),
            "rotate_after_day": _trans("Rotate after day"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
            "based_on": _trans("Based on"),
            "is_active": _trans("Is Active"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            if field.required:
                self.fields[field_name].label_suffix = " *"

        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px\
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0; border:1px solid \
                    hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_work_type_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def save(self, *args, **kwargs):
        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())

        based_on = self.cleaned_data["based_on"]
        start_date = self.instance.start_date
        if based_on == "weekly":
            next_date = get_next_week_date(target_day, start_date)
            self.instance.next_change_date = next_date
        elif based_on == "monthly":
            rotate_every = self.instance.rotate_every  # 0, 1, 2, ..., 31, or "last"
            start_date = self.instance.start_date
            next_date = get_next_monthly_date(start_date, rotate_every)
            self.instance.next_change_date = next_date
        elif based_on == "after":
            self.instance.next_change_date = (
                self.instance.start_date
                + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
            )
        return super().save()


class EmployeeTypeForm(ModelForm):
    """
    EmployeeType form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeType
        fields = "__all__"
        exclude = ["is_active"]


class EmployeeShiftForm(ModelForm):
    """
    EmployeeShift Form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeShift
        fields = "__all__"
        exclude = ["days", "is_active"]

    def clean(self):
        full_time = self.data["full_time"]
        validate_time_format(full_time)
        full_time = self.data["weekly_full_time"]
        validate_time_format(full_time)
        return super().clean()


class EmployeeShiftScheduleUpdateForm(ModelForm):
    """
    EmployeeShiftSchedule model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeShiftSchedule
        fields = "__all__"
        exclude = ["is_active", "is_night_shift"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")

        if instance:
            self.fields["start_time"].initial = (
                instance.start_time.strftime("%H:%M") if instance.start_time else None
            )
            self.fields["end_time"].initial = (
                instance.end_time.strftime("%H:%M") if instance.end_time else None
            )
            if apps.is_installed("attendance"):
                self.fields["auto_punch_out_time"].initial = (
                    instance.auto_punch_out_time.strftime("%H:%M")
                    if instance.auto_punch_out_time
                    else None
                )

        if not apps.is_installed("attendance"):
            self.fields.pop("auto_punch_out_time", None)
            self.fields.pop("is_auto_punch_out_enabled", None)
        else:
            self.fields["auto_punch_out_time"].widget = forms.TimeInput(
                attrs={"type": "time", "class": "oh-input w-100 form-control"}
            )
            self.fields["is_auto_punch_out_enabled"].widget.attrs.update(
                {"onchange": "toggleDivVisibility(this)"}
            )

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """

        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        if apps.is_installed("attendance"):
            auto_punch_out_enabled = cleaned_data.get("is_auto_punch_out_enabled")
            auto_punch_out_time = cleaned_data.get("auto_punch_out_time")
            end_time = cleaned_data.get("end_time")

            if auto_punch_out_enabled:
                if not auto_punch_out_time:
                    raise ValidationError(
                        {
                            "auto_punch_out_time": _(
                                "Automatic punch out time is required when automatic punch out is enabled."
                            )
                        }
                    )
                elif auto_punch_out_time < end_time:
                    raise ValidationError(
                        {
                            "auto_punch_out_time": _(
                                "Automatic punch out time cannot be earlier than the end time."
                            )
                        }
                    )

        return cleaned_data


class EmployeeShiftScheduleForm(ModelForm):
    """
    EmployeeShiftSchedule model's form
    """

    day = forms.ModelMultipleChoiceField(
        queryset=EmployeeShiftDay.objects.all(),
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeShiftSchedule
        fields = "__all__"
        exclude = ["is_night_shift", "is_active"]
        widgets = {
            "start_time": DateInput(attrs={"type": "time"}),
            "end_time": DateInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # """
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            # """
            initial = {
                "start_time": instance.start_time.strftime("%H:%M"),
                "end_time": instance.end_time.strftime("%H:%M"),
            }
            if apps.is_installed("attendance"):
                initial["auto_punch_out_time"] = (
                    instance.auto_punch_out_time.strftime("%H:%M")
                    if instance.auto_punch_out_time
                    else None
                )
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["day"].widget.attrs.update({"id": str(uuid.uuid4())})
        self.fields["shift_id"].widget.attrs.update({"id": str(uuid.uuid4())})
        if not apps.is_installed("attendance"):
            self.fields.pop("auto_punch_out_time", None)
            self.fields.pop("is_auto_punch_out_enabled", None)
        else:
            self.fields["auto_punch_out_time"].widget = forms.TimeInput(
                attrs={"type": "time", "class": "oh-input w-100 form-control"}
            )
            self.fields["is_auto_punch_out_enabled"].widget.attrs.update(
                {"onchange": "toggleDivVisibility(this)"}
            )

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """

        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        if apps.is_installed("attendance"):
            auto_punch_out_enabled = self.cleaned_data["is_auto_punch_out_enabled"]
            auto_punch_out_time = self.cleaned_data["auto_punch_out_time"]
            end_time = self.cleaned_data["end_time"]
            if auto_punch_out_enabled:
                if not auto_punch_out_time:
                    raise ValidationError(
                        {
                            "auto_punch_out_time": _(
                                "Automatic punch out time is required when automatic punch out is enabled."
                            )
                        }
                    )
            if auto_punch_out_enabled and auto_punch_out_time and end_time:
                if auto_punch_out_time < end_time:
                    raise ValidationError(
                        {
                            "auto_punch_out_time": _(
                                "Automatic punch out time cannot be earlier than the end time."
                            )
                        }
                    )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        for day in self.data.getlist("day"):
            if int(day) != int(instance.day.id):
                data_copy = self.data.copy()
                data_copy.update({"day": str(day)})
                shift_schedule = EmployeeShiftScheduleUpdateForm(data_copy).save(
                    commit=False
                )
                shift_schedule.save()
        if commit:
            instance.save()
        return instance

    def clean_day(self):
        """
        Validation to day field
        """
        days = self.cleaned_data["day"]
        for day in days:
            attendance = EmployeeShiftSchedule.objects.filter(
                day=day, shift_id=self.data["shift_id"]
            ).first()
            if attendance is not None:
                raise ValidationError(
                    _("Shift schedule is already exist for {day}").format(
                        day=_(day.day)
                    )
                )
        if days.first() is None:
            raise ValidationError(_("Employee not chosen"))

        return days.first()


class RotatingShiftForm(ModelForm):
    """
    RotatingShift model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingShift
        fields = "__all__"
        exclude = ["employee_id", "is_active"]
        widgets = {"additional_data": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        shift_counts = 0

        def create_shift_field(shift_key, required, initial=None):
            self.fields[shift_key] = forms.ModelChoiceField(
                queryset=EmployeeShift.objects.all(),
                widget=forms.Select(
                    attrs={
                        "class": "oh-select oh-select-2 mb-3",
                        "name": shift_key,
                        "id": f"id_{shift_key}",
                    }
                ),
                required=required,
                empty_label=_("---Choose Shift---"),
                initial=initial,
            )

        for field in self.fields:
            if field.startswith("shift"):
                shift_counts += 1
                create_shift_field(field, shift_counts <= 2)

        for key in self.data.keys():
            if key.startswith("shift") and self.data[key]:
                shift_counts += 1
                create_shift_field(key, shift_counts <= 2)

        additional_data = self.initial.get("additional_data")
        additional_shifts = (
            additional_data.get("additional_shifts") if additional_data else None
        )
        if additional_shifts:
            shift_counts = 3
            for shift_id in additional_shifts:
                if shift_id:
                    create_shift_field(
                        f"shift{shift_counts}", shift_counts <= 2, initial=shift_id
                    )
                    shift_counts += 1

        self.shift_counts = shift_counts

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string(
            "base/rotating_shift/htmx/rotating_shift_as_p.html", context
        )

    def clean(self):
        cleaned_data = super().clean()
        additional_shifts = []
        model_fields = list(self.instance.__dict__.keys())

        for key, value in self.data.items():
            if f"{key}_id" not in model_fields and key.startswith("shift") and value:
                additional_shifts.append(value)

        if additional_shifts:
            if (
                "additional_data" not in cleaned_data
                or cleaned_data["additional_data"] is None
            ):
                cleaned_data["additional_data"] = {}
            cleaned_data["additional_data"]["additional_shifts"] = additional_shifts

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("additional_data"):
            if instance.additional_data is None:
                instance.additional_data = {}
            instance.additional_data["additional_shifts"] = self.cleaned_data[
                "additional_data"
            ].get("additional_shifts")
        else:
            instance.additional_data = None

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class RotatingShiftAssignForm(forms.ModelForm):
    """
    RotatingShiftAssign model's form
    """

    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.filter(employee_work_info__isnull=False),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
        ),
        label=_trans("Employees"),
    )
    based_on = forms.ChoiceField(
        choices=BASED_ON, initial="daily", label=_trans("Based on")
    )
    rotate_after_day = forms.IntegerField(initial=5, label=_trans("Rotate after day"))
    start_date = forms.DateField(
        initial=datetime.date.today, widget=forms.DateInput, label=_trans("Start date")
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingShiftAssign
        fields = "__all__"
        exclude = [
            "next_change_date",
            "current_shift",
            "next_shift",
            "is_active",
            "additional_data",
        ]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "rotating_shift_id": _trans("Rotating Shift"),
            "start_date": _("Start date"),
            "is_active": _trans("Is Active"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            if field.required:
                self.fields[field_name].label_suffix = " *"

        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_shift_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def clean_employee_id(self):
        """
        Validation to employee_id field
        """
        employee_ids = self.cleaned_data.get("employee_id")
        if employee_ids:
            return employee_ids[0]
        else:
            return ValidationError(_("This field is required"))

    def clean(self):
        super().clean()
        self.instance.employee_id = Employee.objects.filter(
            id=self.data.get("employee_id")
        ).first()

        self.errors.pop("employee_id", None)
        if self.instance.employee_id is None:
            raise ValidationError({"employee_id": _("This field is required")})
        super().clean()
        cleaned_data = super().clean()
        if "rotate_after_day" in self.errors:
            del self.errors["rotate_after_day"]
        return cleaned_data

    def save(
        self,
        commit=False,
    ):
        employee_ids = self.data.getlist("employee_id")
        rotating_shift = RotatingShift.objects.get(id=self.data["rotating_shift_id"])

        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())
        for employee_id in employee_ids:
            employee = Employee.objects.filter(id=employee_id).first()
            rotating_shift_assign = RotatingShiftAssign()
            rotating_shift_assign.rotating_shift_id = rotating_shift
            rotating_shift_assign.employee_id = employee
            rotating_shift_assign.based_on = self.cleaned_data["based_on"]
            rotating_shift_assign.start_date = self.cleaned_data["start_date"]
            rotating_shift_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_shift_assign.rotate_after_day = self.data.get("rotate_after_day")
            rotating_shift_assign.rotate_every = self.cleaned_data["rotate_every"]
            rotating_shift_assign.rotate_every_weekend = self.cleaned_data[
                "rotate_every_weekend"
            ]
            rotating_shift_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_shift_assign.current_shift = employee.employee_work_info.shift_id
            rotating_shift_assign.next_shift = rotating_shift.shift1
            rotating_shift_assign.additional_data["next_shift_index"] = 1
            based_on = self.cleaned_data["based_on"]
            start_date = self.cleaned_data["start_date"]
            if based_on == "weekly":
                next_date = get_next_week_date(target_day, start_date)
                rotating_shift_assign.next_change_date = next_date
            elif based_on == "monthly":
                # 0, 1, 2, ..., 31, or "last"
                rotate_every = self.cleaned_data["rotate_every"]
                start_date = self.cleaned_data["start_date"]
                next_date = get_next_monthly_date(start_date, rotate_every)
                rotating_shift_assign.next_change_date = next_date
            elif based_on == "after":
                rotating_shift_assign.next_change_date = (
                    rotating_shift_assign.start_date
                    + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
                )
            rotating_shift_assign.save()


class RotatingShiftAssignUpdateForm(ModelForm):
    """
    RotatingShiftAssign model's form
    """

    based_on = forms.ChoiceField(
        choices=BASED_ON, initial="daily", label=_trans("Based on")
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingShiftAssign
        fields = "__all__"
        exclude = [
            "next_change_date",
            "current_shift",
            "next_shift",
            "is_active",
            "additional_data",
        ]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "start_date": _trans("Start date"),
            "rotate_after_day": _trans("Rotate after day"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
            "based_on": _trans("Based on"),
            "is_active": _trans("Is Active"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for field_name, field in self.fields.items():
            if field.required:
                self.fields[field_name].label_suffix = " *"

        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0; border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0; border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0; border:1px solid hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_shift_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def save(self, *args, **kwargs):
        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())

        based_on = self.cleaned_data["based_on"]
        start_date = self.instance.start_date
        if based_on == "weekly":
            next_date = get_next_week_date(target_day, start_date)
            self.instance.next_change_date = next_date
        elif based_on == "monthly":
            rotate_every = self.instance.rotate_every  # 0, 1, 2, ..., 31, or "last"
            start_date = self.instance.start_date
            next_date = get_next_monthly_date(start_date, rotate_every)
            self.instance.next_change_date = next_date
        elif based_on == "after":
            self.instance.next_change_date = (
                self.instance.start_date
                + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
            )
        return super().save()


class ShiftRequestForm(ModelForm):
    """
    ShiftRequest model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ShiftRequest
        fields = "__all__"
        exclude = [
            "reallocate_to",
            "approved",
            "canceled",
            "reallocate_approved",
            "reallocate_canceled",
            "previous_shift_id",
            "is_active",
            "shift_changed",
        ]
        widgets = {
            "requested_date": DateInput(attrs={"type": "date"}),
            "requested_till": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "description": _trans("Description"),
            "requested_date": _trans("Requested Date"),
            "requested_till": _trans("Requested Till"),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            if hasattr(employee, "employee_work_info"):
                self.instance.previous_shift_id = employee.employee_work_info.shift_id
                if self.instance.is_permanent_shift:
                    self.instance.requested_till = None
        return super().save(commit)

    # here set default filter for all the employees those have work information filled.


class ShiftAllocationForm(ModelForm):
    """
    ShiftRequest model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ShiftRequest
        fields = "__all__"
        exclude = (
            "is_permanent_shift",
            "approved",
            "canceled",
            "reallocate_approved",
            "reallocate_canceled",
            "previous_shift_id",
            "is_active",
            "shift_changed",
        )
        widgets = {
            "requested_date": DateInput(attrs={"type": "date"}),
            "requested_till": DateInput(attrs={"type": "date", "required": "true"}),
        }

        labels = {
            "description": _trans("Description"),
            "requested_date": _trans("Requested Date"),
            "requested_till": _trans("Requested Till"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shift_id"].widget.attrs.update(
            {
                "hx-target": "#id_reallocate_to_parent_div",
                "hx-trigger": "change",
                "hx-get": "/update-employee-allocation",
            }
        )

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            if hasattr(employee, "employee_work_info"):
                self.instance.previous_shift_id = employee.employee_work_info.shift_id
                if not self.instance.requested_till:
                    self.instance.requested_till = (
                        employee.employee_work_info.contract_end_date
                    )
        return super().save(commit)


class WorkTypeRequestForm(ModelForm):
    """
    WorkTypeRequest model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = WorkTypeRequest
        fields = "__all__"
        exclude = (
            "approved",
            "canceled",
            "previous_work_type_id",
            "is_active",
            "work_type_changed",
        )
        widgets = {
            "requested_date": DateInput(attrs={"type": "date"}),
            "requested_till": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "requested_date": _trans("Requested Date"),
            "requested_till": _trans("Requested Till"),
            "description": _trans("Description"),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            if hasattr(employee, "employee_work_info"):
                self.instance.previous_work_type_id = (
                    employee.employee_work_info.work_type_id
                )
                if self.instance.is_permanent_work_type:
                    self.instance.requested_till = None
        return super().save(commit)


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter Old Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter your old password."),
    )
    new_password = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter New Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
    )
    confirm_password = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Re-Enter Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Incorrect old password.")
        return old_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password")
        if self.user.check_password(new_password):
            raise forms.ValidationError(
                "New password must be different from the old password."
            )

        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError(
                {"new_password": _("New password and confirm password do not match")}
            )

        return cleaned_data


class ChangeUsernameForm(forms.Form):
    old_username = forms.CharField(
        label=_("Old Username"),
        strip=False,
        widget=forms.TextInput(
            attrs={
                "readonly": "readonly",
                "class": "oh-input oh-input--text w-100 mb-2",
            }
        ),
    )

    username = forms.CharField(
        label=_("Username"),
        strip=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter New Username"),
                "class": "oh-input oh-input--text w-100 mb-2",
            }
        ),
        help_text=_("Enter your username."),
    )

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": _("Enter Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter your password."),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangeUsernameForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        password = self.cleaned_data.get("password")
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password


class ResetPasswordForm(SetPasswordForm):
    """
    ResetPasswordForm
    """

    new_password1 = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter Strong Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter your new password."),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Re-Enter Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter the same password as before, for verification."),
    )

    def save(self, commit=True):
        if self.is_valid():
            request = getattr(_thread_locals, "request", None)
            if request:
                messages.success(request, _("Password changed successfully"))
        return super().save()

    def clean_confirm_password(self):
        """
        validation method for confirm password field
        """
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("confirm_password")
        if password == confirm_password:
            return confirm_password
        raise forms.ValidationError(_("Password must be same."))


excluded_fields = [
    "id",
    "is_active",
    "reallocate_approved",
    "reallocate_canceled",
    "shift_changed",
    "work_type_changed",
    "created_at",
    "created_by",
    "modified_by",
    "additional_data",
    "horilla_history",
    "additional_data",
]


class ShiftRequestColumnForm(forms.Form):
    model_fields = ShiftRequest._meta.get_fields()
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
            "requested_date",
            "requested_till",
            "previous_shift_id",
            "approved",
        ],
    )


class WorkTypeRequestColumnForm(forms.Form):
    model_fields = WorkTypeRequest._meta.get_fields()
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
            "work_type_id",
            "requested_date",
            "requested_till",
            "previous_shift_id",
            "approved",
        ],
    )


class RotatingShiftAssignExportForm(forms.Form):
    model_fields = RotatingShiftAssign._meta.get_fields()
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
            "rotating_shift_id",
            "start_date",
            "next_change_date",
            "current_shift",
            "next_shift",
            "based_on",
        ],
    )


class RotatingWorkTypeAssignExportForm(forms.Form):
    model_fields = RotatingWorkTypeAssign._meta.get_fields()
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
            "rotating_work_type_id",
            "start_date",
            "next_change_date",
            "current_work_type",
            "next_work_type",
            "based_on",
        ],
    )


class TagsForm(ModelForm):
    """
    Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Tags
        fields = "__all__"
        widgets = {"color": TextInput(attrs={"type": "color", "style": "height:50px"})}
        exclude = ["objects", "is_active"]

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html


class AuditTagForm(ModelForm):
    """
    Audit Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AuditTag
        fields = "__all__"


class ShiftRequestCommentForm(ModelForm):
    """
    Shift request comment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ShiftRequestComment
        fields = ("comment",)


class WorkTypeRequestCommentForm(ModelForm):
    """
    WorkType request comment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = WorkTypeRequestComment
        fields = ("comment",)


class DynamicMailConfForm(ModelForm):
    """
    DynamicEmailConfiguration
    """

    class Meta:
        model = DynamicEmailConfiguration
        fields = "__all__"
        exclude = ["is_active"]

    # def clean(self):
    #     from_mail = self.from_email
    #     return super().clean()
    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("horilla_form.html", context)
        return table_html


class DynamicMailTestForm(forms.Form):
    """
    DynamicEmailTest
    """

    to_email = forms.EmailField(label="To email", required=True)


class MailTemplateForm(ModelForm):
    """
    MailTemplateForm
    """

    class Meta:
        model = HorillaMailTemplate
        fields = "__all__"
        widgets = {
            "body": forms.Textarea(
                attrs={"data-summernote": "", "style": "display:none;"}
            ),
        }

    def get_template_language(self):
        mail_data = {
            "Receiver|Full name": "instance.get_full_name",
            "Sender|Full name": "self.get_full_name",
            "Receiver|Recruitment": "instance.recruitment_id",
            "Sender|Recruitment": "self.recruitment_id",
            "Receiver|Company": "instance.get_company",
            "Sender|Company": "self.get_company",
            "Receiver|Job position": "instance.get_job_position",
            "Sender|Job position": "self.get_job_position",
            "Receiver|Email": "instance.get_mail",
            "Sender|Email": "self.get_mail",
            "Receiver|Employee Type": "instance.get_employee_type",
            "Sender|Employee Type": "self.get_employee_type",
            "Receiver|Work Type": "instance.get_work_type",
            "Sender|Work Type": "self.get_work_type",
            "Candidate|Full name": "instance.get_full_name",
            "Candidate|Recruitment": "instance.recruitment_id",
            "Candidate|Company": "instance.get_company",
            "Candidate|Job position": "instance.get_job_position",
            "Candidate|Email": "instance.get_email",
            "Candidate|Interview Table": "instance.get_interview|safe",
        }
        return mail_data


class MultipleApproveConditionForm(ModelForm):
    CONDITION_CHOICE = [
        ("equal", _("Equal (==)")),
        ("notequal", _("Not Equal (!=)")),
        ("range", _("Range")),
        ("lt", _("Less Than (<)")),
        ("gt", _("Greater Than (>)")),
        ("le", _("Less Than or Equal To (<=)")),
        ("ge", _("Greater Than or Equal To (>=)")),
        ("icontains", _("Contains")),
    ]

    multi_approval_manager = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "oh-select oh-select-2 mb-2"}),
        label=_("Approval Manager"),
        required=True,
    )
    condition_operator = forms.ChoiceField(
        choices=CONDITION_CHOICE,
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select-2 mb-2",
                "hx-trigger": "change",
                "hx-target": "#conditionValueDiv",
                "hx-get": "condition-value-fields",
            },
        ),
    )

    class Meta:
        model = MultipleApprovalCondition
        fields = "__all__"
        exclude = [
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("reporting_manager_id", _("Reporting Manager"))] + [
            (employee.pk, str(employee)) for employee in Employee.objects.all()
        ]
        self.fields["multi_approval_manager"].choices = choices


class DynamicPaginationForm(ModelForm):
    """
    Form for setting default pagination
    """

    class Meta:
        model = DynamicPagination
        fields = "__all__"
        exclude = ("user_id",)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [
                single_file_clean(data, initial),
            ]
        return result[0] if result else None


class AnnouncementForm(ModelForm):
    """
    Announcement Form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Announcement
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"data-summernote": ""}),
            "expire_date": DateInput(attrs={"type": "date"}),
        }

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        # Remove HTML tags and check if there's meaningful content
        text_content = strip_tags(description).strip()
        if not text_content:  # Checks if the field is empty after stripping HTML
            raise forms.ValidationError("Description is required.")
        return description

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attachments"] = MultipleFileField(label="Attachments ")
        self.fields["attachments"].required = False
        self.fields["description"].required = False

    def save(self, commit: bool = ...) -> Any:
        attachement = []
        multiple_attachment_ids = []
        attachements = None
        if self.files.getlist("attachments"):
            attachements = self.files.getlist("attachments")
            self.instance.attachement = attachements[0]
            multiple_attachment_ids = []

            for attachement in attachements:
                file_instance = Attachment()
                file_instance.file = attachement
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.attachements.add(*multiple_attachment_ids)
        return instance, multiple_attachment_ids


class AnnouncementCommentForm(ModelForm):
    """
    Announcement comment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AnnouncementComment
        fields = ["comment"]


class AnnouncementExpireForm(ModelForm):
    """
    Announcement Expire form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AnnouncementExpire
        fields = ("days",)


class DriverForm(forms.ModelForm):
    """
    DriverForm
    """

    class Meta:
        model = DriverViewed
        fields = "__all__"


UserModel = get_user_model()


class PassWordResetForm(forms.Form):
    email = forms.CharField()

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")

        email_message.send()

    def get_users(self, email):
        """
        Given an email, return matching user(s) who should receive a reset.

        This allows subclasses to more easily customize the default policies
        that prevent inactive users and users with unusable passwords from
        resetting their password.
        """
        email_field_name = UserModel.get_email_field_name()
        active_users = UserModel._default_manager.filter(
            **{
                "%s__iexact" % email_field_name: email,
                "is_active": True,
            }
        )
        return (
            u
            for u in active_users
            if u.has_usable_password()
            and _unicode_ci_compare(email, getattr(u, email_field_name))
        )

    def save(
        self,
        domain_override=None,
        subject_template_name="registration/password_reset_subject.txt",
        email_template_name="registration/password_reset_email.html",
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        username = self.cleaned_data["email"]
        user = User.objects.get(username=username)
        employee = user.employee_get
        email = employee.email
        work_mail = None
        try:
            work_mail = employee.employee_work_info.email
        except Exception as e:
            pass
        if work_mail:
            email = work_mail

        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        if email:
            token = token_generator.make_token(user)
            context = {
                "email": email,
                "domain": domain,
                "site_name": site_name,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "user": user,
                "token": token,
                "protocol": "https" if use_https else "http",
                **(extra_email_context or {}),
            }
            self.send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                email,
                html_email_template_name=html_email_template_name,
            )


def validate_ip_or_cidr(value):
    try:
        ipaddress.ip_address(value)
    except ValueError:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            raise ValidationError(
                f"{value} is not a valid IP address or CIDR notation."
            )


class AttendanceAllowedIPForm(forms.ModelForm):
    ip_addresses = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control w-100"}),
        label="Allowed IP Addresses or Network Prefixes",
        help_text="Enter multiple IP addresses or network prefixes, separated by commas.",
    )

    class Meta:
        model = AttendanceAllowedIP
        fields = ["ip_addresses"]

    def clean_ip_addresses(self):
        ip_addresses = self.cleaned_data.get("ip_addresses", "").strip().split("\n")
        cleaned_ips = []
        for ip in ip_addresses:
            ip = ip.strip().split(", ")
            if ip:
                for ip_addr in ip:
                    validate_ip_or_cidr(ip_addr)
                    cleaned_ips.append(ip_addr)
        return cleaned_ips

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.pk:
            existing_ips = set(instance.additional_data.get("allowed_ips", []))
            new_ips = set(self.cleaned_data["ip_addresses"])
            merged_ips = list(existing_ips.union(new_ips))
            instance.additional_data["allowed_ips"] = merged_ips
        else:
            instance.additional_data = {
                "allowed_ips": self.cleaned_data["ip_addresses"]
            }

        if commit:
            instance.save()

        return instance


class AttendanceAllowedIPUpdateForm(ModelForm):
    ip_address = forms.CharField(max_length=30, label="IP Address")

    class Meta:
        model = AttendanceAllowedIP
        fields = ["ip_address"]

    def validate_ip_address(self, value):
        try:
            validate_ipv46_address(value)
        except ValidationError:
            raise ValidationError("Enter a valid IPv4 or IPv6 address.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        for field_name, value in self.data.items():
            cleaned_data[field_name] = self.validate_ip_address(value)

        return cleaned_data


class TrackLateComeEarlyOutForm(ModelForm):
    class Meta:
        model = TrackLateComeEarlyOut
        fields = ["is_enable"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_enable"].widget.attrs.update(
            {
                "hx-post": "/attendance/enable-disable-tracking-late-come-early-out",
                "hx-target": "this",
                "hx-trigger": "change",
            }
        )


class HolidayForm(ModelForm):
    """
    Form for creating or updating a holiday.

    This form allows users to create or update holiday data by specifying details such as
    the start date and end date.

    Attributes:
        - start_date: A DateField representing the start date of the holiday.
        - end_date: A DateField representing the end date of the holiday.
    """

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_end_date(self):
        start_date = self.cleaned_data.get("start_date")
        end_date = self.cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                _("End date should not be earlier than the start date.")
            )

        return end_date

    class Meta:
        """
        Meta class for additional options
        """

        model = Holidays
        fields = "__all__"
        exclude = ["is_active"]
        labels = {
            "name": _("Name"),
        }

    def __init__(self, *args, **kwargs):
        super(HolidayForm, self).__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["autocomplete"] = "name"


class HolidaysColumnExportForm(forms.Form):
    """
    Form for selecting columns to export in holiday data.

    This form allows users to select specific columns from the Holidays model
    for export. The available columns are dynamically generated based on the
    model's meta information, excluding specified excluded_fields.

    Attributes:
        - model_fields: A list of fields in the Holidays model.
        - field_choices: A list of field choices for the form, consisting of field names
          and their verbose names, excluding specified excluded_fields.
        - selected_fields: A MultipleChoiceField representing the selected columns
          to be exported.
    """

    model_fields = Holidays._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name.capitalize())
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "name",
            "start_date",
            "end_date",
            "recurring",
        ],
    )


class CompanyLeaveForm(ModelForm):
    """
    Form for managing company leave data.

    This form allows users to manage company leave data by including all fields from
    the CompanyLeaves model except for is_active.

    Attributes:
        - Meta: Inner class defining metadata options.
            - model: The model associated with the form (CompanyLeaves).
            - fields: A special value indicating all fields should be included in the form.
            - exclude: A list of fields to exclude from the form (is_active).
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = CompanyLeaves
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        """
        Custom initialization to configure the 'based_on' field.
        """
        super().__init__(*args, **kwargs)
        self.fields["based_on_week"].widget.option_template_name = (
            "horilla_widgets/select_option.html"
        )


class PenaltyAccountForm(ModelForm):
    """
    PenaltyAccountForm
    """

    class Meta:
        model = PenaltyAccounts
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop("employee", None)
        super().__init__(*args, **kwargs)
        if apps.is_installed("leave") and employee:
            LeaveType = get_horilla_model_class(app_label="leave", model="leavetype")
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )
            self.fields["leave_type_id"].queryset = assigned_leave_types
