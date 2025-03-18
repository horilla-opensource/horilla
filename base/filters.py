"""
This module contains custom Django filters for filtering querysets related to Shift Requests,
Work Type Requests, Rotating Shift and Rotating Work Type Assign.
"""

import uuid

import django_filters
from django import forms
from django.db.models import Q
from django.utils.translation import gettext as __
from django_filters import CharFilter, DateFilter, FilterSet, filters

from base.models import (
    Announcement,
    AnnouncementView,
    Company,
    CompanyLeaves,
    Department,
    DynamicEmailConfiguration,
    EmailLog,
    EmployeeShift,
    EmployeeShiftSchedule,
    EmployeeType,
    Holidays,
    JobPosition,
    MultipleApprovalCondition,
    PenaltyAccounts,
    RotatingShift,
    RotatingShiftAssign,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    ShiftRequest,
    WorkType,
    WorkTypeRequest,
)
from horilla.filters import FilterSet, HorillaFilterSet, filter_by_name


class ShiftRequestFilter(HorillaFilterSet):
    """
    Custom filter for Shift Requests.
    """

    requested_date = django_filters.DateFilter(
        field_name="requested_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    requested_date__gte = django_filters.DateFilter(
        field_name="requested_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    requested_date__lte = django_filters.DateFilter(
        field_name="requested_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    search = CharFilter(method=filter_by_name)

    requested = django_filters.BooleanFilter(
        method="filter_requested", label="Requested?"
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        fields = "__all__"
        model = ShiftRequest
        fields = [
            "id",
            "employee_id",
            "requested_date",
            "previous_shift_id",
            "shift_id",
            "requested_till",
            "approved",
            "canceled",
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "employee_id__is_active",
            "employee_id__gender",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__employee_type_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
        ]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"

    def filter_requested(self, queryset, name, value):
        """
        Filters the queryset to return entries where 'approved' is False and 'canceled' is False.
        """
        if value:
            return queryset.filter(approved=False, canceled=False)
        return queryset


class WorkTypeRequestFilter(HorillaFilterSet):
    """
    Custom filter for Work Type Requests.
    """

    requested_date = django_filters.DateFilter(
        field_name="requested_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    requested_date__gte = django_filters.DateFilter(
        field_name="requested_till",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    requested_date__lte = django_filters.DateFilter(
        field_name="requested_till",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    requested = django_filters.BooleanFilter(
        method="filter_by_requested", label="Requested"
    )
    search = CharFilter(method=filter_by_name)

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        fields = "__all__"
        model = WorkTypeRequest
        fields = [
            "id",
            "employee_id",
            "requested_date",
            "previous_work_type_id",
            "approved",
            "work_type_id",
            "canceled",
            "employee_id__employee_first_name",
            "employee_id__employee_last_name",
            "employee_id__is_active",
            "employee_id__gender",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__employee_type_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
        ]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"

    def filter_by_requested(self, queryset, name, value):
        """
        Filters the queryset to return entries where 'approved' is False and 'canceled' is False.
        """
        if value:
            return queryset.filter(approved=False, canceled=False)
        return queryset


class RotatingShiftAssignFilters(HorillaFilterSet):
    """
    Custom filter for Rotating Shift Assign.
    """

    search = CharFilter(method=filter_by_name)

    next_change_date = django_filters.DateFilter(
        field_name="next_change_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    start_date = django_filters.DateFilter(
        field_name="start_date", widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        fields = "__all__"
        model = RotatingShiftAssign
        fields = [
            "employee_id",
            "rotating_shift_id",
            "next_change_date",
            "start_date",
            "based_on",
            "rotate_after_day",
            "rotate_every_weekend",
            "rotate_every",
            "current_shift",
            "next_shift",
            "is_active",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__employee_type_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
        ]


class RotatingWorkTypeAssignFilter(HorillaFilterSet):
    """
    Custom filter for Rotating Work Type Assign.
    """

    search = CharFilter(method=filter_by_name)

    next_change_date = django_filters.DateFilter(
        field_name="next_change_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    start_date = django_filters.DateFilter(
        field_name="start_date", widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        fields = "__all__"
        model = RotatingWorkTypeAssign
        fields = [
            "employee_id",
            "rotating_work_type_id",
            "next_change_date",
            "start_date",
            "based_on",
            "rotate_after_day",
            "rotate_every_weekend",
            "rotate_every",
            "current_work_type",
            "next_work_type",
            "is_active",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__work_type_id",
            "employee_id__employee_work_info__employee_type_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__shift_id",
        ]


class ShiftRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("shift_id", "Requested Shift"),
        ("previous_shift_id", "Current Shift"),
        ("requested_date", "Requested Date"),
    ]


class WorkTypeRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("work_type_id", "Requested Work Type"),
        ("previous_work_type_id", "Current Work Type"),
        ("requested_date", "Requested Date"),
        ("employee_id__employee_work_info__department_id", "Department"),
        ("employee_id__employee_work_info__job_position_id", "Job Position"),
        ("employee_id__employee_work_info__reporting_manager_id", "Reporting Manager"),
    ]


class RotatingWorkTypeRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("rotating_work_type_id", "Rotating Work Type"),
        ("current_work_type", "Current Work Type"),
        ("based_on", "Based On"),
        ("employee_id__employee_work_info__department_id", "Department"),
        ("employee_id__employee_work_info__job_role_id", "Job Role"),
        ("employee_id__employee_work_info__reporting_manager_id", "Reporting Manager"),
    ]


class RotatingShiftRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("rotating_shift_id", "Rotating Shift"),
        ("based_on", "Based On"),
        ("employee_id__employee_work_info__department_id", "Department"),
        ("employee_id__employee_work_info__job_role_id", "Job Role"),
        ("employee_id__employee_work_info__reporting_manager_id", "Reporting Manager"),
    ]


class MultipleApprovalConditionFilter(HorillaFilterSet):

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = MultipleApprovalCondition
        fields = [
            "department",
        ]

    def search_method(self, queryset, _, value):
        """
        This method is used to search department
        """

        return (queryset.filter(department__department__icontains=value)).distinct()


class EmployeeShiftFilter(FilterSet):

    search = django_filters.CharFilter(
        field_name="employee_shift", lookup_expr="icontains"
    )

    class Meta:
        model = EmployeeShift
        fields = [
            "employee_shift",
        ]


class EmployeeShiftScheduleFilter(FilterSet):

    search = django_filters.CharFilter(field_name="day__day", lookup_expr="icontains")

    class Meta:
        model = EmployeeShiftSchedule
        fields = []


class RotatingShiftFilter(HorillaFilterSet):

    # search = django_filters.CharFilter(
    #     field_name="name", lookup_expr="icontains"
    # )
    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = RotatingShift
        fields = ["name", "shift1", "shift2"]

    def search_method(self, queryset, _, value):
        """
        This method is used to search employees and objective
        """

        return (
            queryset.filter(name__icontains=value)
            | queryset.filter(shift1__employee_shift__icontains=value)
            | queryset.filter(shift2__employee_shift__icontains=value)
        ).distinct()


class DepartmentViewFilter(HorillaFilterSet):
    search = django_filters.CharFilter(method="filter_by_all_fields")

    class Meta:
        model = Department
        fields = [
            "department",
        ]

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(department__icontains=value)
            | Q(job_position__job_position__icontains=value)
        ).distinct()


class WorkTypeFilter(HorillaFilterSet):

    search = django_filters.CharFilter(field_name="work_type", lookup_expr="icontains")

    class Meta:
        model = WorkType
        fields = [
            "work_type",
        ]


class RotatingWorkTypeFilter(HorillaFilterSet):

    search = django_filters.CharFilter(method="search_method")

    def search_method(self, queryset, _, value):
        """
        This method is used to search employees and objective
        """

        return (
            queryset.filter(name__icontains=value)
            | queryset.filter(work_type1__work_type__icontains=value)
            | queryset.filter(work_type2__work_type__icontains=value)
        ).distinct()

    class Meta:
        model = RotatingWorkType
        fields = ["name", "work_type1", "work_type2"]


class EmployeeTypeFilter(FilterSet):

    search = django_filters.CharFilter(
        field_name="employee_type", lookup_expr="icontains"
    )

    class Meta:
        model = EmployeeType
        fields = [
            "employee_type",
        ]


class JobRoleFilter(HorillaFilterSet):
    search = django_filters.CharFilter(method="filter_by_all_fields")

    class Meta:
        model = JobPosition
        fields = [
            "job_position",
        ]

    def filter_by_all_fields(self, queryset, name, value):
        return queryset.filter(
            Q(job_position__icontains=value) | Q(jobrole__job_role__icontains=value)
        ).distinct()


class CompanyFilter(FilterSet):

    search = CharFilter(method="search_method")

    def search_method(self, queryset, _, value):
        """
        This method is used to search company and objective
        """

        return (
            queryset.filter(company__icontains=value)
            | queryset.filter(hq__icontains=value)
            | queryset.filter(address__icontains=value)
            | queryset.filter(country__icontains=value)
            | queryset.filter(state__icontains=value)
            | queryset.filter(city__icontains=value)
            | queryset.filter(zip__icontains=value)
        ).distinct()

    class Meta:
        model = Company
        fields = ["company", "hq", "address", "country", "state", "city", "zip"]


class MailServerFilter(HorillaFilterSet):

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = DynamicEmailConfiguration
        fields = ["username"]

    def search_method(self, queryset, _, value):
        """
        This method is used to mail server
        """

        return ((queryset.filter(username__icontains=value))).distinct()


class HolidayFilter(HorillaFilterSet):
    """
    Filter class for Holidays model.

    This filter allows searching Holidays objects based on name and date range.
    """

    search = filters.CharFilter(field_name="name", lookup_expr="icontains")
    from_date = DateFilter(
        field_name="start_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    to_date = DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    start_date = DateFilter(
        field_name="start_date",
        lookup_expr="exact",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date = DateFilter(
        field_name="end_date",
        lookup_expr="exact",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        """
        Meta class defines the model and fields to filter
        """

        model = Holidays
        fields = {
            "recurring": ["exact"],
        }

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"


class CompanyLeaveFilter(HorillaFilterSet):
    """
    Filter class for CompanyLeaves model.

    This filter allows searching CompanyLeaves objects based on
    name, week day and based_on_week choices.
    """

    name = filters.CharFilter(field_name="based_on_week_day", lookup_expr="icontains")
    search = filters.CharFilter(method="filter_week_day")

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = CompanyLeaves
        fields = {
            "based_on_week": ["exact"],
            "based_on_week_day": ["exact"],
        }

    def filter_week_day(self, queryset, _, value):
        week_qry = CompanyLeaves.objects.none()
        weekday_values = []
        week_values = []
        WEEK_DAYS = [
            ("0", __("Monday")),
            ("1", __("Tuesday")),
            ("2", __("Wednesday")),
            ("3", __("Thursday")),
            ("4", __("Friday")),
            ("5", __("Saturday")),
            ("6", __("Sunday")),
        ]
        WEEKS = [
            (None, __("All")),
            ("0", __("First Week")),
            ("1", __("Second Week")),
            ("2", __("Third Week")),
            ("3", __("Fourth Week")),
            ("4", __("Fifth Week")),
        ]

        for day_value, day_name in WEEK_DAYS:
            if value.lower() in day_name.lower():
                weekday_values.append(day_value)
        for day_value, day_name in WEEKS:
            if value.lower() in day_name.lower() and value.lower() != __("All").lower():
                week_values.append(day_value)
                week_qry = queryset.filter(based_on_week__in=week_values)
            elif value.lower() in __("All").lower():
                week_qry = queryset.filter(based_on_week__isnull=True)
        return queryset.filter(based_on_week_day__in=weekday_values) | week_qry


class PenaltyFilter(FilterSet):
    """
    PenaltyFilter
    """

    class Meta:
        model = PenaltyAccounts
        fields = "__all__"


class MailLogFilter(HorillaFilterSet):

    search = django_filters.CharFilter(field_name="subject", lookup_expr="icontains")

    class Meta:
        model = EmailLog
        fields = "__all__"


class AnnouncementFilter(HorillaFilterSet):

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = Announcement
        fields = "__all__"


class AnnouncementViewFilter(HorillaFilterSet):

    search = django_filters.CharFilter(
        field_name="announcement", lookup_expr="icontains"
    )

    class Meta:
        model = AnnouncementView
        fields = "__all__"
