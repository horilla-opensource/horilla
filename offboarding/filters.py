"""
offboarding/filters.py

This module is used to register django_filters
"""
import django_filters
from django import forms
from base.filters import FilterSet
from offboarding.models import ResignationLetter


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
