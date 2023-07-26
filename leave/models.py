from django.db import models
from .methods import calculate_requested_days
from recruitment.models import JobPosition
from base.models import JobRole
from employee.models import Employee
from datetime import datetime, timedelta
from django.utils import timezone
import calendar
from django.utils.translation import gettext_lazy as _

from django.core.exceptions import ValidationError


# Create your models here.
BREAKDOWN = [('full_day', _('Full Day')), ('first_half',
                                        _('First Half')), ('second_half', _('Second Half'))]
CHOICES = [("yes", "Yes"), ("no", "No")]

RESET_BASED = [("yearly", _("Yearly")), ("monthly",
                                      _("Monthly")), ("weekly", _("Weekly"))]
MONTHS = [("1", "Jan"), ("2", "Feb"), ("3", "Mar"), ("4", "Apr"), ("5", "May"), ("6", "Jun"),
          ("7", "Jul"), ("8", "Aug"), ("9", "Sep"), ("10", "Oct"), ("11", "Nov"), ("12", "Dec")]

DAYS = [("last day", "Last Day"), ("1", "1st"), ("2", "2nd"), ("3", "3rd"), ("4", "4th"), ("5", "5th"), ("6", "6th"), ("7", "7th"), ("8", "8th"), ("9", "9th"), ("10", "10th"), ("11", "11th"), ("12", "12th"), ("13", "13th"), ("14", "14th"), ("15", "15th"),
        ("16", "16th"), ("17", "17th"), ("18", "18th"), ("19", "19th"), ("20", "20th"), ("21", "21th"), ("22", "22th"), ("23", "23th"), ("24", "24th"), ("25", "25th"), ("26", "26th"), ("27", "27th"), ("28", "28th"), ("29", "29th"), ("30", "30th"), ("31", "31th"), ]


TIME_PERIOD = [("day", _("Day")), ("month", _("Month")), ("year", _("Year"))]

PAYMENT = [("paid", _("Paid")), ("unpaid", _("Unpaid"))]

CARRYFORWARD_TYPE = [("no carryforward", _("No Carry Forward")), ("carryforward", _("Carry Forward")),
                     ("carryforward expire", _("Carry Forward with Expire")),
                     ]

ACCRUAL_PLAN = [("job_position", _("Job Position")), ("job_role", _("Job Role"))]


LEAVE_STATUS = (("requested", _("Requested")), ("approved",
                _("Approved")), ("cancelled", _("Cancelled")))


WEEKS = [('0', _('First Week')),
         ('1', _('Second Week')),
         ('2', _('Third Week')),
         ('3', _('Fourth Week')),
         ('5', _('Fifth Week')),]


WEEK_DAYS = [('0', _('Monday')),
             ('1', _('Tuesday')),
             ('2', _('Wednesday')),
             ('3', _('Thursday')),
             ('4', _('Friday')),
             ('5', _('Saturday')),
             ('6', _('Sunday')),]


class LeaveType(models.Model):
    icon = models.ImageField(
        null=True, blank=True, upload_to='leave/leave_icon')
    name = models.CharField(max_length=30, null=False)
    color = models.CharField(null=True, max_length=30)
    payment = models.CharField(
        max_length=30, choices=PAYMENT, default='unpaid')
    count = models.IntegerField(null=True, default=1)
    period_in = models.CharField(
        max_length=30, choices=TIME_PERIOD, default='day')
    total_days = models.IntegerField(null=True, default=1)
    reset = models.BooleanField(default=False)
    reset_based = models.CharField(
        max_length=30, choices=RESET_BASED, blank=True, null=True,)
    reset_month = models.CharField(max_length=30, choices=MONTHS, blank=True)
    reset_day = models.CharField(
        max_length=30, choices=DAYS, null=True, blank=True)
    reset_weekend = models.CharField(
        max_length=10, null=True, blank=True, choices=WEEK_DAYS)
    carryforward_type = models.CharField(
        max_length=30, choices=CARRYFORWARD_TYPE, default='no carryforward')
    carryforward_max = models.IntegerField(null=True, blank=True)
    carryforward_expire_in = models.IntegerField(null=True, blank=True)
    carryforward_expire_period = models.CharField(
        max_length=30, choices=TIME_PERIOD, null=True, blank=True)
    require_approval = models.CharField(
        max_length=30, choices=CHOICES, null=True, blank=True)
    exclude_company_leave = models.CharField(
        max_length=30, choices=CHOICES)
    exclude_holiday = models.CharField(
        max_length=30, choices=CHOICES)

    def __str__(self):
        return self.name


class Holiday(models.Model):
    name = models.CharField(max_length=30, null=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    recurring = models.BooleanField(default=False)
    objects = models.Manager()

    def __str__(self):
        return self.name





class CompanyLeave(models.Model):
    based_on_week = models.CharField(
        max_length=100, choices=WEEKS, blank=True, null=True)
    based_on_week_day = models.CharField(max_length=100, choices=WEEK_DAYS)
    objects = models.Manager()

    class Meta:
        unique_together = ('based_on_week', 'based_on_week_day')

    def __str__(self):
        return f"{dict(WEEK_DAYS).get(self.based_on_week_day)} | {dict(WEEKS).get(self.based_on_week)}"


class AvailableLeave(models.Model):
    leave_type_id = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name='employee_available_leave', blank=True, null=True)
    employee_id = models.ForeignKey(
        Employee, on_delete=models.DO_NOTHING, related_name='available_leave')
    available_days = models.FloatField(default=0)
    carryforward_days = models.FloatField(default=0)
    total_leave_days = models.FloatField(default=0)
    assigned_date = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ('leave_type_id', 'employee_id')

    def __str__(self):
        return f"{self.employee_id} | {self.leave_type_id}"

    def save(self, *args, **kwargs):
        self.total_leave_days = self.available_days + self.carryforward_days
        super().save(*args, **kwargs)


class LeaveRequest(models.Model):
    leave_type_id = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(
        Employee, on_delete=models.CASCADE)
    start_date = models.DateField(null=False)
    start_date_breakdown = models.CharField(
        max_length=30, choices=BREAKDOWN, default='full_day')
    end_date = models.DateField(null=True, blank=True)
    end_date_breakdown = models.CharField(
        max_length=30, choices=BREAKDOWN, default='full_day')
    requested_days = models.FloatField(blank=True, null=True)
    requested_date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(Employee, on_delete=models.PROTECT, blank=True, null=True, related_name='leave_request_created')
    description = models.TextField()
    attachment = models.FileField(
        null=True, blank=True, upload_to='leave/leave_attachment')
    status = models.CharField(
        max_length=30, choices=LEAVE_STATUS, default='requested')
    approved_available_days = models.FloatField(default=0)
    approved_carryforward_days = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now="True")


    def __str__(self):
        return f"{self.employee_id} | {self.leave_type_id} | {self.status}"

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
                            f"{year}-{month:02}-{day:02}", '%Y-%m-%d').date()
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
                                f"{year}-{month:02}-{week[int(based_on_week_day)]:02}", '%Y-%m-%d').date()
                            if date not in company_leave_dates:
                                company_leave_dates.append(date)
        return company_leave_dates


    def save(self, *args, **kwargs):  
        self.requested_days = calculate_requested_days(self.start_date, self.end_date, self.start_date_breakdown, self.end_date_breakdown)
        if self.leave_type_id.exclude_company_leave == 'yes' and self.leave_type_id.exclude_holiday == 'yes':
            self.exclude_all_leaves()
        else:
            self.exclude_leaves()
        super().save(*args, **kwargs)


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
        if self.leave_type_id.exclude_holiday == 'yes':
            requested_dates = self.requested_dates()
            holiday_dates = self.holiday_dates()
            for requested_date in requested_dates:
                if requested_date in holiday_dates:
                    holiday_count += 1
            self.requested_days = self.requested_days - holiday_count
        if self.leave_type_id.exclude_company_leave == 'yes':
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
            leave_type_id=leave_type_id, employee_id=employee_id)
        if self.requested_days > available_leave.available_days:
            leave = self.requested_days - available_leave.available_days
            self.approved_available_days = available_leave.available_days
            available_leave.available_days = 0
            available_leave.carryforward_days = available_leave.carryforward_days - leave
            self.approved_carryforward_days =  leave
        else:
            available_leave.available_days = available_leave.available_days - self.requested_days
            self.approved_available_days = self.requested_days
        self.status = "approved"
        available_leave.save()
