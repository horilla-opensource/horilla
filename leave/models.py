import calendar
from collections.abc import Iterable
from datetime import datetime, timedelta
import operator
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from django.utils.translation import gettext_lazy as _
from base import thread_local_middleware
from base.models import Company, MultipleApprovalCondition
from base.horilla_company_manager import HorillaCompanyManager
from employee.models import Employee
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from .methods import calculate_requested_days
from django.core.files.storage import default_storage
from django.conf import settings


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
    ("cancelled_and_rejected", _("Cancelled & Rejected")),
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


class LeaveType(models.Model):
    icon = models.ImageField(null=True, blank=True, upload_to="leave/leave_icon")
    name = models.CharField(max_length=30, null=False)
    color = models.CharField(null=True, max_length=30)
    payment = models.CharField(max_length=30, choices=PAYMENT, default="unpaid")
    count = models.IntegerField(null=True, default=1)
    period_in = models.CharField(max_length=30, choices=TIME_PERIOD, default="day")
    total_days = models.IntegerField(null=True, default=1)
    reset = models.BooleanField(default=False)
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
    carryforward_max = models.IntegerField(null=True, blank=True)
    carryforward_expire_in = models.IntegerField(null=True, blank=True)
    carryforward_expire_period = models.CharField(
        max_length=30, choices=TIME_PERIOD, null=True, blank=True
    )
    require_approval = models.CharField(
        max_length=30, choices=CHOICES, null=True, blank=True
    )
    require_attachment = models.CharField(
        max_length=30,
        choices=CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Require Attachment"),
    )
    exclude_company_leave = models.CharField(max_length=30, choices=CHOICES)
    exclude_holiday = models.CharField(max_length=30, choices=CHOICES)
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
            full_filename = settings.MEDIA_ROOT + self.icon.name

            if default_storage.exists(full_filename):
                url = self.icon.url
        return url

    def __str__(self):
        return self.name


class Holiday(models.Model):
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


class CompanyLeave(models.Model):
    based_on_week = models.CharField(
        max_length=100, choices=WEEKS, blank=True, null=True
    )
    based_on_week_day = models.CharField(max_length=100, choices=WEEK_DAYS)
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = models.Manager()
    objects = HorillaCompanyManager(related_company_field="company_id")

    class Meta:
        unique_together = ("based_on_week", "based_on_week_day")

    def __str__(self):
        return f"{dict(WEEK_DAYS).get(self.based_on_week_day)} | {dict(WEEKS).get(self.based_on_week)}"


class AvailableLeave(models.Model):
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

    class Meta:
        unique_together = ("leave_type_id", "employee_id")

    def __str__(self):
        return f"{self.employee_id} | {self.leave_type_id}"

        # Resetting carryforward days

    def update_carryforward(self, available_leave):
        if available_leave.leave_type_id.carryforward_type != "no carryforward":
            if (
                available_leave.leave_type_id.carryforward_max
                >= available_leave.total_leave_days
            ):
                available_leave.carryforward_days = available_leave.total_leave_days
            else:
                available_leave.carryforward_days = (
                    available_leave.leave_type_id.carryforward_max
                )
        available_leave.available_days = available_leave.leave_type_id.total_days
        available_leave.save()

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

        self.total_leave_days = self.available_days + self.carryforward_days
        super().save(*args, **kwargs)


class LeaveRequest(models.Model):
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
    description = models.TextField(verbose_name=_("Description"))
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
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="leave_request_created",
        verbose_name=_("Created By"),
    )
    approved_available_days = models.FloatField(default=0)
    approved_carryforward_days = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now="True")
    reject_reason = models.TextField(blank=True, verbose_name=_("Reject Reason"))
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    def __str__(self):
        return f"{self.employee_id} | {self.leave_type_id} | {self.status}"

    def get_penalties_count(self):
        """
        This method is used to return the total penalties in the late early instance
        """
        return self.penaltyaccount_set.count()

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
        holidays = Holiday.objects.all()
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
        company_leaves = CompanyLeave.objects.all()
        company_leave_dates = []
        for company_leave in company_leaves:
            year = self.start_date.year
            based_on_week = company_leave.based_on_week
            based_on_week_day = company_leave.based_on_week_day
            for month in range(1, 13):
                if based_on_week != None:
                    # Set Sunday as the first day of the week
                    calendar.setfirstweekday(6)
                    month_calendar = calendar.monthcalendar(year, month)
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
        super().save(*args, **kwargs)
        department_id = self.employee_id.employee_work_info.department_id
        requested_days = self.requested_days
        applicable_condition = False
        conditions = MultipleApprovalCondition.objects.filter(department=department_id).order_by('condition_value')
        if conditions:
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
                
        if applicable_condition and self.status=="requested":
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

    def exclude_all_leaves(self):
        requested_dates = self.requested_dates()
        holiday_dates = self.holiday_dates()
        company_leave_dates = self.company_leave_dates()
        total_leaves = list(set(holiday_dates + company_leave_dates))
        total_leave_count = sum(
            requested_date in total_leaves for requested_date in requested_dates
        )
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
                "approvals":approvals,
            }
        else:
            result = False
        return result
    
    def is_approved(self):
        request = getattr(thread_local_middleware._thread_locals,"request",None)
        if request:
            employee =  Employee.objects.filter(employee_user_id = request.user).first()
            condition_approval = LeaveRequestConditionApproval.objects.filter(leave_request_id=self,manager_id = employee.id).first()
            if condition_approval:
                return not condition_approval.is_approved
            else:
                return  True


class LeaverequestFile(models.Model):
    file = models.FileField(upload_to="leave/request_files")


class LeaverequestComment(models.Model):
    """
    LeaverequestComment Model
    """
    
    request_id = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    files = models.ManyToManyField(LeaverequestFile,blank=True)
    comment = models.TextField(null=True, verbose_name=_("Comment"))
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        null=True,
    )

    def __str__(self) -> str:
        return f"{self.comment}"

from horilla_audit.methods import get_diff
class LeaveAllocationRequest(models.Model):
    leave_type_id = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, verbose_name="Leave type"
    )
    employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE, verbose_name="Employee"
    )
    requested_days = models.FloatField(blank=True, null=True)
    requested_date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="leave_allocation_request_created",
    )
    description = models.TextField()
    attachment = models.FileField(
        null=True, blank=True, upload_to="leave/leave_attachment"
    )
    status = models.CharField(
        max_length=30, choices=LEAVE_ALLOCATION_STATUS, default="requested"
    )
    created_at = models.DateTimeField(auto_now="True")
    reject_reason = models.TextField(blank=True)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

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
                if history['type'] == 'Changes':
                    for update in history['changes']:
                        if update["field_name"] == "requested_days":
                            return update
        except:
            return None


class LeaveallocationrequestComment(models.Model):
    """
    LeaveallocationrequestComment Model
    """
    
    request_id = models.ForeignKey(LeaveAllocationRequest, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    files = models.ManyToManyField(LeaverequestFile,blank=True)
    comment = models.TextField(null=True, verbose_name=_("Comment"))
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        null=True,
    )

    def __str__(self) -> str:
        return f"{self.comment}"


class LeaveRequestConditionApproval(models.Model):
    sequence = models.IntegerField()
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    leave_request_id = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    manager_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
