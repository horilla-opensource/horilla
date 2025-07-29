# pylint: disable=too-few-public-methods
"""
Module containing forms for managing biometric devices and associated data.

This module provides Django forms for creating and managing biometric devices,
employee biometric data, COSEC users, and related configurations.
"""

from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from base.forms import Form, ModelForm
from base.methods import reload_queryset
from employee.models import Employee
from horilla.horilla_middlewares import _thread_locals
from horilla_widgets.forms import default_select_option_template

from .models import BiometricDevices, BiometricEmployees


class BiometricDeviceForm(ModelForm):
    """
    Form for creating and updating biometric device configurations.

    This form is used to create and update biometric device configurations.
    It includes fields for specifying the device name, IP address, TCP communication port,
    and other relevant settings. Additionally, it excludes fields related to scheduler
    settings and device activation status.
    """

    class Meta:
        """
        Meta class to add additional options
        """

        model = BiometricDevices
        fields = "__all__"
        exclude = [
            "is_scheduler",
            "scheduler_duration",
            "last_fetch_date",
            "last_fetch_time",
            "is_active",
        ]
        widgets = {
            "machine_type": forms.Select(
                attrs={
                    "id": "machineTypeInput",
                    "onchange": "machineTypeChange($(this))",
                }
            ),
            "bio_password": forms.TextInput(
                attrs={
                    "class": "oh-input oh-input--password w-100",
                    "type": "password",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company_widget = self.fields["company_id"].widget
        if isinstance(company_widget, forms.Select):
            company_widget.option_template_name = default_select_option_template


class BiometricDeviceSchedulerForm(ModelForm):
    """
    Form for updating the scheduler duration of a biometric device.

    This form is used to update the scheduler duration of a biometric
    device to fetch attendance data.
    It includes a field for entering the scheduler duration in the format HH:MM.
    """

    class Meta:
        """
        Meta class to add additional options
        """

        model = BiometricDevices
        fields = ["scheduler_duration"]
        labels = {
            "scheduler_duration": _("Enter the duration in the format HH:MM"),
        }


class EmployeeBiometricAddForm(Form):
    """
    Form for adding employees to a biometric device.

    This form allows administrators to add employees to a biometric device
    for biometric authentication. It includes a field for selecting employees from
    a queryset and ensures that only active employees not already associated with
    a 'zk' type biometric device are available for selection.
    """

    employee_ids = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple(),
        label=_("Employees"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = getattr(_thread_locals, "request")
        self.device_id = (
            self.request.resolver_match.kwargs.get("device_id", None)
            if self.request.resolver_match
            else None
        )
        self.device = BiometricDevices.find(self.device_id)
        zk_employee_ids = BiometricEmployees.objects.filter(
            device_id=self.device
        ).values_list("employee_id", flat=True)
        self.fields["employee_ids"].queryset = Employee.objects.filter(
            is_active=True
        ).exclude(id__in=zk_employee_ids)


class CosecUserAddForm(Form):
    """
    Form for adding users to a COSEC biometric device.

    This form allows administrators to add multiple users to a COSEC biometric device
    for biometric authentication. It includes a field for selecting users from
    a queryset and ensures that only active users not already associated with
    a 'cosec' type biometric device are available for selection.
    """

    employee_ids = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple(),
        label=_("Employees"),
    )

    def __init__(self, *args, device_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        cosec_employee_ids = BiometricEmployees.objects.filter(
            device_id=device_id
        ).values_list("employee_id", flat=True)
        self.fields["employee_ids"].queryset = Employee.objects.filter(
            is_active=True
        ).exclude(id__in=cosec_employee_ids)


class COSECUserForm(Form):
    """
    Form for adding or updating users in a COSEC biometric device.

    This form allows administrators to add or update users in a COSEC biometric
    device. It includes fields for specifying the user's name, whether the user
    is active, whether the user is a VIP user, whether validity is enabled for
    the user, the validity end date, and whether to bypass finger-based
    authentication for the user. It provides validation to ensure that the
    name does not exceed 15 characters and that the validity end date is
    provided when validity is enabled.
    """

    name = forms.CharField(
        label=_("Employee Name"),
        help_text=_("15 characters max."),
        widget=forms.TextInput(attrs={"class": "oh-input w-100"}),
    )
    user_active = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(),
    )
    vip = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(),
    )
    validity_enable = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(),
    )
    validity_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date", "class": "oh-input w-100 form-control"}
        ),
    )
    by_pass_finger = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(),
    )

    def clean(self):
        cleaned_data = super().clean()
        if len(cleaned_data["name"]) > 15:
            raise forms.ValidationError(
                "Maximum 15 characters allowed for Name in COSEC Biometric Device"
            )
        if cleaned_data["validity_enable"]:
            if cleaned_data.get("validity_end_date") is None:
                raise forms.ValidationError(
                    "When the Validity field is enabled, a Validity End Date is required."
                )


class DahuaUserForm(Form):
    """
    This form is used to map a Horilla employee to a user entry on a Dahua biometric device.
    """

    CARD_STATUS_CHOICES = [
        (0, "Normal"),
        (1 << 0, "Reported for loss"),
        (1 << 1, "Canceled"),
        (1 << 2, "Frozen"),
        (1 << 3, "Arrearage"),
        (1 << 4, "Overdue"),
        (1 << 5, "Pre-arrearage (The door still can be unlocked with a voice prompt)"),
    ]
    CARD_TYPE_CHOICES = [
        (0, "Ordinary card"),
        (1, "VIP card"),
        (2, "Guest card"),
        (3, "Patrol card"),
        (4, "Blocklist card"),
        (5, "Duress card"),
    ]
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.Select(),
        label=_("Employee"),
    )
    card_no = forms.CharField(max_length=50, required=True, label=_("Card Number"))
    user_id = forms.CharField(max_length=50, required=True, label=_("User ID"))
    card_status = forms.ChoiceField(
        choices=CARD_STATUS_CHOICES,
        required=False,
        label=_("Card Status"),
        initial=0,
    )
    card_type = forms.ChoiceField(
        choices=CARD_TYPE_CHOICES, required=False, label=_("Card Type")
    )
    password = forms.CharField(max_length=50, required=False, label=_("Password"))
    forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "oh-input w-100", "type": "datetime-local"}
        ),
    )
    valid_date_start = forms.DateTimeField(
        required=False,
        label=_("Valid Date Start"),
        widget=forms.DateTimeInput(
            attrs={"class": "oh-input w-100", "type": "datetime-local"}
        ),
    )
    valid_date_end = forms.DateTimeField(
        required=False,
        label=_("Valid Date End"),
        widget=forms.DateTimeInput(
            attrs={"class": "oh-input w-100", "type": "datetime-local"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request = getattr(_thread_locals, "request")
        self.device_id = (
            self.request.resolver_match.kwargs.get("device_id", None)
            if self.request.resolver_match
            else None
        )
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["employee"].widget.attrs.update(
            {
                "hx-include": "#dahuaBiometricUserForm",
                "hx-target": "#id_user_id",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-get": "/biometric/find-employee-badge-id",
            }
        )

    def clean(self):
        cleaned_data = super().clean()
        device = None
        error_fields = {}
        card_no = cleaned_data.get("card_no")
        user_id = cleaned_data.get("user_id")

        if self.device_id:
            device = BiometricDevices.find(self.device_id)

        if card_no and device:
            if BiometricEmployees.objects.filter(
                dahua_card_no=card_no, device_id=device
            ).exists():
                error_fields["card_no"] = _("This Card Number already exists.")

        if user_id and device:
            if BiometricEmployees.objects.filter(
                user_id=user_id, device_id=device
            ).exists():
                error_fields["user_id"] = _("This User ID already exists.")

        if error_fields:
            raise forms.ValidationError(error_fields)

        return cleaned_data


class MapBioUsers(ModelForm):
    """
    Form for mapping biometric users to Horilla employees.

    This form is used to associate a biometric user (from a biometric device) with
    an employee in the Horilla system.
    """

    class Meta:
        """
        Meta class to add additional options
        """

        model = BiometricEmployees
        fields = ["employee_id", "user_id"]

    def __init__(self, *args, **kwargs):
        self.request = getattr(_thread_locals, "request")
        self.device_id = (
            self.request.resolver_match.kwargs.get("device_id", None)
            if self.request.resolver_match
            else None
        )
        super().__init__(*args, **kwargs)
        if self.device_id:
            already_mapped_employees = BiometricEmployees.objects.filter(
                device_id=self.device_id
            ).values_list("employee_id", flat=True)
            self.fields["employee_id"].queryset = Employee.objects.exclude(
                Q(id__in=already_mapped_employees) | Q(is_active=False)
            )
        self.fields["user_id"].required = True

    def clean(self):
        cleaned_data = super().clean()
        user_id = cleaned_data.get("user_id")
        user_id_label = self.fields["user_id"].label or "User ID"
        if self.device_id and user_id:
            if BiometricEmployees.objects.filter(
                user_id=user_id, device_id=self.device_id
            ).exists():
                raise forms.ValidationError(
                    {
                        "user_id": _(
                            "This biometric %(label)s is already mapped with an employee"
                        )
                        % {"label": user_id_label}
                    }
                )

        return cleaned_data
