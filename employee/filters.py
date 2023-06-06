"""
filters.py

This page is used to register filter for employee models

"""
import django_filters
from django.contrib.auth.models import Permission, Group
from horilla.filters import FilterSet
from employee.models import Employee


class EmployeeFilter(FilterSet):
    """
    Filter set class for Candidate model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """
    search = django_filters.CharFilter(method="filter_by_name")

    employee_first_name = django_filters.CharFilter(lookup_expr="icontains")
    employee_last_name = django_filters.CharFilter(lookup_expr="icontains")
    country = django_filters.CharFilter(lookup_expr="icontains")

    user_permissions = django_filters.ModelMultipleChoiceFilter(
        queryset=Permission.objects.all(),
    )
    groups = django_filters.ModelMultipleChoiceFilter(
        queryset=Group.objects.all(),
    )

    class Meta:
        """
        Meta class to add the additional info
        """
        model = Employee
        fields = [
            "employee_first_name",
            "employee_last_name",
            "email",
            "badge_id",
            "phone",
            "country",
            "gender",
            "is_active",
            "employee_work_info__job_position_id",
            "employee_work_info__department_id",
            "employee_work_info__work_type_id",
            "employee_work_info__employee_type_id",
            "employee_work_info__job_role_id",
            "employee_work_info__reporting_manager_id",
            "employee_work_info__company_id",
            "employee_work_info__shift_id",
        ]

    def filter_by_name(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        # Filter the queryset by first name and last name
        if first_name and last_name:
            queryset = queryset.filter(
                employee_first_name__icontains=first_name,
                employee_last_name__icontains=last_name,
            )
        elif first_name:
            queryset = queryset.filter(employee_first_name__icontains=first_name)
        elif last_name:
            queryset = queryset.filter(employee_last_name__icontains=last_name)
        return queryset

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        self.form.initial["is_active"] = True
