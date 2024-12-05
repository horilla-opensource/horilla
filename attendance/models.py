"""
models.py

This module is used to register models for recruitment app

"""

import contextlib
import datetime as dt
import json
from datetime import date, datetime, timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from attendance.methods.utils import (
    MONTH_MAPPING,
    attendance_date_validate,
    format_time,
    get_diff_dict,
    strtime_seconds,
    validate_hh_mm_ss_format,
    validate_time_format,
    validate_time_in_minutes,
)
from base.horilla_company_manager import HorillaCompanyManager
from base.methods import is_company_leave, is_holiday
from base.models import Company, EmployeeShift, EmployeeShiftDay, Holidays, WorkType
from employee.models import Employee
from horilla.methods import get_horilla_model_class
from horilla.models import HorillaModel
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog

# to skip the migration issue with the old migrations
_validate_time_in_minutes = validate_time_in_minutes


# Create your models here.


class AttendanceActivity(HorillaModel):
    """
    AttendanceActivity model
    """

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="employee_attendance_activities",
        verbose_name=_("Employee"),
    )
    attendance_date = models.DateField(
        null=True,
        validators=[attendance_date_validate],
        verbose_name=_("Attendance Date"),
    )
    shift_day = models.ForeignKey(
        EmployeeShiftDay,
        null=True,
        on_delete=models.DO_NOTHING,
        verbose_name=_("Shift Day"),
    )
    in_datetime = models.DateTimeField(null=True)
    clock_in_date = models.DateField(null=True, verbose_name=_("In Date"))
    clock_in = models.TimeField(verbose_name=_("Check In"))
    clock_out_date = models.DateField(null=True, verbose_name=_("Out Date"))
    out_datetime = models.DateTimeField(null=True)
    clock_out = models.TimeField(null=True, verbose_name=_("Check Out"))
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        """
        Meta class to add some additional options
        """

        ordering = ["-attendance_date", "employee_id__employee_first_name", "clock_in"]

    def duration(self):
        """
        Duration calc b/w in-out method
        """

        if not self.clock_out or not self.clock_out_date:
            self.clock_out_date = datetime.today().date()
            self.clock_out = datetime.now().time()

        clock_in_datetime = datetime.combine(self.clock_in_date, self.clock_in)
        clock_out_datetime = datetime.combine(self.clock_out_date, self.clock_out)

        time_difference = clock_out_datetime - clock_in_datetime

        return time_difference.total_seconds()


class BatchAttendance(HorillaModel):
    """
    Batch attendance model
    """

    title = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.title}-{self.id}"


class Attendance(HorillaModel):
    """
    Attendance model
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.first_save = True

    status = [
        ("create_request", _("Create Request")),
        ("update_request", _("Update Request")),
        ("revalidate_request", _("Re-validate Request")),
    ]

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        related_name="employee_attendances",
        verbose_name=_("Employee"),
    )
    attendance_date = models.DateField(
        null=False,
        validators=[attendance_date_validate],
        verbose_name=_("Attendance date"),
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
    attendance_day = models.ForeignKey(
        EmployeeShiftDay,
        on_delete=models.DO_NOTHING,
        null=True,
        verbose_name=_("Attendance day"),
    )
    attendance_clock_in_date = models.DateField(
        null=True, verbose_name=_("Check-In Date")
    )
    attendance_clock_in = models.TimeField(
        null=True, verbose_name=_("Check-In"), help_text=_("First Check-In Time")
    )
    attendance_clock_out_date = models.DateField(
        null=True, verbose_name=_("Check-Out Date")
    )
    attendance_clock_out = models.TimeField(
        null=True, verbose_name=_("Check-Out"), help_text=_("Last Check-Out Time")
    )
    attendance_worked_hour = models.CharField(
        null=True,
        default="00:00",
        max_length=10,
        validators=[validate_time_format],
        verbose_name=_("Worked Hours"),
    )
    minimum_hour = models.CharField(
        max_length=10,
        default="00:00",
        validators=[validate_time_format],
        verbose_name=_("Minimum hour"),
    )
    batch_attendance_id = models.ForeignKey(
        BatchAttendance,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_("Batch Attendance"),
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
    overtime_second = models.IntegerField(
        null=True, blank=True, verbose_name=_("Overtime In Second")
    )
    approved_overtime_second = models.IntegerField(default=0)
    is_validate_request = models.BooleanField(
        default=False, verbose_name=_("Is validate request")
    )
    is_bulk_request = models.BooleanField(default=False, editable=False)
    is_validate_request_approved = models.BooleanField(
        default=False, verbose_name=_("Is validate request approved")
    )
    request_description = models.TextField(null=True, max_length=255)
    request_type = models.CharField(
        max_length=18, null=True, choices=status, default="update_request"
    )
    is_holiday = models.BooleanField(default=False)
    requested_data = models.JSONField(null=True, editable=False)
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )

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

    def check_min_ot(self):
        """
        Method to check the min ot for the attendance
        """

    def is_night_shift(self):
        """
        check is night shift or not
        """
        day = self.attendance_day
        if day is None:
            return False
        schedule = day.day_schedule.filter(shift_id=self.shift_id).first()
        if not schedule:
            return False
        return schedule.is_night_shift

    def __str__(self) -> str:
        return f"{self.employee_id.employee_first_name} \
            {self.employee_id.employee_last_name} - {self.attendance_date}"

    def activities(self):
        """
        This method is used to return the activites and count of activites comes for an attendance
        """
        activities = AttendanceActivity.objects.filter(
            attendance_date=self.attendance_date, employee_id=self.employee_id
        )
        return {"query": activities, "count": activities.count()}

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

    def get_last_clock_out(self, null_activity=False):
        """
        This method is used to get the last attendance activity if exists
        """
        activities = AttendanceActivity.objects.filter(
            employee_id=self.employee_id,
            attendance_date=self.attendance_date,
            clock_out__isnull=null_activity,
        ).order_by("id")
        return activities.last()

    def get_at_work_from_activities(self):
        """
        This method is used to retun the at work calculated from the activities
        """
        activities = AttendanceActivity.objects.filter(
            attendance_date=self.attendance_date, employee_id=self.employee_id
        ).order_by("clock_in")
        at_work_seconds = 0
        now = datetime.now()
        for activity in activities:
            out_time = activity.clock_out
            if out_time is None:
                combined_out = datetime.combine(
                    now, dt.time(hour=now.hour, minute=now.minute, second=now.second)
                )
            else:
                combined_out = datetime.combine(activity.clock_out_date, out_time)
            in_time = activity.clock_in
            combined_in = datetime.combine(activity.clock_in_date, in_time)
            diffs = combined_out - combined_in
            at_work_seconds = at_work_seconds + diffs.total_seconds()
        return at_work_seconds

    def hours_pending(self):
        """
        This method will returns difference between minimum_hour and attendance_worked_hour
        """
        minimum_hours = strtime_seconds(self.minimum_hour)
        worked_hour = strtime_seconds(self.attendance_worked_hour)
        pending_seconds = minimum_hours - worked_hour
        if pending_seconds < 0:
            return "00:00"
        pending_hours = format_time(pending_seconds)
        return pending_hours

    def adjust_minimum_hour(self):
        """
        Set minimum_hour to 00:00 if the attendance date falls on a holiday or company leave.
        """
        if is_holiday(self.attendance_date) or is_company_leave(self.attendance_date):
            self.minimum_hour = "00:00"
            self.is_holiday = True

    def update_attendance_overtime(self):
        """
        Calculate and update attendance overtime and worked seconds.
        """
        self.attendance_overtime = format_time(
            max(
                0,
                (
                    strtime_seconds(self.attendance_worked_hour)
                    - strtime_seconds(self.minimum_hour)
                ),
            )
        )
        self.at_work_second = strtime_seconds(self.attendance_worked_hour)
        self.overtime_second = strtime_seconds(self.attendance_overtime)

    def handle_overtime_conditions(self):
        condition = AttendanceValidationCondition.objects.first()
        if self.is_validate_request:
            self.is_validate_request_approved = self.attendance_validated = False

        if condition:
            # Handle overtime cutoff
            if condition.overtime_cutoff:
                cutoff_seconds = strtime_seconds(condition.overtime_cutoff)
                if self.overtime_second > cutoff_seconds:
                    self.overtime_second = cutoff_seconds
                    self.attendance_overtime = format_time(cutoff_seconds)

            # Auto-approve overtime if conditions are met
            if condition.auto_approve_ot and self.overtime_second >= strtime_seconds(
                condition.minimum_overtime_to_approve
            ):
                self.attendance_overtime_approve = True

    def save(self, *args, **kwargs):
        self.update_attendance_overtime()
        self.attendance_day = EmployeeShiftDay.objects.get(
            day=self.attendance_date.strftime("%A").lower()
        )
        prev_attendance_approved = False
        self.adjust_minimum_hour()

        # Handle overtime cutoff and auto-approval
        self.handle_overtime_conditions()

        if self.pk is not None:
            # Get the previous values of the boolean field
            prev_state = Attendance.objects.get(pk=self.pk)
            prev_attendance_approved = prev_state.attendance_overtime_approve

        # super().save(*args, **kwargs)  #commend this line, it take too much time to complete
        employee_ot = self.employee_id.employee_overtime.filter(
            month=self.attendance_date.strftime("%B").lower(),
            year=self.attendance_date.year,
        ).first()
        if employee_ot:
            # Update if exists
            self.update_ot(employee_ot)
        else:
            # Create and update in one call
            employee_ot = self.create_ot()
            self.update_ot(employee_ot)
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
        self.first_save = False

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
            "shift_id": self.shift_id.id if self.shift_id else "",
            "work_type_id": self.work_type_id.id if self.work_type_id else "",
            "attendance_worked_hour": self.attendance_worked_hour,
            "minimum_hour": self.minimum_hour,
            "batch_attendance_id": (
                self.batch_attendance_id.id if self.batch_attendance_id else ""
            ),
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
            employee_ot = self.employee_id.employee_overtime.filter(
                month=self.attendance_date.strftime("%B").lower(),
                year=self.attendance_date.strftime("%Y"),
            )
        if employee_ot.exists():
            self.update_ot(employee_ot.first())
        # Call the superclass delete() method to delete the object
        super().delete(*args, **kwargs)

        # Perform additional operations after deleting the object

    def create_ot(self):
        """
        Create a new Hour Account instance if it doesn't exist for a specific month and year.
        Returns:
            AttendanceOverTime: The created or fetched AttendanceOverTime instance.
        """
        # Create or fetch the AttendanceOverTime instance
        employee_ot, created = AttendanceOverTime.objects.get_or_create(
            employee_id=self.employee_id,
            month=self.attendance_date.strftime("%B").lower(),
            year=self.attendance_date.year,
        )

        # Update only if the fields are available
        if self.attendance_overtime_approve:
            employee_ot.overtime = self.attendance_overtime

        if self.attendance_validated:
            employee_ot.hour_account = self.attendance_worked_hour

        employee_ot.save()
        return employee_ot

    def update_ot(self, employee_ot):
        """
        Update the hour account for the given employee.

        Args:
            employee_ot (obj): AttendanceOverTime instance
        """
        if apps.is_installed("leave"):
            approved_leave_requests = self.employee_id.leaverequest_set.filter(
                start_date__lte=self.attendance_date,
                end_date__gte=self.attendance_date,
                status="approved",
            )
        else:
            approved_leave_requests = []

        # Create exclude condition using Q objects
        exclude_condition = Q()
        if approved_leave_requests:
            # Combine multiple conditions for the exclude clause
            for leave in approved_leave_requests:
                exclude_condition |= Q(
                    attendance_date__range=(leave.start_date, leave.end_date)
                )

        # Filter month attendances in a single query
        month_attendances = (
            Attendance.objects.filter(
                employee_id=self.employee_id,
                attendance_date__month=self.attendance_date.month,
                attendance_date__year=self.attendance_date.year,
                attendance_validated=True,
            )
            .exclude(exclude_condition)
            .values("minimum_hour", "at_work_second")
        )

        # Calculate hour balance and hours pending in a single loop
        hour_balance = 0
        minimum_hour_second = 0
        for attendance in month_attendances:
            required_work_second = strtime_seconds(attendance["minimum_hour"])
            at_work_second = min(required_work_second, attendance["at_work_second"])
            hour_balance += at_work_second
            minimum_hour_second += required_work_second

        hours_pending = minimum_hour_second - hour_balance
        employee_ot.worked_hours = format_time(hour_balance)
        employee_ot.pending_hours = format_time(hours_pending)
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
        if (
            self.attendance_clock_out_date
            and self.attendance_clock_out_date < self.attendance_clock_in_date
        ):
            raise ValidationError(
                {
                    "attendance_clock_out_date": "Attendance check-out date never smaller than attendance check-in date"
                }
            )
        if self.attendance_clock_out_date and self.attendance_clock_out_date >= today:
            if out_time > now:
                raise ValidationError(
                    {"attendance_clock_out": "Check out time not allow in the future"}
                )


class AttendanceRequestFile(HorillaModel):
    file = models.FileField(upload_to="attendance/request_files")


class AttendanceRequestComment(HorillaModel):
    """
    AttendanceRequestComment Model
    """

    request_id = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    files = models.ManyToManyField(AttendanceRequestFile, blank=True)
    comment = models.TextField(null=True, verbose_name=_("Comment"), max_length=255)

    def __str__(self) -> str:
        return f"{self.comment}"


class AttendanceOverTime(HorillaModel):
    """
    AttendanceOverTime model
    """

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="employee_overtime",
        verbose_name=_("Employee"),
    )
    month = models.CharField(
        max_length=10,
        verbose_name=_("Month"),
    )
    month_sequence = models.PositiveSmallIntegerField(default=0)
    year = models.CharField(
        default=datetime.now().strftime("%Y"),
        null=True,
        max_length=10,
        verbose_name=_("Year"),
    )
    worked_hours = models.CharField(
        max_length=10,
        default="00:00",
        null=True,
        validators=[validate_time_format],
        verbose_name=_("Worked Hours"),
    )
    pending_hours = models.CharField(
        max_length=10,
        default="00:00",
        null=True,
        validators=[validate_time_format],
        verbose_name=_("Pending Hours"),
    )
    overtime = models.CharField(
        max_length=20,
        default="00:00",
        validators=[validate_time_format],
        verbose_name=_("Overtime Hours"),
    )
    hour_account_second = models.IntegerField(
        default=0,
        null=True,
        verbose_name=_("Worked Seconds"),
    )
    hour_pending_second = models.IntegerField(
        default=0,
        null=True,
        verbose_name=_("Pending Seconds"),
    )
    overtime_second = models.IntegerField(
        default=0,
        null=True,
        verbose_name=_("Overtime Seconds"),
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        """
        Meta class to add some additional options
        """

        unique_together = [("employee_id"), ("month"), ("year")]
        ordering = ["-year", "-month_sequence"]

    def clean(self):
        try:
            year = int(self.year)
            if not (1900 <= year <= 2100):
                raise ValidationError(
                    {"year": _("Year must be an integer value between 1900 and 2100")}
                )
        except (ValueError, TypeError):
            raise ValidationError(
                {"year": _("Year must be an integer value between 1900 and 2100")}
            )

    def month_days(self):
        """
        this method is used to create new AttendanceOvertime's instance if there
        is no existing for a specific month and year
        """
        month = self.month_sequence + 1
        year = int(self.year)
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        return start_date, end_date

    def not_validated_hrs(self):
        """
        This method will return not validated hours in a month
        """
        hrs_to_vlaidate = sum(
            list(
                Attendance.objects.filter(
                    attendance_date__month=MONTH_MAPPING[self.month],
                    attendance_date__year=self.year,
                    employee_id=self.employee_id,
                    attendance_validated=False,
                ).values_list("at_work_second", flat=True)
            )
        )
        return format_time(hrs_to_vlaidate)

    def not_approved_ot_hrs(self):
        """
        This method will return the overtime hours to be approved
        """
        hrs_to_approve = sum(
            list(
                Attendance.objects.filter(
                    attendance_date__month=MONTH_MAPPING[self.month],
                    attendance_date__year=self.year,
                    employee_id=self.employee_id,
                    attendance_validated=True,
                    attendance_overtime_approve=False,
                ).values_list("overtime_second", flat=True)
            )
        )
        return format_time(hrs_to_approve)

    def get_month_index(self):
        """
        This method will return the index of the month
        """
        return MONTH_MAPPING[self.month]

    def save(self, *args, **kwargs):
        self.hour_account_second = strtime_seconds(self.worked_hours)
        self.hour_pending_second = strtime_seconds(self.pending_hours)
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


class AttendanceLateComeEarlyOut(HorillaModel):
    """
    AttendanceLateComeEarlyOut model
    """

    choices = [
        ("late_come", _("Late Come")),
        ("early_out", _("Early Out")),
    ]

    attendance_id = models.ForeignKey(
        Attendance,
        on_delete=models.PROTECT,
        related_name="late_come_early_out",
        verbose_name=_("Attendance"),
    )
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.DO_NOTHING,
        null=True,
        related_name="late_come_early_out",
        verbose_name=_("Employee"),
        editable=False,
    )
    type = models.CharField(max_length=20, choices=choices, verbose_name=_("Type"))
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def get_penalties_count(self):
        """
        This method is used to return the total penalties in the late early instance
        """
        return self.penaltyaccounts_set.count()

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        self.employee_id = self.attendance_id.employee_id
        super().save(*args, **kwargs)

    class Meta:
        """
        Meta class to add some additional options
        """

        unique_together = [("attendance_id"), ("type")]
        ordering = ["-attendance_id__attendance_date"]

    def __str__(self) -> str:
        return f"{self.attendance_id.employee_id.employee_first_name} \
            {self.attendance_id.employee_id.employee_last_name} - {self.type}"


class AttendanceValidationCondition(HorillaModel):
    """
    AttendanceValidationCondition model
    """

    validation_at_work = models.CharField(
        max_length=10,
        validators=[validate_time_format],
        verbose_name=_("Worked Hours Auto Approve Till"),
    )
    minimum_overtime_to_approve = models.CharField(
        blank=True, null=True, max_length=10, validators=[validate_time_format]
    )
    overtime_cutoff = models.CharField(
        blank=True, null=True, max_length=10, validators=[validate_time_format]
    )
    auto_approve_ot = models.BooleanField(
        default=False, verbose_name=_("Auto Approve OT")
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

    def clean(self):
        """
        This method is used to perform some custom validations
        """
        super().clean()
        if not self.id and AttendanceValidationCondition.objects.exists():
            raise ValidationError(_("You cannot add more conditions."))


class GraceTime(HorillaModel):
    """
    Model for saving Grace time
    """

    allowed_time = models.CharField(
        default="00:00:00",
        validators=[validate_hh_mm_ss_format],
        max_length=10,
        verbose_name=_("Allowed time"),
    )
    allowed_time_in_secs = models.IntegerField()
    allowed_clock_in = models.BooleanField(
        default=True, help_text=_("Allcocate this grace time for Check-In Attendance")
    )
    allowed_clock_out = models.BooleanField(
        default=False, help_text=_("Allcocate this grace time for Check-Out Attendance")
    )
    is_default = models.BooleanField(default=False)

    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    objects = HorillaCompanyManager()

    def __str__(self) -> str:
        return str(f"{self.allowed_time} - Hours")

    def clean(self):
        """
        This method is used to perform some custom validations
        """
        super().clean()
        if self.is_default:
            if GraceTime.objects.filter(is_default=True).exclude(id=self.id).exists():
                raise ValidationError(
                    _("There is already a default grace time that exists.")
                )

        allowed_time = self.allowed_time
        is_default = self.is_default
        exclude_default = not is_default

        if (
            GraceTime.objects.filter(allowed_time=allowed_time)
            .exclude(is_default=exclude_default)
            .exclude(id=self.id)
            .exists()
        ):
            raise ValidationError(
                {
                    "allowed_time": _(
                        "There is already an existing grace time with this allowed time."
                    )
                }
            )

    def save(self, *args, **kwargs):
        allowed_time = self.allowed_time
        hours, minutes, secs = allowed_time.split(":")

        hours_int = int(hours)
        minutes_int = int(minutes)
        secs_int = int(secs)

        hours_str = f"{hours_int:02d}"
        minutes_str = f"{minutes_int:02d}"
        secs_str = f"{secs_int:02d}"

        self.allowed_time = f"{hours_str}:{minutes_str}:{secs_str}"
        self.allowed_time_in_secs = hours_int * 3600 + minutes_int * 60 + secs_int
        super().save(*args, **kwargs)


class AttendanceGeneralSetting(HorillaModel):
    """
    AttendanceGeneralSettings
    """

    time_runner = models.BooleanField(default=True)
    company_id = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)


if apps.is_installed("leave") and apps.is_installed("payroll"):

    class PenaltyAccount(HorillaModel):
        """
        LateComeEarlyOutPenaltyAccount
        """

        employee_id = models.ForeignKey(
            Employee,
            on_delete=models.PROTECT,
            related_name="penalty_set",
            editable=False,
            verbose_name="Employee",
            null=True,
        )
        late_early_id = models.ForeignKey(
            AttendanceLateComeEarlyOut,
            on_delete=models.CASCADE,
            null=True,
            editable=False,
        )
        leave_request_id = models.ForeignKey(
            "leave.LeaveRequest", null=True, on_delete=models.CASCADE, editable=False
        )
        leave_type_id = models.ForeignKey(
            "leave.LeaveType",
            on_delete=models.DO_NOTHING,
            blank=True,
            null=True,
            verbose_name="Leave type",
        )
        minus_leaves = models.FloatField(default=0.0, null=True)
        deduct_from_carry_forward = models.BooleanField(default=False)
        penalty_amount = models.FloatField(default=0.0, null=True)

        def clean(self) -> None:
            super().clean()
            if not self.leave_type_id and self.minus_leaves:
                raise ValidationError(
                    {"leave_type_id": _("Specify the leave type to deduct the leave.")}
                )
            if self.leave_type_id and not self.minus_leaves:
                raise ValidationError(
                    {
                        "minus_leaves": _(
                            "If a leave type is chosen for a penalty, minus leaves are required."
                        )
                    }
                )
            if not self.minus_leaves and not self.penalty_amount:
                raise ValidationError(
                    {
                        "leave_type_id": _(
                            "Either minus leaves or a penalty amount is required"
                        )
                    }
                )

            if (
                self.minus_leaves or self.deduct_from_carry_forward
            ) and not self.leave_type_id:
                raise ValidationError({"leave_type_id": _("Leave type is required")})
            return

        class Meta:
            ordering = ["-created_at"]

    @receiver(post_save, sender=PenaltyAccount)
    def create_initial_stage(sender, instance, created, **kwargs):
        """
        This is post save method, used to create initial stage for the recruitment
        """
        # only work when creating
        if created:
            penalty_amount = instance.penalty_amount
            if penalty_amount:
                Deduction = get_horilla_model_class(
                    app_label="payroll", model="deduction"
                )
                penalty = Deduction()
                if instance.late_early_id:
                    penalty.title = (
                        f"{instance.late_early_id.get_type_display()} penalty"
                    )
                    penalty.one_time_date = (
                        instance.late_early_id.attendance_id.attendance_date
                    )
                elif instance.leave_request_id:
                    penalty.title = (
                        f"Leave penalty {instance.leave_request_id.end_date}"
                    )
                    penalty.one_time_date = instance.leave_request_id.end_date
                else:
                    penalty.title = f"Penalty on {datetime.today()}"
                    penalty.one_time_date = datetime.today()
                penalty.include_active_employees = False
                penalty.is_fixed = True
                penalty.amount = instance.penalty_amount
                penalty.only_show_under_employee = True
                penalty.save()
                penalty.include_active_employees = False
                penalty.specific_employees.add(instance.employee_id)
                penalty.save()

            if instance.leave_type_id and instance.minus_leaves:
                available = instance.employee_id.available_leave.filter(
                    leave_type_id=instance.leave_type_id
                ).first()
                unit = round(instance.minus_leaves * 2) / 2
                if not instance.deduct_from_carry_forward:
                    available.available_days = max(0, (available.available_days - unit))
                else:
                    available.carryforward_days = max(
                        0, (available.carryforward_days - unit)
                    )

                available.save()


class WorkRecords(models.Model):
    """
    WorkRecord Model
    """

    choices = [
        ("FDP", _("Present")),
        ("HDP", _("Half Day Present")),
        ("ABS", _("Absent")),
        ("HD", _("Holiday/Company Leave")),
        ("CONF", _("Conflict")),
        ("DFT", _("Draft")),
    ]

    record_name = models.CharField(max_length=250, null=True, blank=True)
    work_record_type = models.CharField(max_length=5, null=True, choices=choices)
    employee_id = models.ForeignKey(
        Employee, on_delete=models.PROTECT, verbose_name=_("Employee")
    )
    date = models.DateField(null=True, blank=True)
    at_work = models.CharField(
        null=True,
        blank=True,
        validators=[
            validate_time_format,
        ],
        default="00:00",
        max_length=5,
    )
    min_hour = models.CharField(
        null=True,
        blank=True,
        validators=[
            validate_time_format,
        ],
        default="00:00",
        max_length=5,
    )
    at_work_second = models.IntegerField(null=True, blank=True, default=0)
    min_hour_second = models.IntegerField(null=True, blank=True, default=0)
    note = models.TextField(max_length=255)
    message = models.CharField(max_length=30, null=True, blank=True)
    is_attendance_record = models.BooleanField(default=False)
    is_leave_record = models.BooleanField(default=False)
    day_percentage = models.FloatField(default=0)
    last_update = models.DateTimeField(null=True, blank=True)
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    def title_message(self):
        title_message = self.message
        if title_message == "Absent":
            if apps.is_installed("leave"):
                LeaveRequest = get_horilla_model_class(
                    app_label="leave", model="leaverequest"
                )
                leave_type = (
                    LeaveRequest.objects.filter(
                        employee_id=self.employee_id,
                        end_date__gte=self.date,
                        start_date__lte=self.date,
                    )
                    .first()
                    .leave_type_id
                    if LeaveRequest.objects.exists()
                    else None
                )
                title_message += f" | {leave_type}"
        return title_message

    def save(self, *args, **kwargs):
        self.last_update = timezone.now()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not 0.0 <= self.day_percentage <= 1.0:
            raise ValidationError(_("Day percentage must be between 0.0 and 1.0"))

    def __str__(self):
        return (
            self.record_name
            if self.record_name is not None
            else f"{self.work_record_type}-{self.date}"
        )


class OverrideAttendances(Attendance):
    """
    Class to override Attendance model save method
    """

    # Additional fields and methods specific to AnotherModel
    @receiver(post_save, sender=Attendance)
    def attendance_post_save(sender, instance, **kwargs):
        """
        Overriding Attendance model save method
        """
        if instance.first_save:
            min_hour_second = strtime_seconds(instance.minimum_hour)
            at_work_second = strtime_seconds(instance.attendance_worked_hour)

            status = "FDP" if instance.at_work_second >= min_hour_second else "HDP"

            status = "CONF" if instance.attendance_validated is False else status
            message = (
                _("Validate the attendance") if status == "CONF" else _("Validated")
            )

            message = (
                _("Incomplete minimum hour")
                if status == "HDP" and min_hour_second > at_work_second
                else message
            )
            work_record = WorkRecords.objects.filter(
                date=instance.attendance_date,
                is_attendance_record=True,
                employee_id=instance.employee_id,
            )
            work_record = (
                WorkRecords()
                if not WorkRecords.objects.filter(
                    date=instance.attendance_date,
                    employee_id=instance.employee_id,
                ).exists()
                else WorkRecords.objects.filter(
                    date=instance.attendance_date,
                    employee_id=instance.employee_id,
                ).first()
            )
            work_record.employee_id = instance.employee_id
            work_record.date = instance.attendance_date
            work_record.at_work = instance.attendance_worked_hour
            work_record.min_hour = instance.minimum_hour
            work_record.min_hour_second = min_hour_second
            work_record.at_work_second = at_work_second
            work_record.work_record_type = status
            work_record.message = message
            work_record.is_attendance_record = True
            if instance.attendance_validated:
                work_record.day_percentage = (
                    1.00 if at_work_second > min_hour_second / 2 else 0.50
                )
            work_record.save()

            if status == "HDP" and work_record.is_leave_record:
                message = _("Half day leave")
            elif status == "FDP" and work_record.is_leave_record:
                message = _("An approved leave exists")
            elif status == "FDP":
                message = _("Present")

            work_record.message = message
            work_record.save()

            message = work_record.message
            status = work_record.work_record_type
            if not instance.attendance_clock_out:
                status = "FDP"
                message = _("Currently working")
            work_record.message = message
            work_record.work_record_type = status
            work_record.save()

    @receiver(pre_delete, sender=Attendance)
    def attendance_pre_delete(sender, instance, **_kwargs):
        """
        Overriding Attendance model delete method
        """
        # Perform any actions before deleting the instance
        # ...
        WorkRecords.objects.filter(
            employee_id=instance.employee_id,
            is_attendance_record=True,
            date=instance.attendance_date,
        ).delete()
