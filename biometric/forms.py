"""
Module containing forms for managing biometric devices and associated data.

This module provides Django forms for creating and managing biometric devices,
employee biometric data, COSEC users, and related configurations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from attendance.forms import ModelForm
from base.forms import Form
from employee.models import Employee

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
            "is_active",
        ]
        labels = {
            "name": _("Device Name"),
            "machine_ip": _("IP Address"),
            "port": _("TCP COMM.Port"),
            "anviz_request_id": _("Header Request ID"),
        }
        widgets = {
            "machine_type": forms.Select(
                attrs={
                    "id": "machineTypeInput",
                    "onchange": "machineTypeChange($(this))",
                }
            ),
            "cosec_password": forms.TextInput(
                attrs={
                    "class": "oh-input oh-input--password w-100",
                    "type": "password",
                }
            ),
        }


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

    This form allows administrators to add multiple employees to a biometric device
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
        zk_employee_ids = BiometricEmployees.objects.filter(
            device_id__machine_type="zk"
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
