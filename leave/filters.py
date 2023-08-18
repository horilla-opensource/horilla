"""
This module contains custom filter classes used for filtering 
various models in the Leave Management System app.
The filters are designed to provide flexible search and filtering 
capabilities for LeaveType, LeaveRequest,AvailableLeave, Holiday, and CompanyLeave models.
"""
from django import forms
from django_filters import FilterSet, DateFilter, filters
from .models import LeaveType, LeaveRequest, AvailableLeave, Holiday, CompanyLeave


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

    leave_type = filters.CharFilter(
        field_name="leave_type_id__name", lookup_expr="icontains"
    )
    employee_id = filters.CharFilter(
        field_name="employee_id__employee_first_name", lookup_expr="icontains"
    )
    assigned_date = DateFilter(
        field_name="assigned_date",
        lookup_expr="exact",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = AvailableLeave
        fields = {
            "leave_type_id": ["exact"],
        }


class LeaveRequestFilter(FilterSet):
    """
    Filter class for LeaveRequest model.
    This filter allows searching LeaveRequest objects based on employee,
    date range, leave type, and status.
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


class CompanyLeaveFilter(FilterSet):
    """
    Filter class for CompanyLeave model.

    This filter allows searching CompanyLeave objects based on
    name, week day and based_on_week choices.
    """

    name = filters.CharFilter(field_name="based_on_week_day", lookup_expr="icontains")

    class Meta:
        """ "
        Meta class defines the model and fields to filter
        """

        model = CompanyLeave
        fields = {
            "based_on_week": ["exact"],
            "based_on_week_day": ["exact"],
        }


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
        """ "
        Meta class defines the model and fields to filter
        """

        model = LeaveRequest
        fields = {
            "leave_type_id": ["exact"],
            "status": ["exact"],
        }
