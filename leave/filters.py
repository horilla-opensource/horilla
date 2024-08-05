"""
This module contains custom filter classes used for filtering
various models in the Leave Management System app.
The filters are designed to provide flexible search and filtering
capabilities for LeaveType, LeaveRequest and AvailableLeave models.
"""

import uuid
from datetime import datetime, timedelta

import django_filters
from django import forms
from django.apps import apps
from django.db.models import Q
from django.db.models.functions import TruncYear
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django_filters import DateFilter, FilterSet, NumberFilter, filters

from base.filters import FilterSet
from employee.models import Employee

from .models import (
    AvailableLeave,
    LeaveAllocationRequest,
    LeaveRequest,
    LeaveType,
    RestrictLeave,
)


class LeaveTypeFilter(FilterSet):
    """
    Filter class for LeaveType model.

    This filter allows searching LeaveType objects based on their name and payment attributes.
    """

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    search = filters.CharFilter(field_name="name", lookup_expr="icontains")
    carry_forward_gte = filters.CharFilter(
        field_name="carryforward_max", lookup_expr="gte"
    )
    carry_forward_lte = filters.CharFilter(
        field_name="carryforward_max", lookup_expr="lte"
    )
    total_days_gte = filters.CharFilter(field_name="total_days", lookup_expr="gte")
    total_days_lte = filters.CharFilter(field_name="total_days", lookup_expr="lte")

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = LeaveType
        fields = "__all__"
        exclude = ["icon"]


class AssignedLeaveFilter(FilterSet):
    """
    Filter class for AvailableLeave model.

    This filter allows searching AvailableLeave objects based on leave type,
    employee, assigned date and payment attributes.
    """

    # leave_type = filters.CharFilter(
    #     field_name="leave_type_id__name", lookup_expr="icontains"
    # )
    search = filters.CharFilter(
        field_name="employee_id__employee_first_name", lookup_expr="icontains"
    )
    employee_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple(),
    )
    assigned_date = DateFilter(
        field_name="assigned_date",
        lookup_expr="exact",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    available_days__gte = NumberFilter(field_name="available_days", lookup_expr="gte")
    available_days__lte = NumberFilter(field_name="available_days", lookup_expr="lte")
    carryforward_days__gte = NumberFilter(
        field_name="carryforward_days", lookup_expr="gte"
    )
    carryforward_days__lte = NumberFilter(
        field_name="carryforward_days", lookup_expr="lte"
    )
    total_leave_days__gte = NumberFilter(
        field_name="total_leave_days", lookup_expr="gte"
    )
    total_leave_days__lte = NumberFilter(
        field_name="total_leave_days", lookup_expr="lte"
    )

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = AvailableLeave
        fields = [
            "employee_id",
            "leave_type_id",
            "available_days",
            "available_days__gte",
            "available_days__lte",
            "carryforward_days",
            "carryforward_days__gte",
            "carryforward_days__lte",
            "total_leave_days",
            "total_leave_days__gte",
            "total_leave_days__lte",
            "assigned_date",
        ]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"


class LeaveRequestFilter(FilterSet):
    """
    Filter class for LeaveRequest model.
    This filter allows searching LeaveRequest objects
    based on employee,date range, leave type, and status.
    """

    overall_leave = django_filters.CharFilter(method="overall_leave_filter")

    search = django_filters.CharFilter(method="filter_by_name")
    from_date = DateFilter(
        field_name="end_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    to_date = DateFilter(
        field_name="start_date",
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
    department_name = django_filters.CharFilter(
        field_name="employee_id__employee_work_info__department_id__department",
        lookup_expr="icontains",
    )

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = LeaveRequest
        fields = [
            "id",
            "employee_id",
            "leave_type_id",
            "status",
            "department_name",
            "overall_leave",
            "employee_id__employee_work_info__company_id",
            "employee_id__employee_work_info__reporting_manager_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__shift_id",
            "employee_id__employee_work_info__work_type_id",
        ]

    def overall_leave_filter(self, queryset, _, value):
        """
        Overall leave custom filter method
        """
        today = datetime.today()

        today_leave_requests = queryset.filter(
            Q(start_date__lte=today) & Q(end_date__gte=today) & Q(status="approved")
        )
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        weekly_leave_requests = queryset.filter(
            status="approved", start_date__lte=end_of_week, end_date__gte=start_of_week
        )
        start_of_month = today.replace(day=1)
        end_of_month = start_of_month.replace(day=28) + timedelta(days=4)
        if end_of_month.month != today.month:
            end_of_month = end_of_month - timedelta(days=end_of_month.day)
        monthly_leave_requests = queryset.filter(
            status="approved",
            start_date__lte=end_of_month,
            end_date__gte=start_of_month,
        )
        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)
        yearly_leave_requests = (
            queryset.filter(
                status="approved",
                start_date__lte=end_of_year,
                end_date__gte=start_of_year,
            )
            .annotate(year=TruncYear("start_date"))
            .filter(year=start_of_year)
        )
        if value == "month":
            queryset = monthly_leave_requests
        elif value == "week":
            queryset = weekly_leave_requests
        elif value == "year":
            queryset = yearly_leave_requests
        else:
            queryset = today_leave_requests
        return queryset

    def filter_by_name(self, queryset, name, value):
        # Call the imported function
        filter_method = {
            "leave_type": "leave_type_id__name__icontains",
            "status": "status__icontains",
            "department": "employee_id__employee_work_info__department_id__department__icontains",
            "job_position": "employee_id__employee_work_info__job_position_id__job_position__icontains",
            "company": "employee_id__employee_work_info__company_id__company__icontains",
        }
        search_field = self.data.get("search_field")
        if not search_field:
            parts = value.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

            # Filter the queryset by first name and last name
            if first_name and last_name:
                queryset = queryset.filter(
                    employee_id__employee_first_name__icontains=first_name,
                    employee_id__employee_last_name__icontains=last_name,
                )
            elif first_name:
                queryset = queryset.filter(
                    employee_id__employee_first_name__icontains=first_name
                )
            elif last_name:
                queryset = queryset.filter(
                    employee_id__employee_last_name__icontains=last_name
                )
        else:
            filter = filter_method.get(search_field)
            queryset = queryset.filter(**{filter: value})

        return queryset

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"


class UserLeaveRequestFilter(FilterSet):
    """
    Filter class for LeaveRequest model specific to user leave requests.
    This filter allows searching user-specific LeaveRequest objects
    based on leave type, date range, and status.
    """

    leave_type = filters.CharFilter(
        field_name="leave_type_id__name", lookup_expr="icontains"
    )
    from_date = DateFilter(
        field_name="end_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    to_date = DateFilter(
        field_name="start_date",
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

        model = LeaveRequest
        fields = {
            "leave_type_id": ["exact"],
            "status": ["exact"],
        }

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        from horilla.horilla_middlewares import _thread_locals

        request = getattr(_thread_locals, "request", None)
        leave_requests = request.user.employee_get.leaverequest_set.all()
        assigned_leave_types = LeaveType.objects.filter(
            id__in=leave_requests.values_list("leave_type_id", flat=True)
        )
        self.form.fields["leave_type_id"].queryset = assigned_leave_types


class LeaveAllocationRequestFilter(FilterSet):
    """
    Filter class for LeaveAllocationRequest model specific to user leave requests.
    This filter allows searching user-specific LeaveRequest objects
    based on leave type, date range, and status.
    """

    id = django_filters.NumberFilter(field_name="id")

    leave_type = filters.CharFilter(
        field_name="leave_type_id__name", lookup_expr="icontains"
    )
    search = filters.CharFilter(
        field_name="employee_id__employee_first_name", lookup_expr="icontains"
    )
    number_of_days_up_to = filters.NumberFilter(
        field_name="requested_days", lookup_expr="lte"
    )
    number_of_days_more_than = filters.NumberFilter(
        field_name="requested_days", lookup_expr="gte"
    )

    class Meta:
        """
        Meta class defines the model and fields to filter
        """

        model = LeaveAllocationRequest
        fields = {
            "id": ["exact"],
            "created_by": ["exact"],
            "status": ["exact"],
            "leave_type_id": ["exact"],
            "employee_id": ["exact"],
        }


class LeaveRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", _("Select")),
        ("employee_id", _("Employee")),
        ("leave_type_id", _("Leave Type")),
        ("start_date", _("Start Date")),
        ("status", _("Status")),
        ("requested_days", _("Requested Days")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employment Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


class MyLeaveRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", _("Select")),
        ("leave_type_id", _("Leave Type")),
        ("status", _("Status")),
        ("requested_days", _("Requested Days")),
    ]


class LeaveAssignReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", _("Select")),
        ("employee_id", _("Employee")),
        ("leave_type_id", _("Leave Type")),
        ("available_days", _("Available Days")),
        ("carryforward_days", _("Carry Forward Days")),
        ("total_leave_days", _("Total Leave Days Days")),
        ("assigned_date", _("Assigned Date")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employment Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


class LeaveAllocationRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", _("Select")),
        ("employee_id", _("Employee")),
        ("leave_type_id", _("Leave Type")),
        ("status", _("Status")),
        ("requested_days", _("Requested Days")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employment Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


class RestrictLeaveFilter(FilterSet):
    """
    Filter class for Restrict model.

    This filter allows searching Restrictleave objects based on name and date range.
    """

    search = filters.CharFilter(field_name="title", lookup_expr="icontains")
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

    class Meta:
        """
        Meta class defines the model and fields to filter
        """

        model = RestrictLeave
        fields = "__all__"

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"


if apps.is_installed("attendance"):
    from .models import CompensatoryLeaveRequest

    class CompensatoryLeaveRequestFilter(FilterSet):
        """
        Filter class for CompensatoryLeaveRequest model specific to user leave requests.
        This filter allows searching user-specific LeaveRequest objects
        based on leave type, date range, and status.
        """

        id = django_filters.NumberFilter(field_name="id")

        leave_type = filters.CharFilter(
            field_name="leave_type_id__name", lookup_expr="icontains"
        )
        search = filters.CharFilter(method="filter_by_name")
        created_by__employee_get = django_filters.CharFilter(
            field_name="created_by__employee_get",
            lookup_expr="exact",
            widget=forms.SelectMultiple(attrs={"class": "form-control"}),
        )
        number_of_days_up_to = filters.NumberFilter(
            field_name="requested_days", lookup_expr="lte"
        )
        number_of_days_more_than = filters.NumberFilter(
            field_name="requested_days", lookup_expr="gte"
        )

        class Meta:
            """
            Meta class defines the model and fields to filter
            """

            model = CompensatoryLeaveRequest
            fields = {
                "id": ["exact"],
                "created_by__employee_get": ["exact"],
                "status": ["exact"],
                "leave_type_id": ["exact"],
                "employee_id": ["exact"],
            }

        def filter_by_name(self, queryset, name, value):
            # Call the imported function
            filter_method = {
                "leave_type": "leave_type_id__name__icontains",
                "status": "status__icontains",
                "department": "employee_id__employee_work_info__department_id__department__icontains",
                "job_position": "employee_id__employee_work_info__job_position_id__job_position__icontains",
                "company": "employee_id__employee_work_info__company_id__company__icontains",
            }
            search_field = self.data.get("search_field")
            if not search_field:
                parts = value.split()
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

                # Filter the queryset by first name and last name
                if first_name and last_name:
                    queryset = queryset.filter(
                        employee_id__employee_first_name__icontains=first_name,
                        employee_id__employee_last_name__icontains=last_name,
                    )
                elif first_name:
                    queryset = queryset.filter(
                        employee_id__employee_first_name__icontains=first_name
                    )
                elif last_name:
                    queryset = queryset.filter(
                        employee_id__employee_last_name__icontains=last_name
                    )
            else:
                filter = filter_method.get(search_field)
                queryset = queryset.filter(**{filter: value})

            return queryset
