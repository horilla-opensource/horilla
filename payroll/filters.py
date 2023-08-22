"""
Module containing filter set classes for payroll models.

This module defines the filter set classes used for filtering data in the payroll app.
Each filter set class corresponds to a specific model and contains filter fields and methods
to customize the filtering behavior.

"""
import django_filters 
from django import forms
from horilla.filters import filter_by_name
from attendance.filters import FilterSet
from payroll.models.models import Allowance, Contract, Deduction
from payroll.models.models import Payslip


class ContractFilter(FilterSet):
    """
    Filter set class for Contract model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method="filter_by_contract")
    contract_start_date = django_filters.DateFilter(
        field_name="contract_start_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    contract_end_date = django_filters.DateFilter(
        field_name="contract_end_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        """
        Meta class to add additional options
        """

        model = Contract
        fields = [
            "employee_id",
            "contract_name",
            "contract_start_date",
            "contract_end_date",
            "wage_type",
            "filing_status",
            "pay_frequency",
            "contract_status",
        ]

    def filter_by_contract(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        og_queryset = queryset
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
        queryset = queryset | og_queryset.filter(contract_name__icontains=value)
        return queryset


class AllowanceFilter(FilterSet):
    """
    Filter set class for Allowance model.
    """

    search = django_filters.CharFilter(method="filter_by_employee")

    class Meta:
        """
        Meta class to add additional options
        """

        model = Allowance
        fields = [
            "title",
            "is_taxable",
            "is_condition_based",
            "is_fixed",
            "based_on",
        ]

    def filter_by_employee(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        og_queryset = queryset
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        # Filter the queryset by first name and last name
        if first_name and last_name:
            queryset = queryset.filter(
                specific_employees__employee_first_name__icontains=first_name,
                specific_employees__employee_last_name__icontains=last_name,
            )
        elif first_name:
            queryset = queryset.filter(
                specific_employees__employee_first_name__icontains=first_name
            )
        elif last_name:
            queryset = queryset.filter(
                specific_employees__employee_last_name__icontains=last_name
            )
        queryset = queryset | og_queryset.filter(title__icontains=value)
        return queryset


class DeductionFilter(FilterSet):
    """
    Filter set class for Deduction model.
    """

    search = django_filters.CharFilter(method="filter_by_employee")

    class Meta:
        """
        Meta class to add additional options
        """

        model = Deduction
        fields = [
            "title",
            "is_pretax",
            "is_condition_based",
            "is_fixed",
            "based_on",
        ]

    def filter_by_employee(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        og_queryset = queryset
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        # Filter the queryset by first name and last name
        if first_name and last_name:
            queryset = queryset.filter(
                specific_employees__employee_first_name__icontains=first_name,
                specific_employees__employee_last_name__icontains=last_name,
            )
        elif first_name:
            queryset = queryset.filter(
                specific_employees__employee_first_name__icontains=first_name
            )
        elif last_name:
            queryset = queryset.filter(
                specific_employees__employee_last_name__icontains=last_name
            )
        queryset = queryset | og_queryset.filter(title__icontains=value)
        return queryset


class PayslipFilter(FilterSet):
    """
    Filter set class for payslip model.
    """

    search = django_filters.CharFilter(method=filter_by_name)
    start_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    start_date_from = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="start_date",
        lookup_expr="gte",
    )
    start_date_till = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="start_date",
        lookup_expr="lte",
    )
    end_date_from = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="end_date",
        lookup_expr="gte",
    )
    end_date_till = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="end_date",
        lookup_expr="lte",
    )
    gross_pay__lte = django_filters.NumberFilter(
        field_name="gross_pay", lookup_expr="lte"
    )
    gross_pay__gte = django_filters.NumberFilter(
        field_name="gross_pay", lookup_expr="gte"
    )
    deduction__lte = django_filters.NumberFilter(
        field_name="deduction", lookup_expr="lte"
    )
    deduction__gte = django_filters.NumberFilter(
        field_name="deduction", lookup_expr="gte"
    )
    net_pay__lte = django_filters.NumberFilter(field_name="net_pay", lookup_expr="lte")
    net_pay__gte = django_filters.NumberFilter(field_name="net_pay", lookup_expr="gte")
    
    department = django_filters.CharFilter(field_name='employee_id__employee_work_info__department_id__department', lookup_expr='icontains')

    class Meta:
        """
        Meta class to add additional options
        """

        model = Payslip
        fields = [
            "employee_id",
            "start_date",
            "end_date",
            "status",
            "gross_pay__lte",
            "gross_pay__gte",
            "deduction__lte",
            "deduction__gte",
            "net_pay__lte",
            "net_pay__gte",
        ]
