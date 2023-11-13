"""
This module contains custom filter classes used for filtering 
various models in the Leave Management System app.
The filters are designed to provide flexible search and filtering 
capabilities for LeaveType, LeaveRequest,AvailableLeave, Holiday, and CompanyLeave models.
"""
import uuid
from django import forms
import django_filters
from django_filters import FilterSet, DateFilter, filters, NumberFilter
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as __
from employee.models import Employee
from .models import (
    LeaveType,
    LeaveRequest,
    AvailableLeave,
    Holiday,
    CompanyLeave,
    LeaveAllocationRequest,
)


class FilterSet(FilterSet):
    """
    Custom FilterSet class for styling filter widgets.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                filter_widget.field.widget.attrs.update(
                    {"class": "oh-switch__checkbox"}
                )
            elif isinstance(widget, (forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )


class LeaveTypeFilter(FilterSet):
    """
    Filter class for LeaveType model.

    This filter allows searching LeaveType objects based on their name and payment attributes.
    """

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = LeaveType
        fields = {
            "payment": ["exact"],
        }


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

    employee_id = filters.CharFilter(
        field_name="employee_id__employee_first_name", lookup_expr="icontains"
    )
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
        """ "
        Meta class defines the model and fields to filter
        """

        model = LeaveRequest
        fields = {
            "leave_type_id": ["exact"],
            "status": ["exact"],
        }


class HolidayFilter(FilterSet):
    """
    Filter class for Holiday model.

    This filter allows searching Holiday objects based on name and date range.
    """

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
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
        """ "
        Meta class defines the model and fields to filter
        """

        model = Holiday
        fields = {
            "recurring": ["exact"],
        }

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"


class CompanyLeaveFilter(FilterSet):
    """
    Filter class for CompanyLeave model.

    This filter allows searching CompanyLeave objects based on
    name, week day and based_on_week choices.
    """

    name = filters.CharFilter(field_name="based_on_week_day", lookup_expr="icontains")
    search = filters.CharFilter(method="filter_week_day")

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = CompanyLeave
        fields = {
            "based_on_week": ["exact"],
            "based_on_week_day": ["exact"],
        }

    def filter_week_day(self, queryset, _, value):
        week_qry = CompanyLeave.objects.none()
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

        model = LeaveRequest
        fields = {
            "leave_type_id": ["exact"],
            "status": ["exact"],
        }


class LeaveAllocationRequestFilter(FilterSet):
    """
    Filter class for LeaveAllocationRequest model specific to user leave requests.
    This filter allows searching user-specific LeaveRequest objects
    based on leave type, date range, and status.
    """

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
        ("", "select"),
        ("employee_id", "Employee"),
        ("leave_type_id", "Leave Type"),
        ("start_date", "Start Date"),
        ("status", "Status"),
        ("requested_days", "Requested Days"),
        ("employee_id.employee_work_info.reporting_manager_id", "Reporting Manager"),
        ("employee_id.employee_work_info.department_id", "Department"),
        ("employee_id.employee_work_info.job_position_id", "Job Position"),
        ("employee_id.employee_work_info.employee_type_id", "Employment Type"),
        ("employee_id.employee_work_info.company_id", "Company"),
    ]


class MyLeaveRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("leave_type_id", "Leave Type"),
        ("status", "Status"),
        ("requested_days", "Requested Days"),
    ]


class LeaveAssignReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("employee_id", "Employee"),
        ("leave_type_id", "Leave Type"),
        ("available_days", "Available Days"),
        ("carryforward_days", "Carry Forward Days"),
        ("total_leave_days", "Total Leave Days Days"),
        ("assigned_date", "Assigned Date"),
    ]


class LeaveAllocationRequestReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("employee_id", "Employee"),
        ("leave_type_id", "Leave Type"),
        ("status", "Status"),
        ("requested_days", "Requested Days"),
        ("employee_id.employee_work_info.reporting_manager_id", "Reporting Manager"),
        ("employee_id.employee_work_info.department_id", "Department"),
        ("employee_id.employee_work_info.job_position_id", "Job Position"),
        ("employee_id.employee_work_info.employee_type_id", "Employment Type"),
        ("employee_id.employee_work_info.company_id", "Company"),
    ]
