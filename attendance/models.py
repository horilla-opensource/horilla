"""
models.py

This module is used to register models for recruitment app

"""
import json
import contextlib
from datetime import datetime
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from base.models import EmployeeShift, EmployeeShiftDay, WorkType
from employee.models import Employee
from attendance.methods.differentiate import get_diff_dict

# Create your models here.


def strtime_seconds(time):
    """
    this method is used to reconvert time in H:M formate string back to seconds and return it
    args:
        time : time in H:M format
    """
    ftr = [3600, 60, 1]
    return sum(a * b for a, b in zip(ftr, map(int, time.split(":"))))


def format_time(seconds):
    """
    This method is used to formate seconds to H:M and return it
    args:
        seconds : seconds
    """
    hour = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int((seconds % 3600) % 60)
    return f"{hour:02d}:{minutes:02d}"


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
            raise ValidationError(_("Invalid time"))
    except ValueError as error:
        raise ValidationError(_("Invalid format")) from error


def attendance_date_validate(date):
    """
    Validates if the provided date is not a future date.

    :param date: The date to validate.
    :raises ValidationError: If the provided date is in the future.
    """
    today = datetime.today().date()
    if date > today:
        raise ValidationError(_("You cannot choose a future date."))


class AttendanceActivity(models.Model):
    """
    AttendanceActivity model
    """

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee_attendance_activities",
        verbose_name=_("Employee"),
    )
    attendance_date = models.DateField(null=True, validators=[attendance_date_validate])
    clock_in_date = models.DateField(null=True)
    shift_day = models.ForeignKey(
        EmployeeShiftDay, null=True, on_delete=models.DO_NOTHING
    )
    clock_in = models.TimeField()
    clock_out = models.TimeField(null=True)
    clock_out_date = models.DateField(null=True)

    class Meta:
        """
        Meta class to add some additional options
        """

        ordering = ["-attendance_date", "employee_id__employee_first_name", "clock_in"]


class Attendance(models.Model):
    """
    Attendance model_
    """

    status = [
        ("create_request", _("Create Request")),
        ("update_request", _("Update Request")),
        ("revalidate_request", _("Re-validate Request")),
    ]

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        related_name="employee_attendances",
        verbose_name=_("Employee"),
    )
    shift_id = models.ForeignKey(
        EmployeeShift, on_delete=models.DO_NOTHING, null=True, verbose_name=_("Shift")
    )
    work_type_id = models.ForeignKey(
        WorkType,
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Work Type"),
    )
    attendance_date = models.DateField(
        null=False,
        validators=[attendance_date_validate],
        verbose_name=_("Attendance date"),
    )
    attendance_day = models.ForeignKey(
        EmployeeShiftDay, on_delete=models.DO_NOTHING, null=True
    )
    attendance_clock_in = models.TimeField(
        null=True, verbose_name=_("Check-in"), help_text=_("First Check-in Time")
    )
    attendance_clock_in_date = models.DateField(
        null=True, verbose_name=_("Check-in date")
    )
    attendance_clock_out = models.TimeField(
        null=True, verbose_name=_("Check-out"), help_text=_("Last Check-out Time")
    )
    attendance_clock_out_date = models.DateField(
        null=True, verbose_name=_("Check-out date")
    )
    attendance_worked_hour = models.CharField(
        null=True,
        default="00:00",
        max_length=10,
        validators=[validate_time_format],
        verbose_name=_("At work"),
    )
    minimum_hour = models.CharField(
        max_length=10,
        default="00:00",
        validators=[validate_time_format],
        verbose_name=_("Minimum hour"),
    )
    attendance_overtime = models.CharField(
        default="00:00",
        validators=[validate_time_format],
        max_length=10,
        verbose_name=_("Overtime"),
    )
    attendance_overtime_approve = models.BooleanField(
        default=False, verbose_name=_("Overtime approved")
    )
    attendance_validated = models.BooleanField(
        default=False, verbose_name=_("Attendance validated")
    )
    at_work_second = models.IntegerField(null=True, blank=True)
    overtime_second = models.IntegerField(null=True, blank=True)
    approved_overtime_second = models.IntegerField(default=0)
    objects = models.Manager()
    is_validate_request = models.BooleanField(
        default=False, verbose_name=_("Is validate request")
    )
    is_validate_request_approved = models.BooleanField(
        default=False, verbose_name=_("Is validate request approved")
    )
    request_description = models.TextField(null=True)
    request_type = models.CharField(
        max_length=18, null=True, choices=status, default="update_request"
    )
    requested_data = models.JSONField(null=True, editable=False)

    class Meta:
        """
        Meta class to add some additional options
        """

        unique_together = ("employee_id", "attendance_date")
        permissions = [
            ("change_validateattendance", "Validate Attendance"),
            ("change_approveovertime", "Change Approve Overtime"),
        ]
        ordering = [
            "-attendance_date",
            "employee_id__employee_first_name",
            "attendance_clock_in",
        ]

    def __str__(self) -> str:
        return f"{self.employee_id.employee_first_name} \
            {self.employee_id.employee_last_name} - {self.attendance_date}"

    def requested_fields(self):
        """
        This method will returns the value difference fields
        """
        keys = []
        if self.requested_data is not None:
            data = json.loads(self.requested_data)
            diffs = get_diff_dict(self.serialize(), data)
            keys = diffs.keys()
        return keys

    # return f"Attendance ID: {self.id}"  # Adjust the representation as needed

    def save(self, *args, **kwargs):
        minimum_hour = self.minimum_hour
        self_at_work = self.attendance_worked_hour
        self.attendance_overtime = format_time(
            max(0, (strtime_seconds(self_at_work) - strtime_seconds(minimum_hour)))
        )
        self_overtime = self.attendance_overtime

        self.at_work_second = strtime_seconds(self_at_work)
        self.overtime_second = strtime_seconds(self_overtime)
        self.attendance_day = EmployeeShiftDay.objects.get(
            day=self.attendance_date.strftime("%A").lower()
        )
        prev_attendance_approved = False

        condition = AttendanceValidationCondition.objects.first()
        if condition is not None:
            overtime_cutoff = condition.overtime_cutoff
            cutoff_seconds = strtime_seconds(overtime_cutoff)
            overtime = self.overtime_second
            if overtime > cutoff_seconds:
                self.overtime_second = cutoff_seconds
                self_overtime = format_time(cutoff_seconds)

        if self.pk is not None:
            # Get the previous values of the boolean field
            prev_state = Attendance.objects.get(pk=self.pk)
            prev_attendance_approved = prev_state.attendance_overtime_approve

        super().save(*args, **kwargs)
        employee_ot = self.employee_id.employee_overtime.filter(
            month=self.attendance_date.strftime("%B").lower(),
            year=self.attendance_date.strftime("%Y"),
        )
        if employee_ot.exists():
            self.update_ot(employee_ot.first())
        else:
            self.create_ot()
        approved = self.attendance_overtime_approve
        attendance_account = self.employee_id.employee_overtime.filter(
            month=self.attendance_date.strftime("%B").lower(),
            year=self.attendance_date.year,
        ).first()
        total_ot_seconds = attendance_account.overtime_second
        if approved and prev_attendance_approved is False:
            self.approved_overtime_second = self.overtime_second
            total_ot_seconds = total_ot_seconds + self.approved_overtime_second
        elif not approved:
            total_ot_seconds = total_ot_seconds - self.approved_overtime_second
            self.approved_overtime_second = 0
        attendance_account.overtime = format_time(total_ot_seconds)
        attendance_account.save()
        super().save(*args, **kwargs)

    def serialize(self):
        """
        Used to serialize attendance instance
        """
        # Return a dictionary containing the data you want to store
        # strftime("%d %b %Y") date
        # strftime("%I:%M %p") time
        serialized_data = {
            "employee_id": self.employee_id.id,
            "attendance_date": str(self.attendance_date),
            "attendance_clock_in_date": str(self.attendance_clock_in_date),
            "attendance_clock_in": str(self.attendance_clock_in),
            "attendance_clock_out": str(self.attendance_clock_out),
            "attendance_clock_out_date": str(self.attendance_clock_out_date),
            "shift_id": self.shift_id.id,
            "work_type_id": self.work_type_id.id,
            "attendance_worked_hour": self.attendance_worked_hour,
            "minimum_hour": self.minimum_hour,
            # Add other fields you want to store
        }
        return serialized_data

    def delete(self, *args, **kwargs):
        # Custom delete logic
        # Perform additional operations before deleting the object
        with contextlib.suppress(Exception):
            AttendanceActivity.objects.filter(
                attendance_date=self.attendance_date, employee_id=self.employee_id
            ).delete()
        # Call the superclass delete() method to delete the object
        super().delete(*args, **kwargs)

        # Perform additional operations after deleting the object

    def create_ot(self):
        """
        this method is used to create new AttendanceOvertime's instance if there
        is no existing for a specific month and year
        """
        employee_ot = AttendanceOverTime()
        employee_ot.employee_id = self.employee_id
        employee_ot.month = self.attendance_date.strftime("%B").lower()
        employee_ot.year = self.attendance_date.year
        if self.attendance_overtime_approve:
            employee_ot.overtime = self.attendance_overtime
        if self.attendance_validated:
            employee_ot.hour_account = self.attendance_worked_hour
        employee_ot.save()
        return self

    def update_ot(self, employee_ot):
        """
        This method is used to update the overtime

        Args:
            employee_ot (obj): AttendanceOverTime instance
        """
        month_attendances = Attendance.objects.filter(
            employee_id=self.employee_id,
            attendance_date__month=self.attendance_date.month,
            attendance_date__year=self.attendance_date.year,
            attendance_validated=True,
        )
        hour_balance = 0
        for attendance in month_attendances:
            hour_balance = hour_balance + attendance.at_work_second
        employee_ot.hour_account = format_time(hour_balance)
        employee_ot.save()
        return employee_ot

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        now = datetime.now().time()
        today = datetime.today().date()
        out_time = self.attendance_clock_out
        if self.attendance_clock_in_date < self.attendance_date:
            raise ValidationError(
                {
                    "attendance_clock_in_date": "Attendance check-in date never smaller than attendance date"
                }
            )
        if self.attendance_clock_out_date < self.attendance_clock_in_date:
            raise ValidationError(
                {
                    "attendance_clock_out_date": "Attendance check-out date never smaller than attendance check-in date"
                }
            )
        if self.attendance_clock_out_date >= today:
            if out_time > now:
                raise ValidationError(
                    {"attendance_clock_out": "Check out time not allow in the future"}
                )


class AttendanceOverTime(models.Model):
    """
    AttendanceOverTime model
    """

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee_overtime",
        verbose_name=_("Employee"),
    )
    month = models.CharField(max_length=10)
    month_sequence = models.PositiveSmallIntegerField(default=0)
    year = models.CharField(
        default=datetime.now().strftime("%Y"), null=True, max_length=10
    )
    hour_account = models.CharField(
        max_length=10, default="00:00", null=True, validators=[validate_time_format]
    )
    overtime = models.CharField(
        max_length=20, default="00:00", validators=[validate_time_format]
    )
    hour_account_second = models.IntegerField(
        default=0,
        null=True,
    )
    overtime_second = models.IntegerField(
        default=0,
        null=True,
    )

    class Meta:
        """
        Meta class to add some additional options
        """

        unique_together = [("employee_id"), ("month"), ("year")]
        ordering = ["-year", "-month_sequence"]

    def save(self, *args, **kwargs):
        self.hour_account_second = strtime_seconds(self.hour_account)
        self.overtime_second = strtime_seconds(self.overtime)
        month_name = self.month.split("-")[0]
        months = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        self.month_sequence = months.index(month_name)
        super().save(*args, **kwargs)


class AttendanceLateComeEarlyOut(models.Model):
    """
    AttendanceLateComeEarlyOut model
    """

    choices = [
        ("late_come", _("Late Come")),
        ("early_out", _("Early Out")),
    ]

    attendance_id = models.ForeignKey(
        Attendance, on_delete=models.CASCADE, related_name="late_come_early_out"
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        null=True,
        related_name="late_come_early_out",
        verbose_name=_("Employee"),
    )
    type = models.CharField(max_length=20, choices=choices)

    class Meta:
        """
        Meta class to add some additional options
        """

        unique_together = [("attendance_id"), ("type")]

    def __str__(self) -> str:
        return f"{self.attendance_id.employee_id.employee_first_name} \
            {self.attendance_id.employee_id.employee_last_name} - {self.type}"


class AttendanceValidationCondition(models.Model):
    """
    AttendanceValidationCondition model
    """

    validation_at_work = models.CharField(
        default="09:00", max_length=10, validators=[validate_time_format]
    )
    minimum_overtime_to_approve = models.CharField(
        default="00:30", null=True, max_length=10, validators=[validate_time_format]
    )
    overtime_cutoff = models.CharField(
        default="02:00", null=True, max_length=10, validators=[validate_time_format]
    )

    def clean(self):
        """
        This method is used to perform some custom validations
        """
        super().clean()
        if not self.id and AttendanceValidationCondition.objects.exists():
            raise ValidationError(_("You cannot add more conditions."))
