"""
Module containing filter set classes for payroll models.

This module defines the filter set classes used for filtering data in the payroll app.
Each filter set class corresponds to a specific model and contains filter fields and methods
to customize the filtering behavior.

"""

import uuid

import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _

from base.filters import FilterSet
from employee.models import Employee
from horilla.filters import filter_by_name
from payroll.models.models import (
    Allowance,
    Contract,
    Deduction,
    FilingStatus,
    LoanAccount,
    Payslip,
    Reimbursement,
)


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
    contract_start_date_from = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="contract_start_date",
        lookup_expr="gte",
    )
    contract_start_date_till = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="contract_start_date",
        lookup_expr="lte",
    )
    contract_end_date_from = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="contract_end_date",
        lookup_expr="gte",
    )
    contract_end_date_till = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="contract_end_date",
        lookup_expr="lte",
    )
    basic_pay__lte = django_filters.NumberFilter(field_name="wage", lookup_expr="lte")
    basic_pay__gte = django_filters.NumberFilter(field_name="wage", lookup_expr="gte")

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
            "employee_id__employee_work_info__company_id",
            "department",
            "job_position",
            "job_role",
            "shift",
            "work_type",
            "pay_frequency",
            "contract_status",
            "wage",
        ]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"

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
            "amount",
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
        return queryset.distinct()


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
            "amount",
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
        return queryset.distinct()


class PayslipFilter(FilterSet):
    """
    Filter set class for payslip model.
    """

    search = django_filters.CharFilter(method=filter_by_name)
    employee_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Employee.objects.all(),
        widget=forms.SelectMultiple(),
    )
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

    department = django_filters.CharFilter(
        field_name="employee_id__employee_work_info__department_id__department",
        lookup_expr="icontains",
    )
    month = django_filters.CharFilter(field_name="start_date", lookup_expr="month")
    year = django_filters.CharFilter(field_name="start_date", lookup_expr="year")

    allowance_title = django_filters.CharFilter(
        method="filter_by_allowance_title", label="Allowance Title"
    )
    allowance_amount_gte = django_filters.NumberFilter(
        method="filter_by_allowance_amount_gte"
    )
    allowance_amount_lte = django_filters.NumberFilter(
        method="filter_by_allowance_amount_lte"
    )
    deduction_amount_gte = django_filters.NumberFilter(
        method="filter_by_deduction_amount_gte"
    )
    deduction_amount_lte = django_filters.NumberFilter(
        method="filter_by_deduction_amount_lte"
    )

    class Meta:
        """
        Meta class to add additional options
        """

        model = Payslip
        fields = [
            "employee_id",
            "start_date",
            "end_date",
            "group_name",
            "status",
            "gross_pay__lte",
            "gross_pay__gte",
            "deduction__lte",
            "deduction__gte",
            "net_pay__lte",
            "net_pay__gte",
            "sent_to_employee",
            "allowance_amount_gte",
            "allowance_amount_lte",
            "deduction_amount_gte",
            "deduction_amount_lte",
        ]

    def filter_by_allowance_amount_gte(self, queryset, name, value):
        return queryset.filter(
            id__in=[
                p.id
                for p in queryset
                if any(
                    float(allowance.get("amount", 0)) >= float(value)
                    for allowance in (p.pay_head_data or {}).get("allowances", [])
                )
            ]
        )

    def filter_by_allowance_amount_lte(self, queryset, name, value):
        return queryset.filter(
            id__in=[
                p.id
                for p in queryset
                if all(
                    float(allowance.get("amount", 0)) <= float(value)
                    for allowance in (p.pay_head_data or {}).get("allowances", [])
                )
            ]
        )

    def filter_by_deduction_amount_lte(self, queryset, name, value):
        value = float(value)
        deduction_keys = [
            "pretax_deductions",
            "gross_pay_deductions",
            "basic_pay_deductions",
            "post_tax_deductions",
            "tax_deductions",
            "net_deductions",
        ]

        return queryset.filter(
            id__in=[
                p.id
                for p in queryset
                if all(
                    float(d.get("amount", 0)) <= value
                    for key in deduction_keys
                    for d in (p.pay_head_data or {}).get(key, [])
                )
            ]
        )

    def filter_by_deduction_amount_gte(self, queryset, name, value):
        value = float(value)
        deduction_keys = [
            "pretax_deductions",
            "gross_pay_deductions",
            "basic_pay_deductions",
            "post_tax_deductions",
            "tax_deductions",
            "net_deductions",
        ]

        return queryset.filter(
            id__in=[
                p.id
                for p in queryset
                if any(
                    float(d.get("amount", 0)) >= value
                    for key in deduction_keys
                    for d in (p.pay_head_data or {}).get(key, [])
                )
            ]
        )

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)
        for field in self.form.fields.keys():
            self.form.fields[field].widget.attrs["id"] = f"{uuid.uuid4()}"


class LoanAccountFilter(FilterSet):
    """
    LoanAccountFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    search_employee = django_filters.CharFilter(method=filter_by_name)
    provided_date = django_filters.DateFilter(
        widget=forms.DateInput(attrs={"type": "date"}),
        field_name="provided_date",
    )

    class Meta:
        model = LoanAccount
        fields = [
            "search",
            "search_employee",
            "provided_date",
            "settled",
            "type",
            "employee_id",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__reporting_manager_id",
        ]


class ReimbursementFilter(FilterSet):
    """
    ReimbursementFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = Reimbursement
        fields = [
            "id",
            "status",
            "type",
            "employee_id",
            "approved_by",
            "employee_id__employee_work_info__department_id",
            "employee_id__employee_work_info__job_position_id",
            "employee_id__employee_work_info__reporting_manager_id",
        ]


class ContractReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", _("Select")),
        ("employee_id", _("Employee")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("contract_status", _("Status")),
        ("employee_id__employee_work_info__shift_id", _("Shift")),
        ("employee_id__employee_work_info__work_type_id", _("Work Type")),
        ("employee_id__employee_work_info__job_role_id", _("Job Role")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


class PayslipReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", _("Select")),
        ("employee_id", _("Employee")),
        ("group_name", _("Payslip Batch")),
        ("start_date", _("Start Date")),
        ("end_date", _("End Date")),
        ("basic_pay", _("Basic Pay")),
        ("gross_pay", _("Gross Pay")),
        ("net_pay", _("Net Pay")),
        ("status", _("Status")),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__job_role_id", _("Job Role")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]
