"""
This page is handling the cbv methods of allowance and deduction in employee profile page.
"""

import operator
from typing import Any

from django.apps import apps
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from employee.models import Employee
from employee.views import return_none
from horilla_views.cbv_methods import login_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaListView,
    HorillaTabView,
)
from payroll.cbv.allowances import AllowanceListView
from payroll.cbv.deduction import DeductionListView
from payroll.methods.payslip_calc import dynamic_attr
from payroll.models.models import Allowance, Deduction

operator_mapping = {
    "equal": operator.eq,
    "notequal": operator.ne,
    "lt": operator.lt,
    "gt": operator.gt,
    "le": operator.le,
    "ge": operator.ge,
    "icontains": operator.contains,
    "range": return_none,
}


class AllowanceDeductionTabView(HorillaTabView):
    """
    generic tab view for allowance and deduction
    """

    def get_context_data(self, **kwargs):
        """
        Adds tab information for allowances and deductions, including actions for adding bonuses
        """

        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        context["tabs"] = [
            {
                "title": _("Allowances"),
                "url": f"{reverse('allowance-tab-list',kwargs={'pk': pk})}",
                "actions": [
                    {
                        "action": "Add Bonus",
                        "attrs": f"""
                            hx-get="{reverse('add-bonus')}?employee_id={pk}"
                            hx-target="#addBonusModalBody"
                            data-toggle="oh-modal-toggle"
                            data-target="#addBonusModal"
                        """,
                    }
                ],
            },
            {
                "title": _("Deductions"),
                "url": f"{reverse('deduction-tab-list',kwargs={'pk': pk })}",
            },
        ]
        return context


class AllowanceTabList(AllowanceListView):
    """
    list view for allowance tab
    """

    template_name = "cbv/allowance_deduction/allowance_deduction.html"
    records_per_page = 5

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "allowance_tab_id"
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("allowance-tab-list", kwargs={"pk": pk})

    columns = [
        col
        for col in AllowanceListView.columns
        if col[1]
        not in (
            "get_specific_employees",
            "get_exclude_employees",
            "condition_based_display",
            "rate",
        )
    ]

    # row_status_class = None
    row_status_indications = None

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(AllowanceListView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs: Any):
        """
        Adds active contract details and basic pay for a specified employee
        to the context
        """

        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        self.request.emp_id = pk
        self.request.allowance_div = None
        self.request.allowance_tab_id = "allowance_tab_id"
        employee = Employee.objects.get(id=pk)
        active_contracts = (
            employee.contract_set.filter(contract_status="active").first()
            if apps.is_installed("payroll")
            else None
        )
        basic_pay = active_contracts.wage if active_contracts else None
        context["active_contracts"] = active_contracts
        context["basic_pay"] = basic_pay
        return context

    def get_queryset(self):
        """
        Returns a filtered queryset of allowance based on
        the employee's active contract and specific conditions
        """

        queryset = HorillaListView.get_queryset(self)
        pk = self.kwargs.get("pk")
        employee = Employee.objects.get(id=pk)
        active_contracts = (
            employee.contract_set.filter(contract_status="active").first()
            if apps.is_installed("payroll")
            else None
        )
        basic_pay = active_contracts.wage if active_contracts else None
        employee_allowances = []

        if basic_pay:
            specific_allowances = queryset.filter(specific_employees=employee)
            conditional_allowances = queryset.filter(is_condition_based=True).exclude(
                exclude_employees=employee
            )
            active_employees = queryset.filter(include_active_employees=True).exclude(
                exclude_employees=employee
            )

            combined_allowances = (
                specific_allowances | conditional_allowances | active_employees
            )
            combined_allowances = combined_allowances.distinct()

            for allowance in combined_allowances:
                if allowance.is_condition_based:
                    condition_field = allowance.field
                    condition_operator = allowance.condition
                    condition_value = allowance.value.lower().replace(" ", "_")
                    employee_value = dynamic_attr(employee, condition_field)

                    operator_func = operator_mapping.get(condition_operator)
                    if employee_value is not None:
                        condition_value = type(employee_value)(condition_value)
                        if operator_func(employee_value, condition_value):
                            employee_allowances.append(allowance)
                else:
                    employee_allowances.append(allowance)

            filtered_allowances = []
            for allowance in employee_allowances:
                operator_func = operator_mapping.get(allowance.if_condition)
                condition_value = basic_pay if allowance.if_choice == "basic_pay" else 0
                if operator_func(condition_value, allowance.if_amount):
                    filtered_allowances.append(allowance)

            queryset = queryset.filter(
                id__in=[allowance.id for allowance in filtered_allowances]
            )
        else:
            queryset = queryset.none()

        return queryset


class DeductionTab(DeductionListView):
    """
    list view for deduction tab
    """

    @method_decorator(login_required, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super(DeductionListView, self).dispatch(*args, **kwargs)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.view_id = "deduct-div"
        pk = self.request.resolver_match.kwargs.get("pk")
        self.search_url = reverse("deduction-tab-list", kwargs={"pk": pk})
        self.row_status_indications = None

    columns = [
        col
        for col in DeductionListView.columns
        if col[1]
        not in (
            "specific_employees_col",
            "excluded_employees_col",
            "condition_based_col",
            "rate",
        )
    ]

    # action_method = "deduct_detail_actions"

    template_name = "cbv/allowance_deduction/allowance_deduction.html"

    def get_context_data(self, **kwargs: Any):
        """
        Adds employee details, active contracts, and basic pay to the context.
        """

        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        self.request.my_id = pk
        employee = Employee.objects.get(id=pk)
        active_contracts = (
            employee.contract_set.filter(contract_status="active").first()
            if apps.is_installed("payroll")
            else None
        )
        basic_pay = active_contracts.wage if active_contracts else None
        context["active_contracts"] = active_contracts
        context["basic_pay"] = basic_pay
        # context["search_url"] = (
        #     f"{reverse('deduction-tab-list', kwargs={'pk': pk})}"
        # )
        return context

    def get_queryset(self):
        """
        Returns a filtered queryset of deductions based on
        the employee's active contract and specific conditions
        """

        queryset = HorillaListView.get_queryset(self)
        pk = self.kwargs.get("pk")
        employee = Employee.objects.get(id=pk)
        active_contracts = (
            employee.contract_set.filter(contract_status="active").first()
            if apps.is_installed("payroll")
            else None
        )
        basic_pay = active_contracts.wage if active_contracts else None
        if basic_pay:
            specific_deductions = queryset.filter(
                specific_employees=employee, is_pretax=True, is_tax=False
            ).distinct()
            conditional_deduction = (
                queryset.filter(is_condition_based=True, is_pretax=True, is_tax=False)
                .exclude(exclude_employees=employee)
                .distinct()
            )
            active_employee_deduction = (
                queryset.filter(
                    include_active_employees=True, is_pretax=True, is_tax=False
                )
                .exclude(exclude_employees=employee)
                .distinct()
            )
            queryset = (
                specific_deductions | conditional_deduction | active_employee_deduction
            )

            filtered_queryset = []
            for deduction in queryset:
                if deduction.is_condition_based:
                    condition_field = deduction.field
                    condition_operator = deduction.condition
                    condition_value = deduction.value.lower().replace(" ", "_")
                    employee_value = dynamic_attr(employee, condition_field)
                    operator_func = operator_mapping.get(condition_operator)

                    if employee_value is not None and operator_func(
                        employee_value, type(employee_value)(condition_value)
                    ):
                        filtered_queryset.append(deduction)
                else:
                    filtered_queryset.append(deduction)
            queryset = queryset.filter(
                id__in=[deduction.id for deduction in filtered_queryset]
            )
        else:
            queryset = super().get_queryset().none()
        return queryset


class DeductionDetailView(HorillaDetailedView):
    """
    Detail View
    """

    model = Deduction
    title = _("Details")

    header = {
        "title": "title",
        "subtitle": "Deduction",
        "avatar": "get_avatar",
    }

    body = [
        (_("Tax"), "tax_col", True),
        (_("One Time deduction"), "get_one_time_deduction"),
        (_("Condition Based"), "condition_based_col"),
        (_("Amount"), "amount_col"),
        (_("Has Maximum Limit"), "has_maximum_limit_col"),
        (_("Deduction Eligibility"), "deduction_eligibility"),
    ]

    action_method = "deduct_detail_actions"


class AllowanceDetailView(HorillaDetailedView):
    """
    detail view for allowance tab
    """

    model = Allowance
    title = _("Details")

    header = {
        "title": "title",
        "subtitle": "",
        "avatar": "get_avatar",
    }

    body = [
        (_("Taxable"), "get_is_taxable_display"),
        (_("One Time Allowance"), "one_time_date_display"),
        (_("Condition Based"), "condition_based_display"),
        (_("Amount"), "based_on_amount"),
        (_("Has Maximum Limit"), "cust_allowance_max_limit"),
        (_("Allowance Eligibility"), "allowance_eligibility"),
    ]

    action_method = "allowance_detail_actions"
