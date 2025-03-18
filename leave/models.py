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
from django.db.models import Q, Sum
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
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
from horilla.horilla_middlewares import _thread_locals
from horilla.methods import get_horilla_model_class
from horilla.models import HorillaModel
from horilla_audit.methods import get_diff
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from horilla_views.cbv_methods import render_template
from leave.methods import calculate_requested_days
from leave.threading import LeaveClashThread

from .methods import (
    attendance_days,
    calculate_requested_days,
    filter_conditional_leave_request,
)

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
    carryforward_expire_date = models.DateField(null=True, blank=True)
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

        if not self.reset or not self.reset_day:
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

    def set_expired_date(self, assigned_date):
        period = self.carryforward_expire_in
        if self.carryforward_expire_period == "day":
            expired_date = assigned_date + relativedelta(days=period)
        elif self.carryforward_expire_period == "month":
            expired_date = assigned_date + relativedelta(months=period)
        else:
            expired_date = assigned_date + relativedelta(years=period)

        return expired_date

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

        if (
            self.carryforward_type == "carryforward expire"
            and not self.carryforward_expire_date
        ):
            self.carryforward_expire_date = self.set_expired_date(
                assigned_date=self.created_at
            )
        elif self.carryforward_type != "carryforward expire":
            self.carryforward_expire_date = None

        super().save()

    def __str__(self):
        return self.name

    def leave_list_actions(self):
        """
        actions for list view
        """

        return render_template(
            path="cbv/leave_types/leave_type_list_actions.html",
            context={"instance": self},
        )

    def leave_detail_reset(self):
        """
        reset col in detail view
        """
        return render_template(
            path="cbv/leave_types/leave_detail_reset.html", context={"instance": self}
        )

    def leave_detail_carryforward(self):
        """
        carryforward col in detail view
        """
        return render_template(
            path="cbv/leave_types/leave_detail_carryforward.html",
            context={"instance": self},
        )

    def get_create_url(self):
        """
        This method to get create url
        """

        url = reverse_lazy("type-creation")
        return url

    def get_assign_url(self):
        """
        This method to get assign url
        """

        url = reverse_lazy("assign-one", kwargs={"pk": self.pk})
        return url

    def get_update_url(self):
        """
        for to get update url
        """

        url = reverse_lazy("type-update", kwargs={"id": self.pk})
        return url

    def get_delete_url(self):
        """
        This method to get delete url
        """
        url = reverse_lazy("generic-delete")

        return url

    # def get_delete_url(self):
    #     """
    #     for to get delete url
    #     """

    #     url = reverse_lazy("type-delete", kwargs={"obj_id": self.pk})
    #     message = "Are you sure you want to delete this leave type?"
    #     return f"'{url}'" + "," + f"'{message}'"

    def leave_detail_view(self):
        """
        detail view
        """

        url = reverse("leave-type-detail-view", kwargs={"pk": self.pk})
        return url

    def encashable(self):
        """
        encashable condition
        """
        return "Yes" if self.is_encashable else "No"

    def detail_view_actions(self):
        """
        detail view actions
        """
        return render_template(
            path="cbv/leave_types/detail_actions.html", context={"instance": self}
        )


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

    def detail_view(self):
        """
        detail view
        """

        url = reverse("holiday-detail-view", kwargs={"pk": self.pk})
        return url

    def detail_view_actions(self):
        """
        detail view actions
        """
        return render_template(
            path="cbv/holidays/detail_view_actions.html",
            context={"instance": self},
        )

    def get_recurring_status(self):
        """
        recurring data
        """
        return "Yes" if self.recurring else "No"

    def holidays_actions(self):
        """
        method for rendering actions(edit,delete)
        """

        return render_template(
            path="cbv/holidays/holidays_actions.html",
            context={"instance": self},
        )


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

    def custom_based_on_week(self):
        """
        custom based on col
        """

        return render_template(
            path="cbv/company_leaves/on_week.html",
            context={"instance": self, "weeks": WEEKS},
        )

    def get_detail_title(self):
        """
        for return title
        """

        title = "Company Leaves"
        return title

    def detail_view_actions(self):
        """
        detail view actions
        """
        return render_template(
            path="cbv/company_leaves/detail_view_actions.html",
            context={"instance": self},
        )

    def based_on_week_day_col(self):
        """
        custom based on week day col
        """

        return render_template(
            path="cbv/company_leaves/on_week_day.html",
            context={"instance": self, "week_days": WEEK_DAYS},
        )

    def company_leave_actions(self):
        """
        custom actions col
        """

        return render_template(
            path="cbv/company_leaves/company_leave_actions.html",
            context={"instance": self, "weeks": WEEKS},
        )

    def detail_view(self):
        """
        detail view
        """

        url = reverse("company-leave-detail-view", kwargs={"pk": self.pk})
        return url

    def get_avatar(self):
        """
        Method will rerun the api to the avatar or path to the profile image
        """
        url = (
            f"https://ui-avatars.com/api/?name={self.get_full_name()}&background=random"
        )
        if self.profile:
            full_filename = settings.MEDIA_ROOT + self.profile.name

            if default_storage.exists(full_filename):
                url = self.profile.url

        return url


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

    def assigned_leave_actions(self):
        """
        method for edit and delete actions coloumn
        """
        return render_template(
            path="cbv/assigned_leave/assigned_leave_actions.html",
            context={"instance": self},
        )

    def assigned_leave_detail_actions(self):
        """
        method for detail view edit and delete actions
        """
        return render_template(
            path="cbv/assigned_leave/assigned_leave_detail_actions.html",
            context={"instance": self},
        )

    def assigned_leave_detail_view(self):
        """
        detail view
        """
        url = reverse("available-leave-single-view", kwargs={"pk": self.pk})
        return url

    def assigned_leave_detail_name_subtitle(self):
        """
        Return subtitle containing both name and emp id.
        """
        return f"{self.employee_id}"

    def assigned_leave_detail_postion_subtitle(self):
        """
        Return subtitle containing both department and job position information.
        """
        return f"{self.employee_id.employee_work_info.department_id} / {self.employee_id.employee_work_info.job_position_id}"

    def forcasted_leaves(self):
        forecasted_leave = {}
        if self.leave_type_id.reset_based == "monthly":
            today = datetime.now()
            for i in range(1, 7):  # Calculate for the next 6 months
                next_month = today + relativedelta(months=i)
                if self.leave_type_id.carryforward_max:
                    forecasted_leave[next_month.strftime("%Y-%m")] = (
                        self.available_days
                        + min(
                            self.leave_type_id.carryforward_max,
                            (self.leave_type_id.total_days * i),
                        )
                    )
                else:
                    forecasted_leave[next_month.strftime("%Y-%m")] = (
                        self.available_days + (self.leave_type_id.total_days * i)
                    )
        return forecasted_leave

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
        """
        taken leaves calculation
        """
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

    def pre_save_processing(self):
        """
        Reusable method to compute fields normally set in save().
        """
        # Logic for reset_date
        if self.reset_date is None and self.leave_type_id.reset:
            self.reset_date = self.set_reset_date(
                assigned_date=self.assigned_date, available_leave=self
            )

        # Logic for expired_date
        if self.leave_type_id.carryforward_type == "carryforward expire":
            expiry_date = self.assigned_date
            if self.leave_type_id.carryforward_expire_date:
                expiry_date = self.leave_type_id.carryforward_expire_date
            self.expired_date = expiry_date

        # Compute total_leave_days and ensure carryforward_days >= 0
        self.total_leave_days = round(
            max(self.available_days + self.carryforward_days, 0), 3
        )
        self.carryforward_days = round(max(self.carryforward_days, 0), 3)

    def save(self, *args, **kwargs):
        self.pre_save_processing()
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
        null=True,
        related_name="leave_request_created",
        verbose_name=_("Created By"),
    )
    objects = HorillaCompanyManager(
        related_company_field="employee_id__employee_work_info__company_id"
    )

    class Meta:
        ordering = ["-id"]

    def comment_action(self):
        """
        method for rendering comment action
        """

        return render_template(
            path="cbv/my_leave_request/comment.html",
            context={"instance": self},
        )

    def cancel_confirmation_action(self):
        """
        method for rendering cancel action
        """

        current_date = date.today()
        return render_template(
            path="cbv/my_leave_request/confirm_cancel.html",
            context={"instance": self, "current_date": current_date},
        )

    def leave_actions(self):
        """
        method for rendering cancel action
        """

        return render_template(
            path="cbv/my_leave_request/leave_actions.html",
            context={"instance": self},
        )

    def detail_leave_actions(self):
        """
        method for rendering detail view action
        """

        return render_template(
            path="cbv/my_leave_request/detail_leave_actions.html",
            context={"instance": self},
        )

    def get_period(self):

        return f"{self.start_date} to {self.end_date}"

    def clashed_due_to(self):
        """
        method for rendering clashed_due_to col in clashes
        """
        overlapping_requests = LeaveRequest.objects.filter(
            Q(
                employee_id__employee_work_info__department_id=self.employee_id.employee_work_info.department_id
            )
            | Q(
                employee_id__employee_work_info__job_position_id=self.employee_id.employee_work_info.job_position_id
            ),
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        )

        clashed_due_to_department = overlapping_requests.filter(
            employee_id__employee_work_info__department_id=self.employee_id.employee_work_info.department_id
        )
        clashed_due_to_job_position = overlapping_requests.filter(
            employee_id__employee_work_info__job_position_id=self.employee_id.employee_work_info.job_position_id
        )

        return render_template(
            path="cbv/leave_requests/clashed_due_to.html",
            context={
                "instance": self,
                "clashed_due_to_department": clashed_due_to_department,
                "clashed_due_to_job_position": clashed_due_to_job_position,
            },
        )

    def leave_type_custom(self):
        """
        leave type custom col
        """
        leave_requests_with_interview = []
        context = {"instance": self}
        if apps.is_installed("recruitment"):
            Schedule = get_horilla_model_class(
                app_label="recruitment", model="interviewschedule"
            )
            interviews = Schedule.objects.filter(
                employee_id=self.employee_id,
                interview_date__range=[
                    self.start_date,
                    self.end_date,
                ],
            )
            if interviews:
                leave_requests_with_interview.append(interviews)

            context = {
                "instance": self,
                "leave_requests_with_interview": leave_requests_with_interview,
            }
        return render_template(
            path="cbv/my_leave_request/leave_type_col.html", context=context
        )

    def is_rejected(self):
        """
        method to change background if they are rejected
        """

        if self.status == "rejected":
            return 'style="background-color: rgba(255, 166, 0, 0.158);"'

    def my_leave_request_detail_subtitle(self):
        """
        Return subtitle containing both department and job position information.
        """
        return f"{self.employee_id.employee_work_info.department_id} / {self.employee_id.employee_work_info.job_position_id}"

    def my_leave_request_detail_view(self):
        """
        detail view
        """
        url = reverse("my-leave-request-detail-view", kwargs={"pk": self.pk})
        return url

    def rejected_action(self):
        """
        method for rendering rejected action
        """

        return render_template(
            path="cbv/my_leave_request/rejected_action.html",
            context={"instance": self},
        )

    def cancelled_action(self):
        """
        method for rendering cancelled action
        """

        return render_template(
            path="cbv/my_leave_request/cancelled_action.html",
            context={"instance": self},
        )

    def attachment_action(self):
        """
        method for rendering attachment action
        """

        return render_template(
            path="cbv/my_leave_request/attachment_action.html",
            context={"instance": self},
        )

    def multiple_approval_action(self):
        """
        method for rendering multiple approval action
        """

        return render_template(
            path="cbv/leave_requests/multiple_approval_action.html",
            context={"instance": self},
        )

    def custom_status_col(self):
        """
        method for rendering custom status col
        """
        request = getattr(_thread_locals, "request")
        multiple_approvals = filter_conditional_leave_request(request).distinct()

        return render_template(
            path="cbv/leave_requests/custom_status_col.html",
            context={"instance": self, "multiple_approvals": multiple_approvals},
        )

    def leave_request_detail_action(self):
        """
        method for rendering detail view action
        """

        return render_template(
            path="cbv/leave_requests/leave_request_detail_actions.html",
            context={"instance": self},
        )

    def comment_sidebar(self):
        """
        method for comment sidebar
        """
        return render_template(
            path="cbv/leave_requests/comment_action.html",
            context={"instance": self},
        )

    def leave_clash_col(self):
        """
        method for leave clash coloumn
        """
        return render_template(
            path="cbv/leave_requests/leave_clash.html",
            context={"instance": self},
        )

    def penality_col(self):
        """
        method for penality coloumn
        """
        return render_template(
            path="cbv/leave_requests/penality.html",
            context={"instance": self},
        )

    def actions_col(self):
        """
        method for actions coloumn
        """
        return render_template(
            path="cbv/leave_requests/actions_col.html",
            context={"instance": self},
        )

    def confirmation_col(self):
        """
        method for confirmation button coloumn
        """
        current_date = date.today()

        return render_template(
            path="cbv/leave_requests/confirmation.html",
            context={
                "instance": self,
                "current_date": current_date,
                "end_date": self.end_date,
            },
        )

    def is_attendance_request_cancelled(self):
        """
        method to change background if they are cancelled
        """

        if self.status == "cancelled":
            return 'style="background-color: lightgrey"'

    def leave_requests_detail_view(self):
        """
        detail view
        """
        url = reverse("leave-requests-detail-view", kwargs={"pk": self.pk})
        return url

    def leave_requests_detail_view_actions(self):
        """
        method for detail view actions coloumn
        """
        current_date = date.today()
        return render_template(
            path="cbv/leave_requests/leave_request_detail_actions.html",
            context={"instance": self, "current_date": current_date},
        )

    def leave_requests_custom_emp_col(self):
        """
        custom emp col in leave requests
        """
        leave_requests_with_interview = []
        context = {"instance": self}
        if apps.is_installed("recruitment"):
            Schedule = get_horilla_model_class(
                app_label="recruitment", model="interviewschedule"
            )
            interviews = Schedule.objects.filter(
                employee_id=self.employee_id,
                interview_date__range=[
                    self.start_date,
                    self.end_date,
                ],
            )
            if interviews:
                leave_requests_with_interview.append(interviews)
            context = {
                "instance": self,
                "leave_requests_with_interview": leave_requests_with_interview,
            }

        return render_template(
            path="cbv/leave_requests/leave_request_emp_col.html", context=context
        )

    def leave_requests_detail_subtitle(self):
        """
        Return subtitle containing both name and emp id.
        """
        return f"{self.employee_id}"

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
                if not isinstance(manager, Employee):
                    manager = getattr(self.employee_id.employee_work_info, manager)
                LeaveRequestConditionApproval.objects.create(
                    sequence=sequence,
                    leave_request_id=self,
                    manager_id=manager,
                )

    def clean(self, *args, **kwargs):

        cleaned_data = super().clean(*args, **kwargs)
        restricted_leave = RestrictLeave.objects.all()
        leave_type_instance = LeaveType.objects.get(id=self.leave_type_id.id)

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

    def clean(self, *args, **kwargs):
        if self.status != "requested":
            raise ValidationError(
                _(
                    "This form cannot be edited because the status is Requested / Rejected."
                )
            )

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

    def get_status(self):
        """
        Display status
        """
        return dict(LEAVE_ALLOCATION_STATUS).get(self.status)

    def comment(self):
        """
        For comment column
        """

        return render_template(
            path="cbv/leave_allocation_request/comment.html",
            context={"instance": self},
        )

    def action_col(self):
        """
        For action column
        """

        return render_template(
            path="cbv/leave_allocation_request/action_column.html",
            context={"instance": self},
        )

    def detail_action(self):
        """
        For action column
        """

        return render_template(
            path="cbv/leave_allocation_request/detail_action.html",
            context={"instance": self},
        )

    def leave_detail_action(self):
        """
        For action column
        """

        return render_template(
            path="cbv/leave_allocation_request/leave_detail_action.html",
            context={"instance": self},
        )

    def attachment_col(self):
        """
        For attachment column
        """

        return render_template(
            path="cbv/leave_allocation_request/attachment.html",
            context={"instance": self},
        )

    def history_col(self):
        """
        For history column
        """

        return render_template(
            path="cbv/leave_allocation_request/history.html",
            context={"instance": self},
        )

    def reject_col(self):
        """
        For rejeect column
        """

        return render_template(
            path="cbv/leave_allocation_request/reject.html",
            context={"instance": self},
        )

    def confirm_col(self):
        """
        For action column
        """

        return render_template(
            path="cbv/leave_allocation_request/confirmations.html",
            context={"instance": self},
        )

    def diff_cell(self):
        if self.status == "rejected":
            return 'style="background-color: rgba(255, 166, 0, 0.158);"'

    def leave_request_allocation_detail_subtitle(self):
        """
        Return subtitle containing both department and job position information.
        """
        return f"{self.employee_id.employee_work_info.department_id} / {self.employee_id.employee_work_info.job_position_id}"

    def leave_request_allocation_detail_view(self):
        """
        detail view
        """
        url = reverse("detail-leave-allocation-request", kwargs={"pk": self.pk})
        return url

    def detail_view_leave_request_allocation(self):
        """
        detail view
        """
        url = reverse("leave-allocation-request-detail-view", kwargs={"pk": self.pk})
        return url


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

    def job_position_col(self):
        """
        For job position column
        """

        return render_template(
            path="cbv/restricted_days/job_position.html",
            context={"instance": self},
        )

    def actions_col(self):
        """
        For action column
        """

        return render_template(
            path="cbv/restricted_days/actions.html",
            context={"instance": self},
        )

    def detail_action(self):
        """
        For action column
        """

        return render_template(
            path="cbv/restricted_days/detail_action.html",
            context={"instance": self},
        )

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.title}&background=random"
        return url

    def restricted_days_detail_view(self):
        """
        detail view
        """
        url = reverse("restricted-days-detail-view", kwargs={"pk": self.pk})
        return url


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

        def status_display(self):
            """
            status
            """
            return dict(LEAVE_ALLOCATION_STATUS).get(self.status)

        def compensatory_comment(self):
            """
            comment sidebar col
            """
            return render_template(
                path="cbv/compensatory_leave/compensatory_comment.html",
                context={"instance": self},
            )

        def compensatory_date(self):
            """
            date col
            """
            return render_template(
                path="cbv/compensatory_leave/custom_date.html",
                context={"instance": self},
            )

        def compensatory_options(self):
            """
            edit and delete options
            """
            return render_template(
                path="cbv/compensatory_leave/compensatory_actions.html",
                context={"instance": self},
            )

        def compensatory_confirm_actions(self):
            """
            approve and reject options
            """
            return render_template(
                path="cbv/compensatory_leave/compensatory_confirmation.html",
                context={"instance": self},
            )

        def compensatory_detail_name_subtitle(self):
            """
            Return subtitle containing both name and emp id.
            """
            return f"{self.employee_id}"

        def compensatory_detail_subtitle(self):
            """
            Return subtitle containing both department and job position information.
            """
            return f"{self.employee_id.employee_work_info.department_id} / {self.employee_id.employee_work_info.job_position_id}"

        def my_compensatory_detail_actions(self):
            """
            my compensatory detail view actions
            """
            return render_template(
                path="cbv/compensatory_leave/my_compensatory_detail_action.html",
                context={"instance": self},
            )

        def compensatory_detail_actions(self):
            """
            compensatory detail view actions
            """
            return render_template(
                path="cbv/compensatory_leave/compensatory_detail_actions.html",
                context={"instance": self},
            )

        def compensatory_detail_reject_reason(self):
            """
            compensatory reject reason in detail view
            """
            return render_template(
                path="cbv/compensatory_leave/detail_reject_reason.html",
                context={"instance": self},
            )

        def my_compensatory_detail_view(self):
            """
            detail view of my compensatory tab
            """
            url = reverse("my-compensatory-detail-view", kwargs={"pk": self.pk})
            return url

        def compensatory_detail_view(self):
            """
            detail view of compensatory tab
            """
            url = reverse("compensatory-detail-view", kwargs={"pk": self.pk})
            return url

        def is_compensatory_request_rejected(self):
            """
            method to change background if they are rejected
            """
            hovering = "lightgrey"
            if self.status == "rejected":
                return (
                    f'style="background-color: rgba(255, 166, 0, 0.158);"'
                    f"onmouseover=\"this.style.backgroundColor='{hovering}';\" "
                    f"onmouseout=\"this.style.backgroundColor='rgba(255, 166, 0, 0.158)';\""
                )

        def assign_compensatory_leave_type(self):
            available_leave, created = AvailableLeave.objects.get_or_create(
                employee_id=self.employee_id,
                leave_type_id=self.leave_type_id,
            )
            available_leave.available_days += self.requested_days
            available_leave.save()

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

        pass
        # Additional fields and methods specific to AnotherModel
        # @receiver(pre_save, sender=LeaveRequest)
        # def leaverequest_pre_save(sender, instance, **_kwargs):
        #     """
        #     Overriding LeaveRequest model save method
        #     """
        #     WorkRecords = get_horilla_model_class(
        #         app_label="attendance", model="workrecords"
        #     )
        #     if (
        #         instance.start_date == instance.end_date
        #         and instance.end_date_breakdown != instance.start_date_breakdown
        #     ):
        #         instance.end_date_breakdown = instance.start_date_breakdown
        #         super(LeaveRequest, instance).save()

        #     period_dates = get_date_range(instance.start_date, instance.end_date)
        #     if instance.status == "approved":
        #         for date in period_dates:
        #             try:
        #                 work_entry = (
        #                     WorkRecords.objects.filter(
        #                         date=date,
        #                         employee_id=instance.employee_id,
        #                     )
        #                     if WorkRecords.objects.filter(
        #                         date=date,
        #                         employee_id=instance.employee_id,
        #                     ).exists()
        #                     else WorkRecords()
        #                 )
        #                 work_entry.employee_id = instance.employee_id
        #                 work_entry.is_leave_record = True
        #                 work_entry.day_percentage = (
        #                     0.50
        #                     if instance.start_date == date
        #                     and instance.start_date_breakdown == "first_half"
        #                     or instance.end_date == date
        #                     and instance.end_date_breakdown == "second_half"
        #                     else 0.00
        #                 )
        #                 status = (
        #                     "CONF"
        #                     if instance.start_date == date
        #                     and instance.start_date_breakdown == "first_half"
        #                     or instance.end_date == date
        #                     and instance.end_date_breakdown == "second_half"
        #                     else "ABS"
        #                 )
        #                 work_entry.work_record_type = status
        #                 work_entry.date = date
        #                 work_entry.message = (
        #                     "Absent"
        #                     if status == "ABS"
        #                     else _("Half day Attendance need to validate")
        #                 )
        #                 work_entry.save()
        #             except:
        #                 pass

        #     else:
        #         for date in period_dates:
        #             WorkRecords.objects.filter(
        #                 is_leave_record=True,
        #                 date=date,
        #                 employee_id=instance.employee_id,
        #             ).delete()


# @receiver(post_save, sender=LeaveRequest)
# def update_available(sender, instance, **kwargs):
#     """
#     post save method to update the available leaves
#     """

#     _sender = sender

#     def update_leaves():
#         try:
#             if instance.leave_type_id:
#                 available_leaves = instance.employee_id.available_leave.filter(
#                     leave_type_id=instance.leave_type_id
#                 )
#                 for assigned in available_leaves:
#                     assigned.save()
#         except Exception as e:
#             pass

#     thread = threading.Thread(target=update_leaves)
#     thread.start()
