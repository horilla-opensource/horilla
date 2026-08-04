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
