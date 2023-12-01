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
import re
from django import forms
from django.db.models import Q
from django.contrib.auth.models import User
from django.forms import DateInput, TextInput
from django.utils.translation import gettext_lazy as trans
from employee.models import Employee, EmployeeWorkInformation, EmployeeBankDetails
from base.methods import reload_queryset


class ModelForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for _, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget,
                (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput),
            ):
                label = trans(field.label.title())
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = trans(field.label)
                field.empty_label = trans("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                if field.label is not None:
                    label = trans(field.label)
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


class UserForm(ModelForm):
    """
    Form for User model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = ("groups",)
        model = User


class UserPermissionForm(ModelForm):
    """
    Form for User model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = ("groups", "user_permissions")
        model = User


class EmployeeForm(ModelForm):
    """
    Form for Employee model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Employee
        fields = "__all__"
        exclude = ("employee_user_id",)
        widgets = {
            "dob": TextInput(attrs={"type": "date", "id": "dob"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if instance := kwargs.get("instance"):
            # ----
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            # ----
            initial = {}
            if instance.dob is not None:
                initial["dob"] = instance.dob.strftime("%H:%M")
            kwargs["initial"] = initial
        else:
            self.initial = {"badge_id": self.get_next_badge_id()}

    def get_next_badge_id(self):
        """
        This method is used to generate badge id
        """
        try:
            # total_employee_count = Employee.objects.count()
            badge_ids = Employee.objects.filter(~Q(badge_id=None)).order_by("-badge_id")
            greatest_id = badge_ids.first().badge_id
            match = re.findall(r"\d+", greatest_id[::-1])
            total_employee_count = 0
            if match:
                total_employee_count = int(match[0][::-1])
        except Exception:
            total_employee_count = 0
        try:
            string = (
                Employee.objects.filter(~Q(badge_id=None))
                .order_by("-badge_id")
                .last()
                .badge_id
            )
        except Exception:
            string = "DUDE"
        # Find the index of the last integer group in the string
        integer_group_index = None
        for i in range(len(string) - 1, -1, -1):
            if string[i].isdigit():
                integer_group_index = i
            elif integer_group_index is not None:
                break

        if integer_group_index is None:
            # There is no integer group in the string, so just append #01
            return string + "#01"
        # Extract the integer group from the string
        integer_group = string[integer_group_index:]
        prefix = string[:integer_group_index]

        # Set the integer group to the total number of employees plus one
        new_integer_group = str(total_employee_count + 1).zfill(len(integer_group))

        # Return the new string
        return prefix + new_integer_group

    def clean_badge_id(self):
        """
        This method is used to clean the badge id
        """
        badge_id = self.cleaned_data["badge_id"]
        if badge_id:
            queryset = Employee.objects.filter(badge_id=badge_id).exclude(
                pk=self.instance.pk if self.instance else None
            )
            if queryset.exists():
                raise forms.ValidationError(trans("Badge ID must be unique."))
            if not re.search(r"\d", badge_id):
                raise forms.ValidationError(
                    trans("Badge ID must contain at least one digit.")
                )
        return badge_id


class EmployeeWorkInformationForm(ModelForm):
    """
    Form for EmployeeWorkInformation model
    """

    employees = Employee.objects.filter(employee_work_info=None)
    employee_id = forms.ModelChoiceField(queryset=employees)

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeWorkInformation
        fields = "__all__"
        widgets = {
            "date_joining": DateInput(attrs={"type": "date"}),
            "contract_end_date": DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, disable=False, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["placeholder"] = self.fields[field].label
            if disable:
                self.fields[field].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if "employee_id" in self.errors:
            del self.errors["employee_id"]
        return cleaned_data


class EmployeeWorkInformationUpdateForm(ModelForm):
    """
    Form for EmployeeWorkInformation model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeWorkInformation
        fields = "__all__"
        exclude = ("employee_id",)

        widgets = {
            "date_joining": DateInput(attrs={"type": "date"}),
            "contract_end_date": DateInput(attrs={"type": "date"}),
        }


class EmployeeBankDetailsForm(ModelForm):
    """
    Form for EmployeeBankDetails model
    """

    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2, "cols": 40}))

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeBankDetails
        fields = "__all__"
        exclude = [
            "employee_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "oh-input w-100"


class EmployeeBankDetailsUpdateForm(ModelForm):
    """
    Form for EmployeeBankDetails model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeBankDetails
        fields = "__all__"
        exclude = ("employee_id",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "oh-input w-100"
        for field in self.fields:
            self.fields[field].widget.attrs["placeholder"] = self.fields[field].label


excel_columns = [
    ("badge_id", trans("Badge ID")),
    ("employee_first_name", trans("First Name")),
    ("employee_last_name", trans("Last Name")),
    ("email", trans("Email")),
    ("phone", trans("Phone")),
    ("experience", trans("Experience")),
    ("gender", trans("Gender")),
    ("dob", trans("Date of Birth")),
    ("country", trans("Country")),
    ("state", trans("State")),
    ("city", trans("City")),
    ("address", trans("Address")),
    ("zip", trans("Zip Code")),
    ("marital_status", trans("Marital Status")),
    ("children", trans("Children")),
    ("is_active", trans("Is active")),
    ("emergency_contact", trans("Emergency Contact")),
    ("emergency_contact_name", trans("Emergency Contact Name")),
    ("emergency_contact_relation", trans("Emergency Contact Relation")),
    ("employee_work_info__email", trans("Work Email")),
    ("employee_work_info__mobile", trans("Work Phone")),
    ("employee_work_info__department_id", trans("Department")),
    ("employee_work_info__job_position_id", trans("Job Position")),
    ("employee_work_info__job_role_id", trans("Job Role")),
    ("employee_work_info__shift_id", trans("Shift")),
    ("employee_work_info__work_type_id", trans("Work Type")),
    ("employee_work_info__reporting_manager_id", trans("Reporting Manager")),
    ("employee_work_info__employee_type_id", trans("Employee Type")),
    ("employee_work_info__location", trans("Work Location")),
    ("employee_work_info__date_joining", trans("Date Joining")),
    ("employee_work_info__company_id", trans("Company")),
    ("employee_bank_details__bank_name", trans("Bank Name")),
    ("employee_bank_details__branch", trans("Branch")),
    ("employee_bank_details__account_number", trans("Account Number")),
    ("employee_bank_details__any_other_code1", trans("Bank Code #1")),
    ("employee_bank_details__any_other_code2", trans("Bank Code #2")),
    ("employee_bank_details__country", trans("Country")),
    ("employee_bank_details__state", trans("State")),
    ("employee_bank_details__city", trans("City")),
]


class EmployeeExportExcelForm(forms.Form):
    selected_fields = forms.MultipleChoiceField(
        choices=excel_columns,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "badge_id",
            "employee_first_name",
            "employee_last_name",
            "email",
            "phone",
            "gender",
            "employee_work_info__department_id",
            "employee_work_info__job_position_id",
            "employee_work_info__job_role_id",
            "employee_work_info__shift_id",
            "employee_work_info__work_type_id",
            "employee_work_info__reporting_manager_id",
            "employee_work_info__employee_type_id",
            "employee_work_info__company_id",
        ],
    )
