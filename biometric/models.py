"""
This module contains Django models for managing biometric devices
and employee attendance within a company.
"""

import uuid

import requests
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from base.models import Company
from employee.models import Employee
from horilla.models import HorillaModel
from horilla_views.cbv_methods import render_template


def validate_schedule_time_format(value):
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
            raise ValidationError(_("Invalid time"))
        if hour == 0 and minute == 0:
            raise ValidationError(_("Both hour and minute cannot be zero"))
    except ValueError as error:
        raise ValidationError(_("Invalid format, it should be HH:MM format")) from error


class BiometricDevices(HorillaModel):
    """
    Model: BiometricDevices

    Represents a biometric device used for attendance tracking within a
    company. Each device can be of different types such as ZKTeco Biometric,
    Anviz Biometric, or Matrix COSEC Biometric.The model includes fields for
    device details, authentication credentials, scheduling information, and
    company association.
    """

    BIO_DEVICE_TYPE = [
        ("zk", _("ZKTeco Biometric")),
        ("anviz", _("Anviz Biometric")),
        ("cosec", _("Matrix COSEC Biometric")),
    ]
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=100)
    machine_type = models.CharField(
        max_length=18,
        choices=BIO_DEVICE_TYPE,
        null=True,
    )
    machine_ip = models.CharField(max_length=15, null=True, blank=True, default="")
    port = models.IntegerField(null=True, blank=True)
    zk_password = models.CharField(max_length=100, null=True, blank=True, default="0")
    cosec_username = models.CharField(max_length=100, null=True, blank=True, default="")
    cosec_password = models.CharField(max_length=100, null=True, blank=True)
    anviz_request_id = models.CharField(max_length=200, null=True, blank=True)
    api_url = models.CharField(max_length=200, null=True, blank=True)
    api_key = models.CharField(max_length=100, null=True, blank=True)
    api_secret = models.CharField(max_length=100, null=True, blank=True)
    api_token = models.CharField(max_length=500, null=True, blank=True)
    api_expires = models.CharField(max_length=100, null=True, blank=True)
    is_live = models.BooleanField(default=False)
    is_scheduler = models.BooleanField(default=False)
    scheduler_duration = models.CharField(
        null=True,
        default="00:00",
        max_length=10,
        validators=[validate_schedule_time_format],
    )
    last_fetch_date = models.DateField(null=True, blank=True)
    last_fetch_time = models.TimeField(null=True, blank=True)
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )

    objects = models.Manager()

    def __str__(self):
        return f"{self.name} - {self.machine_type}"

    def get_card_details(self):
        """
        return card details based on machine type
        """

        if self.machine_type in ["zk", "cosec"]:
            return f"Machine IP : {self.machine_ip}<br>Port No : {self.port}"
        elif self.machine_type == "anviz":
            return f"API Url : {self.api_url}"
        else:
            return ""

    def render_live_capture_html(self):
        """
        live capture button
        """
        checked_attribute = "checked" if self.is_live else ""
        activate_label = "Activate live capture mode"
        activate_title = "Activate" if not self.is_live else "Deactivate"

        if self.machine_type in ["zk", "cosec"]:
            html = f"""
            <td>
                  <span class="oh-kanban-card__subtitle d-block">{activate_label}</span>
                </td>
                <td>
                <div class="oh-switch">
                    <input type="checkbox"
                        class="style-widget oh-switch__checkbox is-live-activate"
                        title="{activate_title}"
                        data-toggle="oh-modal-toggle"
                        data-target="#BiometricDeviceTestModal"
                        name="is_live"
                        {checked_attribute}
                        hx-trigger="change"
                        hx-get="/biometric/biometric-device-live-capture?deviceId=d9ab2bc7-01d5-4005-897f-01f35198d743&amp;search=&amp;machine_type=&amp;is_scheduler=unknown&amp;is_active=unknown&amp;is_live=unknown&amp;page=1&amp;view=card"
                        hx-target="#BiometricDeviceTestFormTarget" />
                </div>
                </td>
                """
            return html
        else:
            return ""

    def render_actions_html(self):
        """
        actions buttons
        """

        margin_style = (
            "style='margin-top:0px;'" if self.machine_type in ["anviz", "cosec"] else ""
        )

        test_url = reverse("biometric-device-test", args=[self.id])
        unschedule_url = reverse("biometric-device-unschedule", args=[self.id])
        schedule_url = reverse("biometric-device-schedule", args=[self.id])
        employees_url = reverse("biometric-device-employees", args=[self.id])

        html = f"""
        <div class="d-block oh-kanban-card__biometric-actions" {margin_style} style="display: flex; gap: 10px; ">
            <a href="#" hx-get="{test_url}" data-toggle="oh-modal-toggle"
                data-target="#BiometricDeviceTestModal" hx-target="#BiometricDeviceTestFormTarget"
                class="oh-checkpoint-badge text-success mr-2" style="border: 2px solid #28a745; padding: 5px 10px; border-radius: 4px; display: inline-block; color: #28a745;">Test
            </a>
            {"<a hx-confirm='Do you want to unschedule the device attendance fetching?'"
              f" hx-post='{unschedule_url}'"
              " hx-target='#biometricDeviceList' class='oh-checkpoint-badge text-info ' style='border: 2px solid #17a2b8; padding: 5px 10px; border-radius: 4px; display: inline-block; color: #17a2b8;'>Unschedule</a>"
              if self.is_scheduler else
              "<a href='#' class='oh-checkpoint-badge text-info' hx-get='" + schedule_url + "'"
              " data-toggle='oh-modal-toggle' data-target='#BiometricDeviceModal'"
              " hx-target='#BiometricDeviceFormTarget' style='border: 2px solid #17a2b8; padding: 5px 10px; border-radius: 4px; display: inline-block; color: #17a2b8;'>Schedule</a>"}
            {"<a href='" + employees_url + "' class='oh-checkpoint-badge text-secondary bio-user-list ml-4' style='border: 2px solid #6c757d; padding: 5px 10px; border-radius: 4px; display: inline-block; color: #6c757d;'>Employee</a>"
              if self.machine_type in ["zk", "cosec"] else ""}
        </div>

        """

        return html

    def archive_status(self):
        """
        archive status
        """
        if self.is_active:
            return "Archive"
        else:
            return "Un-Archive"

    def get_update_url(self):
        """
        This method to get update url
        """
        url = reverse_lazy("biometric-device-edit", kwargs={"device_id": self.pk})
        return url

    def get_archive_url(self):
        """
        This method to get archive url
        """
        url = reverse_lazy("biometric-device-archive", kwargs={"device_id": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("biometric-device-delete", kwargs={"device_id": self.pk})
        return url

    def get_machine_type(self):
        """
        return machine type from choices
        """

        return dict(self.BIO_DEVICE_TYPE).get(self.machine_type)

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
        return url

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if self.machine_type in ("zk", "cosec"):
            if not self.machine_ip:
                raise ValidationError(
                    {
                        "machine_ip": _(
                            "The Machine IP is required for ZKTeco Biometric\
                            & Matrix COSEC Biometric"
                        )
                    }
                )
            if not self.port:
                raise ValidationError(
                    {"port": _("The Port No is required for ZKTeco Biometric")}
                )
        if self.machine_type == "zk":
            if not self.zk_password:
                raise ValidationError(
                    {
                        "zk_password": _(
                            "The password is required for ZKTeco Biometric Device"
                        )
                    }
                )
            try:
                int(self.zk_password)
            except ValueError:
                raise ValidationError(
                    {
                        "zk_password": _(
                            "The password must be an integer (numeric) value for ZKTeco Biometric Device"
                        )
                    }
                )

        if self.machine_type == "cosec":
            if not self.cosec_username:
                raise ValidationError(
                    {
                        "cosec_username": _(
                            "The username is required for Matrix COSEC Biometric"
                        )
                    }
                )
            if not self.cosec_password:
                raise ValidationError(
                    {
                        "cosec_username": _(
                            "The password is required for Matrix COSEC Biometric"
                        )
                    }
                )
        if self.machine_type == "anviz":
            if not self.anviz_request_id:
                raise ValidationError(
                    {
                        "anviz_request_id": _(
                            "The Request ID required for the Anviz Biometric Device."
                        )
                    }
                )
            if not self.api_url:
                raise ValidationError(
                    {"api_url": _("The API Url required for Anviz Biometric Device")}
                )
            if not self.api_key:
                raise ValidationError(
                    {"api_key": _("The API Key required for Anviz Biometric Device")}
                )
            if not self.api_secret:
                raise ValidationError(
                    {
                        "api_secret": _(
                            "The API Secret is required for Anviz Biometric Device"
                        )
                    }
                )
            if self.anviz_request_id and self.api_key and self.api_secret:
                payload = {
                    "header": {
                        "nameSpace": "authorize.token",
                        "nameAction": "token",
                        "version": "1.0",
                        "requestId": self.anviz_request_id,
                        "timestamp": "2022-10-21T07:39:07+00:00",
                    },
                    "payload": {"api_key": self.api_key, "api_secret": self.api_secret},
                }
                error = {
                    "header": {"nameSpace": "System", "name": "Exception"},
                    "payload": {"type": "AUTH_ERROR", "message": "AUTH_ERROR"},
                }
                try:
                    response = requests.post(
                        self.api_url,
                        json=payload,
                        timeout=10,
                    )
                    if response.status_code != 200:
                        raise ValidationError(
                            {f"API call failed with status code {response.status_code}"}
                        )

                    api_response = response.json()
                    if api_response == error:
                        raise ValidationError(
                            {
                                "api_url": _(
                                    "Authentication failed. Please check your API Url\
                                    , API Key and API Secret."
                                )
                            }
                        )

                    payload = api_response["payload"]
                    api_token = payload["token"]
                    api_expires = payload["expires"]
                    self.api_token = api_token
                    self.api_expires = api_expires
                except Exception as exc:
                    raise ValidationError(
                        {
                            "api_url": _(
                                "Authentication failed. Please check your API Url , API Key\
                                and API Secret."
                            )
                        }
                    ) from exc

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Biometric Device")
        verbose_name_plural = _("Biometric Devices")


class BiometricEmployees(models.Model):
    """
    Model: BiometricEmployees

    Description:
    Represents the association between employees and biometric devices for
    attendance tracking within a company.Each entry in this model maps an
    employee to a specific biometric device.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    uid = models.IntegerField(null=True, blank=True)
    ref_user_id = models.IntegerField(
        null=True, blank=True, validators=[MaxValueValidator(99999999)]
    )
    user_id = models.CharField(max_length=100)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    device_id = models.ForeignKey(
        BiometricDevices, on_delete=models.CASCADE, null=True, blank=True
    )
    objects = models.Manager()

    def __str__(self):
        return f"{self.employee_id} - {self.user_id}"

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Employee in Biometric Device")
        verbose_name_plural = _("Employees in Biometric Device")


class COSECAttendanceArguments(models.Model):
    """
    Model: COSECAttendanceArguments

    Description:
    Represents arguments related to attendance fetching for COSEC biometric
    devices within a company.This model stores information such as the last
    fetched roll-over count and sequence number for COSEC devices.
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    last_fetch_roll_ovr_count = models.CharField(max_length=100, null=True)
    last_fetch_seq_number = models.CharField(max_length=100, null=True)
    device_id = models.ForeignKey(
        BiometricDevices, on_delete=models.CASCADE, null=True, blank=True
    )
    objects = models.Manager()

    def __str__(self):
        return f"{self.device_id} - {self.last_fetch_roll_ovr_count} - {self.last_fetch_seq_number}"
