import calendar
import logging
import math
import operator
import threading
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.methods import get_date_range
from base.models import (
    Company,
    CompanyLeaves,
    Department,
    Holidays,
    JobPosition,
    MultipleApprovalCondition,
    clear_messages,
)
from employee.models import Employee, EmployeeWorkInformation
from horilla import horilla_middlewares
from horilla.methods import get_horilla_model_class
from horilla.models import HorillaModel
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from leave.methods import calculate_requested_days
from leave.threading import LeaveClashThread

logger = logging.getLogger(__name__)

operator_mapping = {
    "equal": operator.eq,
    "notequal": operator.ne,
    "lt": operator.lt,
    "gt": operator.gt,
    "le": operator.le,
    "ge": operator.ge,
    "icontains": operator.contains,
}
# Create your models here.
BREAKDOWN = [
    ("full_day", _("Full Day")),
    ("first_half", _("First Half")),
    ("second_half", _("Second Half")),
]
CHOICES = [("yes", "Yes"), ("no", "No")]

RESET_BASED = [
    ("yearly", _("Yearly")),
    ("monthly", _("Monthly")),
    ("weekly", _("Weekly")),
]
MONTHS = [
    ("1", _("Jan")),
    ("2", _("Feb")),
    ("3", _("Mar")),
    ("4", _("Apr")),
    ("5", _("May")),
    ("6", _("Jun")),
    ("7", _("Jul")),
    ("8", _("Aug")),
    ("9", _("Sep")),
    ("10", _("Oct")),
    ("11", _("Nov")),
    ("12", _("Dec")),
]

DAYS = [
    ("last day", _("Last Day")),
    ("1", "1st"),
    ("2", "2nd"),
    ("3", "3rd"),
    ("4", "4th"),
    ("5", "5th"),
    ("6", "6th"),
    ("7", "7th"),
    ("8", "8th"),
    ("9", "9th"),
    ("10", "10th"),
    ("11", "11th"),
    ("12", "12th"),
    ("13", "13th"),
    ("14", "14th"),
    ("15", "15th"),
    ("16", "16th"),
    ("17", "17th"),
    ("18", "18th"),
    ("19", "19th"),
    ("20", "20th"),
    ("21", "21th"),
    ("22", "22th"),
    ("23", "23th"),
    ("24", "24th"),
    ("25", "25th"),
    ("26", "26th"),
    ("27", "27th"),
    ("28", "28th"),
    ("29", "29th"),
    ("30", "30th"),
    ("31", "31th"),
]


TIME_PERIOD = [("day", _("Day")), ("month", _("Month")), ("year", _("Year"))]

PAYMENT = [("paid", _("Paid")), ("unpaid", _("Unpaid"))]

CARRYFORWARD_TYPE = [
    ("no carryforward", _("No Carry Forward")),
    ("carryforward", _("Carry Forward")),
    ("carryforward expire", _("Carry Forward with Expire")),
]

ACCRUAL_PLAN = [("job_position", _("Job Position")), ("job_role", _("Job Role"))]


LEAVE_STATUS = (
    ("requested", _("Requested")),
    ("approved", _("Approved")),
    ("cancelled", _("Cancelled")),
    ("rejected", _("Rejected")),
)

LEAVE_ALLOCATION_STATUS = (
    ("requested", _("Requested")),
    ("approved", _("Approved")),
    ("rejected", _("Rejected")),
)

WEEKS = [
    ("0", _("First Week")),
    ("1", _("Second Week")),
    ("2", _("Third Week")),
    ("3", _("Fourth Week")),
    ("4", _("Fifth Week")),
]


WEEK_DAYS = [
    ("0", _("Monday")),
    ("1", _("Tuesday")),
    ("2", _("Wednesday")),
    ("3", _("Thursday")),
    ("4", _("Friday")),
    ("5", _("Saturday")),
    ("6", _("Sunday")),
]


class LeaveType(HorillaModel):
    icon = models.ImageField(null=True, blank=True, upload_to="leave/leave_icon")
    name = models.CharField(max_length=30, null=False)
    color = models.CharField(null=True, max_length=30)
    payment = models.CharField(max_length=30, choices=PAYMENT, default="unpaid")
    count = models.FloatField(null=True, default=1)
    period_in = models.CharField(max_length=30, choices=TIME_PERIOD, default="day")
    limit_leave = models.BooleanField(default=True)
    total_days = models.FloatField(null=True, default=1)
    reset = models.BooleanField(default=False)
    is_encashable = models.BooleanField(default=False, verbose_name=_("Is encashable"))
    reset_based = models.CharField(
        max_length=30,
        choices=RESET_BASED,
        blank=True,
        null=True,
    )
    reset_month = models.CharField(max_length=30, choices=MONTHS, blank=True)
    reset_day = models.CharField(max_length=30, choices=DAYS, null=True, blank=True)
    reset_weekend = models.CharField(
        max_length=10, null=True, blank=True, choices=WEEK_DAYS
    )
    carryforward_type = models.CharField(
        max_length=30, choices=CARRYFORWARD_TYPE, default="no carryforward"
    )
    carryforward_max = models.FloatField(null=True, blank=True)
    carryforward_expire_in = models.IntegerField(null=True, blank=True)
    carryforward_expire_period = models.CharField(
        max_length=30, choices=TIME_PERIOD, null=True, blank=True
    )
    require_approval = models.CharField(
        max_length=30, choices=CHOICES, null=True, blank=True, default="yes"
    )
    require_attachment = models.CharField(
        max_length=30,
        choices=CHOICES,
        default="no",
        null=True,
        blank=True,
        verbose_name=_("Require Attachment"),
    )
    exclude_company_leave = models.CharField(
        max_length=30, choices=CHOICES, default="no"
    )
    exclude_holiday = models.CharField(max_length=30, choices=CHOICES, default="no")
    is_compensatory_leave = models.BooleanField(default=False)
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        ordering = ["-id"]

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
        if self.icon:
            full_filename = self.icon.name

            if default_storage.exists(full_filename):
                url = self.icon.url
        return url

    def leave_type_next_reset_date(self):
        today = datetime.now().date()

        if not self.reset:
            return None

        def get_reset_day(month, day):
            return (
                calendar.monthrange(today.year, month)[1]
                if day == "last day"
                else int(day)
            )

        if self.reset_based == "yearly":
            month, day = int(self.reset_month), get_reset_day(
                int(self.reset_month), self.reset_day
            )
            reset_date = datetime(
                today.year + (datetime(today.year, month, day).date() < today),
                month,
                day,
            ).date()

        elif self.reset_based == "monthly":
            month = today.month
            reset_date = datetime(
                today.year, month, get_reset_day(month, self.reset_day)
            ).date()
            if reset_date < today:
                month = (month % 12) + 1
                year = today.year + (month == 1)
                reset_date = datetime(
                    year, month, get_reset_day(month, self.reset_day)
                ).date()

        elif self.reset_based == "weekly":
            target_weekday = WEEK_DAYS[self.reset_day]
            days_until_reset = (target_weekday - today.weekday()) % 7 or 7
            reset_date = today + timedelta(days=days_until_reset)

        else:
            reset_date = None

        return reset_date

    def clean(self, *args, **kwargs):
        if self.is_compensatory_leave:
            if LeaveType.objects.filter(is_compensatory_leave=True).count() >= 1:
                raise ValidationError(_("Compensatory Leave Request already exists."))

    def save(self, *args, **kwargs):
        if (
            self.carryforward_type != "no carryforward"
            and self.carryforward_max is None
        ):
            self.carryforward_max = math.inf
        if self.pk and LeaveType.objects.get(id=self.pk).is_compensatory_leave:
            self.is_compensatory_leave = True
        super().save()

    def __str__(self):
        return self.name


class Holiday(HorillaModel):
    name = models.CharField(max_length=30, null=False, verbose_name=_("Name"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End Date"))
    recurring = models.BooleanField(default=False, verbose_name=_("Recurring"))
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager(related_company_field="company_id")

    def __str__(self):
        return self.name


class CompanyLeave(HorillaModel):
    based_on_week = models.CharField(
        max_length=100, choices=WEEKS, blank=True, null=True
    )
    based_on_week_day = models.CharField(max_length=100, choices=WEEK_DAYS)
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        unique_together = ("based_on_week", "based_on_week_day")

    def __str__(self):
        return f"{dict(WEEK_DAYS).get(self.based_on_week_day)} | {dict(WEEKS).get(self.based_on_week)}"


from django.db.models import Sum


class AvailableLeave(HorillaModel):
    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="available_leave",
        verbose_name=_("Employee"),
    )
    leave_type_id = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="employee_available_leave",
        blank=True,
        null=True,
        verbose_name=_("Leave type"),
    )
    available_days = models.FloatField(default=0, verbose_name=_("Available Days"))
    carryforward_days = models.FloatField(
        default=0, verbose_name=_("Carryforward Days")
    )
    total_leave_days = models.FloatField(default=0, verbose_name=_("Total Leave Days"))
    assigned_date = models.DateField(
        default=timezone.now, verbose_name=_("Assigned Date")
    )
    reset_date = models.DateField(
        blank=True, null=True, verbose_name=_("Leave Reset Date")
    )
    expired_date = models.DateField(
        blank=True, null=True, verbose_name=_("CarryForward Expired Date")
    )
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
        unique_together = ("leave_type_id", "employee_id")

    def __str__(self):
        return f"{self.employee_id} | {self.leave_type_id}"

    def forcasted_leaves(self, date):
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").date()
        next_reset_date = self.leave_type_id.leave_type_next_reset_date()
        if next_reset_date and next_reset_date <= date:
            return self.leave_type_id.total_days

        return 0

    # Resetting carryforward days

    def update_carryforward(self):
        if self.leave_type_id.carryforward_type != "no carryforward":
            if self.leave_type_id.carryforward_max >= self.total_leave_days:
                self.carryforward_days = self.total_leave_days
            else:
                self.carryforward_days = self.leave_type_id.carryforward_max
        self.available_days = self.leave_type_id.total_days

    # Setting the reset date for carryforward leaves

    def set_reset_date(self, assigned_date, available_leave):
        if available_leave.leave_type_id.reset_based == "monthly":
            reset_day = available_leave.leave_type_id.reset_day
            if reset_day == "last day":
                temp_date = assigned_date + relativedelta(months=0, day=31)
                if assigned_date < temp_date:
                    reset_date = temp_date
                else:
                    reset_date = assigned_date + relativedelta(months=1, day=31)

            else:
                temp_date = assigned_date + relativedelta(months=0, day=int(reset_day))
                if assigned_date < temp_date:
                    reset_date = temp_date
                else:
                    reset_date = assigned_date + relativedelta(
                        months=1, day=int(reset_day)
                    )

        elif available_leave.leave_type_id.reset_based == "weekly":
            temp = 7 - (
                assigned_date.isoweekday()
                - int(available_leave.leave_type_id.reset_weekend)
                - 1
            )
            if temp != 7:
                reset_date = assigned_date + relativedelta(days=(temp % 7))
            else:
                reset_date = assigned_date + relativedelta(days=7)
        else:
            reset_month = int(available_leave.leave_type_id.reset_month)
            reset_day = available_leave.leave_type_id.reset_day

            if reset_day == "last day":
                temp_date = assigned_date + relativedelta(
                    years=0, month=reset_month, day=31
                )
                if assigned_date < temp_date:
                    reset_date = temp_date
                else:
                    reset_date = assigned_date + relativedelta(
                        years=1, month=reset_month, day=31
                    )
            else:
                temp_date = assigned_date + relativedelta(
                    years=0, month=reset_month, day=int(reset_day)
                )
                if assigned_date < temp_date:
                    reset_date = temp_date
                else:
                    # nth_day = int(reset_day)
                    reset_date = assigned_date + relativedelta(
                        years=1, month=reset_month, day=int(reset_day)
                    )

        return reset_date

    def leave_taken(self):
        leave_taken = LeaveRequest.objects.filter(
            leave_type_id=self.leave_type_id,
            employee_id=self.employee_id,
            status="approved",
        ).aggregate(total_sum=Sum("requested_days"))

        return leave_taken["total_sum"] if leave_taken["total_sum"] else 0

    # Setting the expiration date for carryforward leaves
    def set_expired_date(self, available_leave, assigned_date):
        period = available_leave.leave_type_id.carryforward_expire_in
        if available_leave.leave_type_id.carryforward_expire_period == "day":
            expired_date = assigned_date + relativedelta(days=period)
        elif available_leave.leave_type_id.carryforward_expire_period == "month":
            expired_date = assigned_date + relativedelta(months=period)
        else:
            expired_date = assigned_date + relativedelta(years=period)

        available_leave.carryforward_days = 0
        available_leave.available_days = available_leave.leave_type_id.total_days
        return expired_date

    def save(self, *args, **kwargs):
        # if self.assigned_date == datetime.now().date() or self.assigned_date.date() == datetime.now().date():
        if self.reset_date is None:
            # Check whether the reset is enabled
            if self.leave_type_id.reset:
                reset_date = self.set_reset_date(
                    assigned_date=self.assigned_date, available_leave=self
                )
                self.reset_date = reset_date
            # assigning expire date
            if self.leave_type_id.carryforward_type == "carryforward expire":
                expired_date = self.set_expired_date(
                    assigned_date=self.assigned_date, available_leave=self
                )
                self.expired_date = expired_date

        self.total_leave_days = max(self.available_days + self.carryforward_days, 0)
        self.carryforward_days = max(self.carryforward_days, 0)
        super().save(*args, **kwargs)


def restrict_leaves(restri):

    restricted_dates = []
    restricted_days = RestrictLeave.objects.filter(id=restri)
    for i in restricted_days:
        restrict_start_date = i.start_date
        restrict_end_date = i.end_date
        total_days = restrict_end_date - restrict_start_date
        for i in range(total_days.days + 1):
            date = restrict_start_date + timedelta(i)
            restricted_dates.append(date)
    return restricted_dates


class LeaveRequest(HorillaModel):
    employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name=_("Employee")
    )
    leave_type_id = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, verbose_name=_("Leave Type")
    )
    start_date = models.DateField(null=False, verbose_name=_("Start Date"))
    start_date_breakdown = models.CharField(
        max_length=30,
        choices=BREAKDOWN,
        default="full_day",
        verbose_name=_("Start Date Breakdown"),
    )
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End Date"))
    end_date_breakdown = models.CharField(
        max_length=30,
        choices=BREAKDOWN,
        default="full_day",
        verbose_name=_("End Date Breakdown"),
    )
    requested_days = models.FloatField(
        blank=True, null=True, verbose_name=_("Requested Days")
    )
    leave_clashes_count = models.IntegerField(
        default=0, verbose_name=_("Leave Clashes Count")
    )
    description = models.TextField(verbose_name=_("Description"), max_length=255)
    attachment = models.FileField(
        null=True,
        blank=True,
        upload_to="leave/leave_attachment",
        verbose_name=_("Attachment"),
    )
    status = models.CharField(
        max_length=30,
        choices=LEAVE_STATUS,
        default="requested",
        verbose_name=_("Status"),
    )
    requested_date = models.DateField(
        default=timezone.now, verbose_name=_("Created Date")
    )
    approved_available_days = models.FloatField(default=0)
    approved_carryforward_days = models.FloatField(default=0)
    reject_reason = models.TextField(
        blank=True, verbose_name=_("Reject Reason"), max_length=255
    )
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="leave_request_created",
        verbose_name=_("Created By"),
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        ordering = ["-id"]

    def tracking(self):
        return get_diff(self)

    def __str__(self):
        return f"{self.employee_id} | {self.leave_type_id} | {self.status}"

    def employees_on_leave_today(today=None, status=None):
        """
        Retrieve employees who are on leave on a given date (default is today).

        Args:
            today (date, optional): The date to check. Defaults to the current date
                                    in the server's local timezone.
            status (str, optional): The status to filter leave requests. If None, no filtering by status is applied.

        Returns:
            QuerySet: A queryset of LeaveRequest instances where employees are on leave on the specified date.
        """
        today = date.today() if today is None else today
        queryset = LeaveRequest.objects.filter(
            start_date__lte=today, end_date__gte=today
        )

        if status is not None:
            queryset = queryset.filter(status=status)

        return queryset

    def get_penalties_count(self):
        """
        This method is used to return the total penalties in the late early instance
        """
        return self.penaltyaccounts_set.count()

    def requested_dates(self):
        """
        :return: this functions returns a list of dates from start date to end date.
        """
        request_start_date = self.start_date
        request_end_date = self.end_date
        if request_end_date is None:
            request_end_date = self.start_date
        requested_days = request_end_date - request_start_date
        requested_dates = []
        for i in range(requested_days.days + 1):
            date = request_start_date + timedelta(i)
            requested_dates.append(date)
        return requested_dates

    def holiday_dates(self):
        """
        :return: this functions returns a list of all holiday dates.
        """
        holiday_dates = []
        holidays = Holidays.objects.all()
        for holiday in holidays:
            holiday_start_date = holiday.start_date
            holiday_end_date = holiday.end_date
            if holiday_end_date is None:
                holiday_end_date = holiday_start_date
            holiday_days = holiday_end_date - holiday_start_date
            for i in range(holiday_days.days + 1):
                date = holiday_start_date + timedelta(i)
                holiday_dates.append(date)
        return holiday_dates

    def company_leave_dates(self):
        """
        :return: This function returns a list of all company leave dates"""
        from datetime import date

        company_leaves = CompanyLeaves.objects.all()
        company_leave_dates = []
        for company_leave in company_leaves:
            if self:
                year = self.start_date.year
            else:
                year = date.today().year
            based_on_week = company_leave.based_on_week
            based_on_week_day = company_leave.based_on_week_day
            for month in range(1, 13):
                if based_on_week != None:
                    # Set Sunday as the first day of the week
                    calendar.setfirstweekday(6)
                    month_calendar = calendar.monthcalendar(year, month)
                    try:
                        weeks = month_calendar[int(based_on_week)]
                        weekdays_in_weeks = [day for day in weeks if day != 0]
                        for day in weekdays_in_weeks:
                            date = datetime.strptime(
                                f"{year}-{month:02}-{day:02}", "%Y-%m-%d"
                            ).date()
                            if (
                                date.weekday() == int(based_on_week_day)
                                and date not in company_leave_dates
                            ):
                                company_leave_dates.append(date)
                    except IndexError:
                        pass
                else:
                    # Set Monday as the first day of the week
                    calendar.setfirstweekday(0)
                    month_calendar = calendar.monthcalendar(year, month)
                    for week in month_calendar:
                        if week[int(based_on_week_day)] != 0:
                            date = datetime.strptime(
                                f"{year}-{month:02}-{week[int(based_on_week_day)]:02}",
                                "%Y-%m-%d",
                            ).date()
                            if date not in company_leave_dates:
                                company_leave_dates.append(date)
        return company_leave_dates

    def save(self, *args, **kwargs):

        self.requested_days = calculate_requested_days(
            self.start_date,
            self.end_date,
            self.start_date_breakdown,
            self.end_date_breakdown,
        )
        if (
            self.leave_type_id.exclude_company_leave == "yes"
            and self.leave_type_id.exclude_holiday == "yes"
        ):
            self.exclude_all_leaves()
        else:
            self.exclude_leaves()

        if self.status in ["cancelled", "rejected"]:
            self.leave_clashes_count = 0
        else:
            self.leave_clashes_count = self.count_leave_clashes()

        super().save(*args, **kwargs)

        self.update_leave_clashes_count()
        work_info = EmployeeWorkInformation.objects.filter(employee_id=self.employee_id)
        department_id = None
        conditions = None
        if work_info.exists():
            department_id = self.employee_id.employee_work_info.department_id
            emp_comp_id = self.employee_id.employee_work_info.company_id
        requested_days = self.requested_days
        applicable_condition = False
        if department_id != None and emp_comp_id != None:
            conditions = MultipleApprovalCondition.objects.filter(
                department=department_id, company_id=emp_comp_id
            ).order_by("condition_value")
        if conditions != None:
            for condition in conditions:
                operator = condition.condition_operator
                if operator == "range":
                    start_value = float(condition.condition_start_value)
                    end_value = float(condition.condition_end_value)
                    if start_value <= requested_days <= end_value:
                        applicable_condition = condition
                        break
                else:
                    operator_func = operator_mapping.get(condition.condition_operator)
                    condition_value = type(requested_days)(condition.condition_value)
                    if operator_func(requested_days, condition_value):
                        applicable_condition = condition
                        break

        if applicable_condition and self.status == "requested":
            LeaveRequestConditionApproval.objects.filter(leave_request_id=self).delete()
            sequence = 0
            managers = applicable_condition.approval_managers()
            for manager in managers:
                sequence += 1
                LeaveRequestConditionApproval.objects.create(
                    sequence=sequence,
                    leave_request_id=self,
                    manager_id=manager,
                )

    def clean(self):
        cleaned_data = super().clean()
        restricted_leave = RestrictLeave.objects.all()
        leave_type_instance = LeaveType.objects.get(name=self.leave_type_id)

        work_info = EmployeeWorkInformation.objects.filter(employee_id=self.employee_id)
        if work_info.exists():
            emp_dep = self.employee_id.employee_work_info.department_id
            emp_job = self.employee_id.employee_work_info.job_position_id

        request = getattr(horilla_middlewares._thread_locals, "request", None)
        if not request.user.is_superuser:
            if EmployeePastLeaveRestrict.objects.first().enabled:
                if self.start_date < date.today():
                    raise ValidationError(_("Requests cannot be made for past dates."))
        if not request.user.is_superuser:

            for restrict in restricted_leave:
                restri = restrict.id
                requ_days = self.requested_dates()

                restri_days = []

                if (
                    restrict.include_all
                    and len(restrict.exclued_leave_types.all()) == 0
                ):
                    restri_days = restrict_leaves(restri)

                if restrict.exclued_leave_types.all():
                    excluded = []
                    for exclued in restrict.exclued_leave_types.all():
                        excluded.append(exclued)
                    if self.leave_type_id in excluded:
                        pass
                    else:
                        restri_days = restrict_leaves(restri)

                if restrict.spesific_leave_types.all():
                    for spesific in restrict.spesific_leave_types.all():
                        if str(spesific.name) == str(leave_type_instance):
                            restri_days = restrict_leaves(restri)

                if restri_days:
                    if (
                        restrict.department == emp_dep
                        and len(restrict.job_position.all()) == 0
                    ):

                        # Check if any date in requ_days is present in restri_days
                        if any(date in restri_days for date in requ_days):
                            raise ValidationError(
                                "You cannot request leave for this date range. The requestesd dates are restricted, Please contact admin."
                            )
                    elif restrict.job_position.all():
                        if emp_job in restrict.job_position.all():
                            if any(date in restri_days for date in requ_days):
                                raise ValidationError(
                                    "You cannot request leave for this date range. The requestesd dates are restricted, Please contact admin."
                                )

        return cleaned_data

    def exclude_all_leaves(self):
        requested_dates = self.requested_dates()
        holiday_dates = self.holiday_dates()
        company_leave_dates = self.company_leave_dates()
        total_leaves = list(set(holiday_dates + company_leave_dates))
        total_leave_count = sum(
            requested_date in total_leaves for requested_date in requested_dates
        )
        if (self.start_date in total_leaves or self.end_date in total_leaves) and (
            self.start_date_breakdown == "second_half"
            or self.end_date_breakdown == "first_half"
        ):
            self.requested_days += 0.5

        self.requested_days = self.requested_days - total_leave_count

    def exclude_leaves(self):
        holiday_count = 0
        if self.leave_type_id.exclude_holiday == "yes":
            requested_dates = self.requested_dates()
            holiday_dates = self.holiday_dates()
            for requested_date in requested_dates:
                if requested_date in holiday_dates:
                    holiday_count += 1
            self.requested_days = self.requested_days - holiday_count
        if self.leave_type_id.exclude_company_leave == "yes":
            requested_dates = self.requested_dates()
            company_leave_dates = self.company_leave_dates()
            company_leave_count = sum(
                requested_date in company_leave_dates
                for requested_date in requested_dates
            )
            self.requested_days = self.requested_days - company_leave_count

    def no_approval(self):
        employee_id = self.employee_id
        leave_type_id = self.leave_type_id
        available_leave = AvailableLeave.objects.get(
            leave_type_id=leave_type_id, employee_id=employee_id
        )
        if self.requested_days > available_leave.available_days:
            leave = self.requested_days - available_leave.available_days
            self.approved_available_days = available_leave.available_days
            available_leave.available_days = 0
            available_leave.carryforward_days = (
                available_leave.carryforward_days - leave
            )
            self.approved_carryforward_days = leave
        else:
            available_leave.available_days = (
                available_leave.available_days - self.requested_days
            )
            self.approved_available_days = self.requested_days
        self.status = "approved"
        available_leave.save()

    def multiple_approvals(self, *args, **kwargs):
        approvals = LeaveRequestConditionApproval.objects.filter(leave_request_id=self)
        requested_query = approvals.filter(is_approved=False).order_by("sequence")
        approved_query = approvals.filter(is_approved=True).order_by("sequence")
        managers = []
        for manager in approvals:
            managers.append(manager.manager_id)
        if approvals.exists():
            result = {
                "managers": managers,
                "approved": approved_query,
                "requested": requested_query,
                "approvals": approvals,
            }
        else:
            result = False
        return result

    def is_approved(self):
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        if request:
            employee = Employee.objects.filter(employee_user_id=request.user).first()
            condition_approval = LeaveRequestConditionApproval.objects.filter(
                leave_request_id=self, manager_id=employee.id
            ).first()
            if condition_approval:
                return not condition_approval.is_approved
            else:
                return True

    def delete(self, *args, **kwargs):
        if self.status == "requested":
            super().delete(*args, **kwargs)

            # Update the leave clashes count for all relevant leave requests
            self.update_leave_clashes_count()
        else:
            request = getattr(horilla_middlewares._thread_locals, "request", None)
            if request:
                clear_messages(request)
                messages.warning(
                    request,
                    _("The {} leave request cannot be deleted !").format(self.status),
                )

    def update_leave_clashes_count(self):
        """
        Update the leave clashes count for all leave requests.
        """
        leave_requests_to_update = LeaveRequest.objects.exclude(
            Q(id=self.id) | Q(status="cancelled") | Q(status="rejected")
        )

        for leave_request in leave_requests_to_update:
            leave_request.leave_clashes_count = leave_request.count_leave_clashes()

        # Bulk update leave clashes count for all leave requests
        LeaveRequest.objects.bulk_update(
            leave_requests_to_update, ["leave_clashes_count"]
        )

    def count_leave_clashes(self):
        """
        Method to count leave clashes where this employee's leave request overlaps
        with other employees' requested dates.
        """
        work_info = EmployeeWorkInformation.objects.filter(employee_id=self.employee_id)
        if work_info.exists() and self.status not in ["cancelled", "rejected"]:
            overlapping_requests = (
                LeaveRequest.objects.exclude(id=self.id)
                .filter(
                    (
                        Q(
                            employee_id__employee_work_info__department_id=self.employee_id.employee_work_info.department_id
                        )
                        | Q(
                            employee_id__employee_work_info__job_position_id=self.employee_id.employee_work_info.job_position_id
                        )
                    )
                    & Q(
                        employee_id__employee_work_info__company_id=self.employee_id.employee_work_info.company_id
                    ),
                    start_date__lte=self.end_date,
                    end_date__gte=self.start_date,
                )
                .exclude(Q(status="cancelled") | Q(status="rejected"))
            )

            return overlapping_requests.count()
        return 0


class LeaverequestFile(models.Model):
    file = models.FileField(upload_to="leave/request_files")


class LeaverequestComment(HorillaModel):
    """
    LeaverequestComment Model
    """

    request_id = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    files = models.ManyToManyField(LeaverequestFile, blank=True)
    comment = models.TextField(null=True, verbose_name=_("Comment"), max_length=255)

    def __str__(self) -> str:
        return f"{self.comment}"


class LeaveAllocationRequest(HorillaModel):
    leave_type_id = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, verbose_name="Leave type"
    )
    employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name="Employee"
    )
    requested_days = models.FloatField(blank=True, null=True)
    requested_date = models.DateField(default=timezone.now)
    description = models.TextField(max_length=255)
    attachment = models.FileField(
        null=True, blank=True, upload_to="leave/leave_attachment"
    )
    status = models.CharField(
        max_length=30, choices=LEAVE_ALLOCATION_STATUS, default="requested"
    )
    reject_reason = models.TextField(blank=True, max_length=255)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.employee_id}| {self.leave_type_id}| {self.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_history = False

    def tracking(self):
        return get_diff(self)

    def allocate_tracking(self):
        """
        This method is used to return the tracked history of the instance
        """

        try:
            histories = get_diff(self)[:2]
            for history in histories:
                if history["type"] == "Changes":
                    for update in history["changes"]:
                        if update["field_name"] == "requested_days":
                            return update
        except:
            return None


class LeaveallocationrequestComment(HorillaModel):
    """
    LeaveallocationrequestComment Model
    """

    request_id = models.ForeignKey(LeaveAllocationRequest, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    files = models.ManyToManyField(LeaverequestFile, blank=True)
    comment = models.TextField(null=True, verbose_name=_("Comment"), max_length=255)

    def __str__(self) -> str:
        return f"{self.comment}"


class LeaveRequestConditionApproval(models.Model):
    sequence = models.IntegerField()
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    leave_request_id = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    manager_id = models.ForeignKey(Employee, on_delete=models.CASCADE)


class RestrictLeave(HorillaModel):
    title = models.CharField(max_length=200)
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    department = models.ForeignKey(
        Department, verbose_name=_("Department"), on_delete=models.CASCADE
    )
    job_position = models.ManyToManyField(
        JobPosition,
        verbose_name=_("Job Position"),
        blank=True,
        help_text=_(
            "If no job positions are specifically selected, the system will consider all job positions under the selected department."
        ),
    )
    include_all = models.BooleanField(
        default=True, help_text=_("Enable to select all Leave types.")
    )
    spesific_leave_types = models.ManyToManyField(
        LeaveType,
        verbose_name=_("Spesific leave types"),
        related_name="spesific_leave_type",
        blank=True,
        help_text=_("Choose specific leave types to restrict."),
    )
    exclued_leave_types = models.ManyToManyField(
        LeaveType,
        verbose_name=_("Exclude leave types"),
        related_name="excluded_leave_type",
        blank=True,
        help_text=_("Choose leave types to exclude from restriction."),
    )

    description = models.TextField(
        null=True, verbose_name=_("Description"), max_length=255
    )
    company_id = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Company"),
    )
    objects = HorillaCompanyManager(related_company_field="company_id")

    def __str__(self) -> str:
        return f"{self.title}"


if apps.is_installed("attendance"):

    class CompensatoryLeaveRequest(HorillaModel):
        leave_type_id = models.ForeignKey(
            LeaveType, on_delete=models.PROTECT, verbose_name="Leave type"
        )
        employee_id = models.ForeignKey(
            Employee, on_delete=models.CASCADE, verbose_name="Employee"
        )
        attendance_id = models.ManyToManyField(
            "attendance.Attendance",
            verbose_name="Attendance",
        )
        requested_days = models.FloatField(blank=True, null=True)
        requested_date = models.DateField(default=timezone.now)
        description = models.TextField(max_length=255)
        status = models.CharField(
            max_length=30, choices=LEAVE_ALLOCATION_STATUS, default="requested"
        )
        reject_reason = models.TextField(blank=True, max_length=255)
        history = HorillaAuditLog(
            related_name="history_set",
            bases=[
                HorillaAuditInfo,
            ],
        )
        objects = HorillaCompanyManager(
            related_company_field="employee_id__employee_work_info__company_id"
        )

        class Meta:
            ordering = ["-id"]

        def __str__(self):
            return f"{self.employee_id}| {self.leave_type_id}| {self.id}"

        def assign_compensatory_leave_type(self):
            available_leave, created = AvailableLeave.objects.get_or_create(
                employee_id=self.employee_id,
                leave_type_id=self.leave_type_id,
            )
            available_leave.available_days += self.requested_days
            available_leave.save()

        def exclude_compensatory_leave(self):
            if AvailableLeave.objects.filter(
                employee_id=self.employee_id,
                leave_type_id=self.leave_type_id,
            ).exists():
                available_leave = AvailableLeave.objects.filter(
                    employee_id=self.employee_id,
                    leave_type_id=self.leave_type_id,
                ).first()
                if available_leave.available_days < self.requested_days:
                    available_leave.available_days = 0
                    available_leave.carryforward_days = max(
                        0,
                        available_leave.carryforward_days
                        - (self.requested_days - available_leave.available_days),
                    )
                else:
                    available_leave.available_days -= self.requested_days
                available_leave.save()

        def save(self, *args, **kwargs):
            self.leave_type_id = LeaveType.objects.filter(
                is_compensatory_leave=True
            ).first()
            super().save(*args, **kwargs)


class LeaveGeneralSetting(HorillaModel):
    """
    LeaveGeneralSettings
    """

    compensatory_leave = models.BooleanField(default=True)
    objects = models.Manager()
    company_id = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)


if apps.is_installed("attendance"):

    class CompensatoryLeaverequestComment(HorillaModel):
        """
        CompensatoryLeaverequestComment Model
        """

        request_id = models.ForeignKey(
            CompensatoryLeaveRequest, on_delete=models.CASCADE
        )
        employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
        files = models.ManyToManyField(LeaverequestFile, blank=True)
        comment = models.TextField(null=True, verbose_name=_("Comment"), max_length=255)

        def __str__(self) -> str:
            return f"{self.comment}"


class EmployeePastLeaveRestrict(HorillaModel):
    enabled = models.BooleanField(default=True)


if apps.is_installed("attendance"):

    class OverrideLeaveRequests(LeaveRequest):
        """
        Class to override Attendance model save method
        """

        # Additional fields and methods specific to AnotherModel
        @receiver(pre_save, sender=LeaveRequest)
        def leaverequest_pre_save(sender, instance, **_kwargs):
            """
            Overriding LeaveRequest model save method
            """
            WorkRecords = get_horilla_model_class(
                app_label="attendance", model="workrecords"
            )
            if (
                instance.start_date == instance.end_date
                and instance.end_date_breakdown != instance.start_date_breakdown
            ):
                instance.end_date_breakdown = instance.start_date_breakdown
                super(LeaveRequest, instance).save()

            period_dates = get_date_range(instance.start_date, instance.end_date)
            if instance.status == "approved":
                for date in period_dates:
                    try:
                        work_entry = (
                            WorkRecords.objects.filter(
                                date=date,
                                employee_id=instance.employee_id,
                            )
                            if WorkRecords.objects.filter(
                                date=date,
                                employee_id=instance.employee_id,
                            ).exists()
                            else WorkRecords()
                        )
                        work_entry.employee_id = instance.employee_id
                        work_entry.is_leave_record = True
                        work_entry.day_percentage = (
                            0.50
                            if instance.start_date == date
                            and instance.start_date_breakdown == "first_half"
                            or instance.end_date == date
                            and instance.end_date_breakdown == "second_half"
                            else 0.00
                        )
                        status = (
                            "CONF"
                            if instance.start_date == date
                            and instance.start_date_breakdown == "first_half"
                            or instance.end_date == date
                            and instance.end_date_breakdown == "second_half"
                            else "ABS"
                        )
                        work_entry.work_record_type = status
                        work_entry.date = date
                        work_entry.message = (
                            "Absent"
                            if status == "ABS"
                            else _("Half day Attendance need to validate")
                        )
                        work_entry.save()
                    except:
                        pass

            else:
                for date in period_dates:
                    WorkRecords.objects.filter(
                        is_leave_record=True,
                        date=date,
                        employee_id=instance.employee_id,
                    ).delete()


@receiver(post_save, sender=LeaveRequest)
def update_available(sender, instance, **kwargs):
    """
    post save method to update the available leaves
    """

    _sender = sender

    def update_leaves():
        try:
            if instance.leave_type_id:
                available_leaves = instance.employee_id.available_leave.filter(
                    leave_type_id=instance.leave_type_id
                )
                for assigned in available_leaves:
                    assigned.save()
        except Exception as e:
            pass

    thread = threading.Thread(target=update_leaves)
    thread.start()
