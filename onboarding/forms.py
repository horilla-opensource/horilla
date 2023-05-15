from django import forms
from django.forms import DateInput
from .models import OnboardingStage, OnboardingTask
from employee.models import Employee, EmployeeBankDetails
from recruitment.models import Candidate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _


class ModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.DateInput)):
                field.widget.attrs.update({"class": "oh-input  w-100"})
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": field.label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
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


class UserCreationFormCustom(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget,
                (
                    forms.NumberInput,
                    forms.EmailInput,
                    forms.TextInput,
                    forms.PasswordInput,
                ),
            ):
                field.widget.attrs.update(
                    {
                        "class": "oh-input oh-input--password w-100",
                        "placeholder": field.label,
                    }
                )
            elif isinstance(widget, (forms.DateField)):
                field.widget.attrs.update({"class": "oh-input oh-calendar-input w-100"})
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": field.label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.empty_label = f"---Choose {field.label}---"
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
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


class OnboardingStageForm(ModelForm):
    class Meta:
        model = OnboardingStage
        fields = "__all__"
        exclude = ("sequence",)


class OnboardingTaskForm(forms.ModelForm):
    class Meta:
        model = OnboardingTask
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(OnboardingTaskForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"


class OnboardingCandidateForm(ModelForm):
    class Meta:
        model = Candidate
        fields = "__all__"
        exclude = (
            "stage_id",
            "assigned_manager",
            "confirmation",
            "hired",
            "referral",
            "portfolio",
            "canceled",
            "is_active",
            "resume",
            "schedule_date",
        )
        widgets = {
            "joining_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "name": _("Full Name"),
            "email": _("Email"),
            "mobile": _("Mobile"),
        }


class UserCreationForm(UserCreationFormCustom):
    class Meta:
        model = User
        fields = ["password1", "password2"]


class OnboardingViewTaskForm(ModelForm):
    class Meta:
        model = OnboardingTask
        fields = "__all__"
        exclude = ("recruitment_id",)
        labels = {
            "task_title": _("Task Title"),
        }


class OnboardingViewStageForm(ModelForm):
    class Meta:
        model = OnboardingStage
        fields = ["stage_title", "employee_id"]
        labels = {
            "stage_title": _("Stage Title"),
        }


class EmployeeCreationForm(ModelForm):
    employee_first_name = forms.CharField(required=True, label=_("First Name"))
    employee_last_name = forms.CharField(required=True, label=_("Last Name"))
    phone = forms.CharField(required=True, label=_("Phone"))
    address = forms.CharField(required=True, label=_("Address"))
    country = forms.CharField(required=True, label=_("Country"))
    state = forms.CharField(required=True, label=_("State"))
    zip = forms.CharField(required=True, label=_("Zip"))
    qualification = forms.CharField(required=True, label=_("Qualification"))
    experience = forms.IntegerField(required=True, label=_("Experience"))
    children = forms.CharField(required=True, label=_("Childrens"))
    emergency_contact = forms.CharField(
        required=True, label=_("Emergency Contact Number")
    )
    emergency_contact_name = forms.CharField(
        required=True, label=_("Emergency Contact Name")
    )
    emergency_contact_relation = forms.CharField(
        required=True, label=_("Emergency Contact Relation")
    )

    class Meta:
        model = Employee
        fields = "__all__"

    class Meta:
        model = Employee
        fields = "__all__"
        exclude = (
            "employee_user_id",
            "employee_profile",
            "email",
            "is_active",
            "additional_info",
        )
        widgets = {
            "dob": DateInput(attrs={"type": "date"}),
        }


class BankDetailsCreationForm(ModelForm):
    bank_name = forms.CharField(required=True, label="Bank Name")
    account_number = forms.CharField(required=True, label="Account Number")
    branch = forms.CharField(required=True, label="Branch")
    address = forms.Textarea()
    country = forms.CharField(required=True, label="Country")
    state = forms.CharField(required=True, label="State")
    city = forms.CharField(required=True, label="City")
    any_other_code1 = forms.CharField(required=True, label="Code #1")
    any_other_code2 = forms.CharField(required=False, label="Code #2")

    class Meta:
        model = EmployeeBankDetails
        fields = "__all__"
        exclude = ("employee_id", "additional_info")
