"""
This module contains custom Django filters for filtering querysets related to Shift Requests,
Work Type Requests, Rotating Shift and Rotating Work Type Assign.
"""

import uuid

import django_filters
from django import forms
from django_filters import CharFilter

from base.models import (
    RotatingShiftAssign,
    RotatingWorkTypeAssign,
    ShiftRequest,
    WorkTypeRequest,
)
from horilla.filters import FilterSet, filter_by_name


class ShiftRequestFilter(FilterSet):
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


class WorkTypeRequestFilter(FilterSet):
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


class RotatingShiftAssignFilters(FilterSet):
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


class RotatingWorkTypeAssignFilter(FilterSet):
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
