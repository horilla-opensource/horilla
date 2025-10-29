"""
This page is handle the payslip automation page in settings.
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
)
from payroll.filters import PayslipAutoGenerateFilter
from payroll.forms.component_forms import PayslipAutoGenerateForm
from payroll.models.models import PayslipAutoGenerate


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="payroll.view_payslipautogenerate"), name="dispatch"
)
class PaySlipAutomationListView(HorillaListView):
    """
    List view of the page
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # self.action_method = "actions_col"
        self.view_id = "pay_slip_id"
        self.search_url = reverse("pay-slip-automation-list")

    model = PayslipAutoGenerate
    filter_class = PayslipAutoGenerateFilter
    show_toggle_form = False

    columns = [
        (_("Payslip creation date"), "get_generate_day_display"),
        (_("Company"), "get_company"),
        (_("Is active"), "is_active_col"),
    ]

    header_attrs = {
        "get_generate_day_display": """
                   style = "width:200px !important"
                   """,
    }

    actions = [
        {
            "action": "Edit",
            "icon": "create-outline",
            "attrs": """
                    class="oh-btn oh-btn--light-bkg w-50"
                    hx-get="{get_update_url}?instance_ids={ordered_ids}"
                    hx-target="#genericModalBody"
                    data-toggle="oh-modal-toggle"
                    data-target="#genericModal"
                    """,
        },
        {
            "action": "Delete",
            "icon": "trash-outline",
            "attrs": """
                    class="oh-btn oh-btn--danger-outline oh-btn--light-bkg w-50"
                    hx-confirm="Are you sure you want to delete this payslip auto generate?"
                    hx-target="#autoPayslipTr{get_instance_id}"
                    hx-post="{get_delete_url}"
                    hx-swap="delete"
                    """,
        },
    ]

    row_attrs = """
                id = "autoPayslipTr{get_instance_id}"
                """


#   onclick = "deleteItem({get_delete_url})"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="payroll.view_payslipautogenerate"), name="dispatch"
)
class PaySlipAutomationNav(HorillaNavView):
    """
    Nav bar
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("pay-slip-automation-list")
        self.create_attrs = f"""
                            onclick = "event.stopPropagation();"
                            data-toggle="oh-modal-toggle"
                            data-target="#genericModal"
                            hx-target="#genericModalBody"
                            hx-get="{reverse('pay-slip-automation-create')}"
                            """

    nav_title = _("Payslip Automation")
    filter_instance = PayslipAutoGenerateFilter()
    search_swap_target = "#listContainer"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="payroll.change_payslipautogenerate"), name="dispatch"
)
class PaySlipAutomationFormView(HorillaFormView):
    """
    Create and edit form
    """

    model = PayslipAutoGenerate
    form_class = PayslipAutoGenerateForm
    new_display_title = _("Create Auto Payslip Generate")

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form view.
        """
        context = super().get_context_data(**kwargs)
        if self.form.instance.pk:
            self.form_class.verbose_name = _("Update Auto Payslip Generate")
        return context

    def form_valid(self, form: PayslipAutoGenerateForm) -> HttpResponse:
        """
        Handle a valid form submission.

        If the form is valid, save the instance and display a success message.
        """
        company = (
            self.form.instance.company_id
            if self.form.instance.company_id
            else "All company"
        )
        if form.is_valid():
            if form.instance.pk:
                message = _(
                    f"Payslip Auto generate for {company} created successfully "
                )
            else:
                message = _(
                    f"Payslip Auto generate for {company} created successfully "
                )
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required(perm="payroll.delete_payslipautogenerate"), name="dispatch"
)
class DeleteAutoPayslipView(View):
    """
    Handles deletion of a PayslipAutoGenerate object.

    Deletes the object if 'auto_generate' is False, else shows a message.
    Redirects to the referring page or root URL.
    """

    def post(self, request, auto_id):
        """
        Deletes the PayslipAutoGenerate object and redirects.
        """
        auto_payslip = get_object_or_404(PayslipAutoGenerate, id=auto_id)
        if not auto_payslip.auto_generate:
            company = (
                auto_payslip.company_id
                if auto_payslip.company_id
                else _("All companies")
            )
            auto_payslip.delete()
            messages.success(
                request,
                _(f"Payslip auto generate for {company} deleted successfully."),
            )
        else:
            messages.info(
                request, _("Active 'Payslip auto generate' cannot be deleted.")
            )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
