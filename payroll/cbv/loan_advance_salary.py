"""
this page is handling the cbv methods of loan/advanced salary page
"""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _

from horilla_views.cbv_methods import login_required, permission_required
from horilla_views.generic.cbv.views import (
    HorillaDetailedView,
    HorillaFormView,
    HorillaListView,
    HorillaNavView,
    HorillaTabView,
    TemplateView,
)
from payroll.filters import LoanAccountFilter
from payroll.forms.component_forms import LoanAccountForm
from payroll.models.models import LoanAccount


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class AdvanceSalaryView(TemplateView):
    """
    for loan/advance salary page
    """

    template_name = "cbv/loan/loan_main.html"


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class LoansGenericTab(HorillaTabView):
    """
    Tab view for loans/advanced salary
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tabs = [
            {
                "title": _("Loan"),
                "url": f"{reverse('loan-tab-list-view')}",
            },
            {
                "title": _("Salary Advance"),
                "url": f"{reverse('advanced-salary-list-view')}",
            },
            {
                "title": _("Fine"),
                "url": f"{reverse('fines-list-view')}",
            },
        ]

    def get_context_data(self, **kwargs):
        qs = LoanAccount.objects.all()
        filter_class = LoanAccountFilter
        if filter_class:
            qs = filter_class(
                data=self.request.GET, queryset=qs, request=self.request
            ).qs

        loan_count = qs.filter(type="loan").count()
        adv_count = qs.filter(type="advanced_salary").count()
        fine_count = qs.filter(type="fine").count()

        loan_url = reverse("loan-tab-list-view")
        adv_url = reverse("advanced-salary-list-view")
        fine_url = reverse("fines-list-view")

        for tab in self.tabs:
            url = tab.get("url", "")
            if loan_url in url:
                tab["badge"] = loan_count
            elif adv_url in url:
                tab["badge"] = adv_count
            elif fine_url in url:
                tab["badge"] = fine_count

        context = super().get_context_data(**kwargs)
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class LoanListView(HorillaListView):
    """
    List view for loan tab
    """

    bulk_update_fields = [
        "provided_date",
        "installment_start_date",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("loan-tab-list-view")

    def get_queryset(self):
        """
        queryset for rendering loan data only
        """
        queryset = super().get_queryset()
        queryset = queryset.filter(type="loan")
        return queryset

    filter_class = LoanAccountFilter
    model = LoanAccount

    columns = [
        (_("Employee"), "employee_id", "employee_id__get_avatar"),
        (_("Title"), "title"),
        (_("Provided Date"), "provided_date"),
        (_("Installment Start Date"), "installment_start_date"),
        (_("Toatal Installments"), "installments"),
        (_("Amount"), "loan_amount"),
        (_("Description"), "description"),
        (_("Progress Bar"), "progress_bar_col"),
    ]

    sortby_mapping = [
        (_("Employee"), "employee_id__get_full_name", "employee_id__get_avatar"),
        (_("Provided Date"), "provided_date"),
        (_("Installment Start Date"), "installment_start_date"),
        (_("Toatal Installments"), "installments"),
        (_("Amount"), "loan_amount"),
    ]

    action_method = "loan_actions"

    row_attrs = """
                hx-get='{loan_detail_view}?instance_ids={ordered_ids}'
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
                """
    # Mirrors LoanNavView.nested_group_by_fields -- needed here too since
    # this (List) and Nav are separate classes; see the same split in
    # employee/cbv/employees.py's EmployeesList/EmployeeNav. Inherited by
    # AdvancedSalaryList/FinesListView below, covering all 3 tabs.
    nested_group_by_fields = [
        ("employee_id", _("Employee")),
        ("title", _("Title")),
        ("provided_date", _("Provided Date")),
        ("installment_start_date", _("Installment Start Date")),
        ("installments", _("Total Installments")),
        ("loan_amount", _("Amount")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employment Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class AdvancedSalaryList(LoanListView):
    """
    List view for advanced salary
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("advanced-salary-list-view")

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        queryset = queryset.filter(type="advanced_salary")
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class FinesListView(LoanListView):
    """
    List view for fines tab
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("fines-list-view")

    def get_queryset(self):
        queryset = HorillaListView.get_queryset(self)
        queryset = queryset.filter(type="fine")
        return queryset


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class LoanNavView(HorillaNavView):
    """
    Navbar for the laons/advance salary
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_url = reverse("loan-generic-tab-view")

        self.create_attrs = f"""
             hx-get="{reverse_lazy("loan-create-form")}"
             hx-target="#genericModalBody"
             data-target="#genericModal"
             data-toggle="oh-modal-toggle"
         """

    nav_title = _("Loans & Salary Advances")
    filter_body_template = "cbv/loan/loan_filter.html"
    filter_instance = LoanAccountFilter()
    filter_form_context_name = "form"
    search_swap_target = "#listContainer"

    # Mirrors LoanListView.nested_group_by_fields below -- List and Nav
    # are separate classes/templates (see employee/cbv/employees.py's
    # EmployeesList/EmployeeNav for the same split), so the inline
    # "add/change field" dropdowns in the "Grouped by" breadcrumb
    # (nested_group_by_table.html, rendered by the List view) need this
    # here too, not just the currently-active fields it already had
    # access to via nested_fields_active.
    nested_group_by_fields = [
        ("employee_id", _("Employee")),
        ("title", _("Title")),
        ("provided_date", _("Provided Date")),
        ("installment_start_date", _("Installment Start Date")),
        ("installments", _("Total Installments")),
        ("loan_amount", _("Amount")),
        (
            "employee_id__employee_work_info__reporting_manager_id",
            _("Reporting Manager"),
        ),
        ("employee_id__employee_work_info__department_id", _("Department")),
        ("employee_id__employee_work_info__job_position_id", _("Job Position")),
        ("employee_id__employee_work_info__employee_type_id", _("Employment Type")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class LoanDetailView(HorillaDetailedView):
    """
    detail view for the loan page
    """

    model = LoanAccount
    template_name = "cbv/loan/loan_detail_view.html"

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        loan = LoanAccount.objects.get(id=pk)
        installments = loan.deduction_ids.all()
        loan_id = self.request.GET.get("loan_id")
        ded_id = self.request.GET.get("ded_id")
        context["loan"] = loan
        context["loan_id"] = loan_id
        context["ded_id"] = ded_id
        context["installments"] = installments
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("payroll.view_loanaccount"), name="dispatch")
class LoanFormView(HorillaFormView):
    """
    form view for create and edit loans
    """

    form_class = LoanAccountForm
    model = LoanAccount
    new_display_title = _("Loans & Salary Advances")

    def form_valid(self, form: LoanAccountForm) -> HttpResponse:
        if form.is_valid():
            if form.instance.pk:
                message = _("Loan Updated Successfully")
            else:
                message = _("New Loan Created Successfully")
            form.save()

            messages.success(self.request, _(message))
            return self.HttpResponse(
                "<script>$('#reloadMessagesButton').click();</script>"
            )
        return super().form_valid(form)
