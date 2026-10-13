"""
this page is handling the cbv methods for the payroll settings page,
which lists payslip auto generation as a tab
"""

from typing import Any

from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import hx_request_required, login_required
from horilla_views.generic.cbv.views import HorillaTabView, TemplateView
from payroll.cbv.allowances import AllowanceListView
from payroll.cbv.deduction import DeductionListView
from payroll.cbv.payslip_automation import PaySlipAutomationListView
from payroll.cbv.salary_structure import SalaryStructureListView


def _payroll_settings_tab_badge_count(request, view_cls):
    """Same queryset rules as the tab's HorillaListView (filters, permissions)."""
    view = view_cls()
    view.request = request
    view.args = ()
    view.kwargs = {}
    view.queryset = None
    return view.get_queryset().count()


@method_decorator(login_required, name="dispatch")
class PayrollSettingsView(TemplateView):
    """
    page for payroll settings (Payslip Auto Generation tab)
    """

    template_name = "cbv/payroll_settings/payroll_settings_main.html"


@method_decorator(login_required, name="dispatch")
class PayrollSettingsTabView(HorillaTabView):
    """
    tab view for payroll settings, shows payslip auto generation as a tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Salary Structures"),
                "url": f"{reverse('payroll-settings-salary-structure-tab')}",
            },
            {
                "title": _("Allowances"),
                "url": f"{reverse('payroll-settings-allowance-tab')}",
            },
            {
                "title": _("Deductions"),
                "url": f"{reverse('payroll-settings-deduction-tab')}",
            },
            {
                "title": _("Payslip Auto Generation"),
                "url": f"{reverse('payroll-settings-auto-payslip-tab')}",
            },
        ]

    def get_context_data(self, **kwargs: Any):
        """
        Eagerly compute each tab's real record count so its badge shows the
        right number on first load — lazy-loaded (non-active) tabs don't run
        the count-updating script embedded in their list template until the
        user actually clicks them, so without this they'd sit at "0".

        view_classes lines up with self.tabs position for position (Salary
        Structures, Allowances, Deductions, Payslip Auto Generation). It used
        to start one entry short of self.tabs, which shifted every pairing by
        one: Salary Structures showed Allowances' count, Allowances showed
        Deductions', Deductions showed Payslip Auto Generation's, and that
        last tab was left with no count at all.
        """
        context = super().get_context_data(**kwargs)
        view_classes = [
            SalaryStructureListView,
            AllowanceListView,
            DeductionListView,
            PaySlipAutomationListView,
        ]
        for tab, view_cls in zip(self.tabs, view_classes):
            tab["badge"] = _payroll_settings_tab_badge_count(self.request, view_cls)
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PayrollSettingsSalaryStructureTab(TemplateView):
    """
    salary structure tab content, embeds the nav + list
    """

    template_name = "cbv/payroll_settings/salary_structure_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PayrollSettingsAllowanceTab(TemplateView):
    """
    payslip auto generation tab content, embeds the existing nav + list
    """

    template_name = "cbv/payroll_settings/allowance_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PayrollSettingsDeductionTab(TemplateView):
    """
    payslip auto generation tab content, embeds the existing nav + list
    """

    template_name = "cbv/payroll_settings/deduction_tab.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(hx_request_required, name="dispatch")
class PayrollSettingsAutoPayslipTab(TemplateView):
    """
    payslip auto generation tab content, embeds the existing nav + list
    """

    template_name = "cbv/payroll_settings/auto_payslip_tab.html"
