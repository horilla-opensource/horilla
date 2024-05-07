"""
offboarding/filters.py

This module is used to register django_filters
"""

import uuid

import django_filters
from django import forms

from base.filters import FilterSet
from offboarding.models import (
    Offboarding,
    OffboardingEmployee,
    OffboardingStage,
    ResignationLetter,
)


class LetterFilter(FilterSet):
    """
    LetterFilter class
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    planned_to_leave_on = django_filters.DateFilter(
        field_name="planned_to_leave_on",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = ResignationLetter
        fields = [
            "status",
            "employee_id",
            "planned_to_leave_on",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__reporting_manager_id",
        ]


class PipelineFilter(FilterSet):
    """
    PipelineFilter
    """

    search = django_filters.CharFilter(method="search_method", lookup_expr="icontains")

    class Meta:
        model = Offboarding
        fields = "__all__"

    def search_method(self, queryset, _, value):
        """
        This method is used to add custom search condition
        """
        return (
            queryset.filter(title__icontains=value)
            | queryset.filter(offboardingstage__title__icontains=value)
            | queryset.filter(
                offboardingstage__offboardingemployee__employee_id__employee_first_name__icontains=value
            )
        ).distinct()


class PipelineStageFilter(FilterSet):
    """
    PipelineStageFilter
    """

    search = django_filters.CharFilter(method="search_method", lookup_expr="icontains")

    class Meta:
        model = OffboardingStage
        fields = "__all__"
        exclude = [
            "sequence",
        ]

    def search_method(self, queryset, _, value):
        """
        This method is used to add custom search condition
        """

        return (
            queryset.filter(title__icontains=value)
            | queryset.filter(
                offboardingemployee__employee_id__employee_first_name__icontains=value
            )
            | queryset.filter(offboarding_id__title__icontains=value)
        ).distinct()


class PipelineEmployeeFilter(FilterSet):
    """
    PipelineEmployeeFilter
    """

    search = django_filters.CharFilter(method="search_method", lookup_expr="icontains")

    notice_period_starts = django_filters.DateFilter(
        field_name="notice_period_starts",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    notice_period_ends = django_filters.DateFilter(
        field_name="notice_period_ends",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = OffboardingEmployee
        fields = [
            "stage_id",
            "employee_id__gender",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__job_role_id",
            "employee_id__employee_work_info__employee_type_id",
            "employee_id__employee_work_info__shift_id",
            "employee_id__employee_work_info__work_type_id",
        ]

    def search_method(self, queryset, _, value):
        """
        This method is used to add custom search condition
        """
        return (
            queryset.filter(employee_id__employee_first_name__icontains=value)
            | queryset.filter(stage_id__title__icontains=value)
            | queryset.filter(stage_id__offboarding_id__title__icontains=value)
        ).distinct()


class LetterReGroup(FilterSet):
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", "Employee"),
        ("planned_to_leave_on", "Planned to leave date"),
        ("status", "Status"),
        ("employee_id__employee_work_info__department_id", "Department"),
        ("employee_id__employee_work_info__job_position_id", "Job Position"),
        ("employee_id__employee_work_info__reporting_manager_id", "Reporting Manager"),
    ]
