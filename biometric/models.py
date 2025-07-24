# pylint: disable=too-few-public-methods
"""
This module contains Django models for managing biometric devices
and employee attendance within a company.
"""

import uuid

import requests
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from employee.models import Employee
from horilla.models import HorillaModel


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
        ("zk", _("ZKTeco / eSSL Biometric")),
        ("anviz", _("Anviz Biometric")),
        ("cosec", _("Matrix COSEC Biometric")),
        ("dahua", _("Dahua Biometric")),
        ("etimeoffice", _("e-Time Office")),
    ]
    BIO_DEVICE_DIRECTION = [
        ("in", _("In Device")),
        ("out", _("Out Device")),
        ("alternate", _("Alternate In/Out Device")),
        ("system", _("System Direction(In/Out) Device")),
    ]
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    machine_type = models.CharField(
        max_length=18, choices=BIO_DEVICE_TYPE, null=True, verbose_name=_("Device Type")
    )
    machine_ip = models.CharField(
        max_length=150, null=True, blank=True, default="", verbose_name=_("Machine IP")
    )
    port = models.IntegerField(null=True, blank=True, verbose_name=_("Port No"))
    zk_password = models.CharField(
        max_length=100, null=True, blank=True, default="0", verbose_name=_("Password")
    )
    bio_username = models.CharField(
        max_length=100, null=True, blank=True, default="", verbose_name=_("Username")
    )
    bio_password = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Password")
    )
    anviz_request_id = models.CharField(
        max_length=200, null=True, blank=True, verbose_name=_("Request ID")
    )
    api_url = models.CharField(
        max_length=200, null=True, blank=True, verbose_name=_("API Url")
    )
    api_key = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("API Key")
    )
    api_secret = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("API Secret")
    )
    api_token = models.CharField(max_length=500, null=True, blank=True)
    api_expires = models.CharField(max_length=100, null=True, blank=True)
    is_live = models.BooleanField(default=False, verbose_name=_("Is Live"))
    is_scheduler = models.BooleanField(default=False, verbose_name=_("Is Scheduled"))
    scheduler_duration = models.CharField(
        null=True,
        default="00:00",
        max_length=10,
        validators=[validate_schedule_time_format],
    )
    last_fetch_date = models.DateField(null=True, blank=True)
    last_fetch_time = models.TimeField(null=True, blank=True)
    device_direction = models.CharField(
        max_length=50,
        choices=BIO_DEVICE_DIRECTION,
        default="system",
        verbose_name=_("Device Direction"),
    )
    company_id = models.ForeignKey(
        Company,
        null=True,
        editable=True,
        on_delete=models.PROTECT,
        verbose_name=_("Company"),
    )

    objects = HorillaCompanyManager()

    def __str__(self):
        return f"{self.name} - {self.machine_type}"

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        required_fields = {}

        if self.machine_type in ("zk", "cosec", "dahua"):
            if not self.machine_ip:
                required_fields["machine_ip"] = _(
                    "The Machine IP is required for the selected biometric device."
                )
            if not self.port:
                required_fields["port"] = _(
                    "The Port Number is required for the selected biometric device."
                )

        if self.machine_type == "zk":
            if not self.zk_password:
                required_fields["zk_password"] = _(
                    "The password is required for ZKTeco Biometric Device."
                )
            else:
                try:
                    int(self.zk_password)
                except ValueError:
                    required_fields["zk_password"] = _(
                        "The password must be an integer (numeric) value for\
                            ZKTeco Biometric Device."
                    )

        if self.machine_type in ("cosec", "dahua"):
            if not self.bio_username:
                required_fields["bio_username"] = _(
                    "The Username is required for the selected biometric device."
                )
            if not self.bio_password:
                required_fields["bio_password"] = _(
                    "The Password is required for the selected biometric device."
                )

        if self.machine_type == "anviz":
            if not self.anviz_request_id:
                required_fields["anviz_request_id"] = _(
                    "The Request ID is required for the Anviz Biometric Device."
                )
            if not self.api_url:
                required_fields["api_url"] = _(
                    "The API URL is required for Anviz Biometric Device."
                )
            if not self.api_key:
                required_fields["api_key"] = _(
                    "The API Key is required for Anviz Biometric Device."
                )
            if not self.api_secret:
                required_fields["api_secret"] = _(
                    "The API Secret is required for Anviz Biometric Device."
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
        if required_fields:
            raise ValidationError(required_fields)

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
    user_id = models.CharField(max_length=100, verbose_name=_("User ID"))
    dahua_card_no = models.CharField(max_length=100, null=True, blank=True)
    employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name=_("Employee")
    )
    device_id = models.ForeignKey(
        BiometricDevices, on_delete=models.CASCADE, null=True, blank=True
    )
    objects = models.Manager()

    def __str__(self):
        return f"{self.employee_id} - {self.user_id} - {self.device_id}"

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

    class Meta:
        verbose_name = _("COSEC Attendance Arguments")
        verbose_name_plural = _("COSEC Attendance Arguments")

    def __str__(self):
        return f"{self.device_id} - {self.last_fetch_roll_ovr_count} - {self.last_fetch_seq_number}"
