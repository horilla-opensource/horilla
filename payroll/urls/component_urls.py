"""
component_urls.py

This module is used to bind the urls related to payslip and its pay-heads methods
"""

from django.urls import path

from payroll.cbv import (
    allowance_deduction,
    allowances,
    asset_fine,
    deduction,
    loan_advance_salary,
    payslip,
    reimbursements,
)
from payroll.models.models import Allowance, Deduction
from payroll.views import component_views

urlpatterns = [
    path(
        "individual-payslip-tab-list/<int:pk>/",
        payslip.PayrollTab.as_view(),
        name="individual-payslip-tab-list",
    ),
    path("view-payslip/", payslip.PayslipView.as_view(), name="view-payslip"),
    path("payslip-list/", payslip.PayslipList.as_view(), name="payslip-list"),
    path("payslip-navbar/", payslip.PayslipNav.as_view(), name="payslip-navbar"),
    path(
        "payslip-bulk-export-data/",
        payslip.PayslipBulkExport.as_view(),
        name="payslip-bulk-export-data",
    ),
    path(
        "payroll-create-form-view/",
        payslip.PayrollCreateFormView.as_view(),
        name="payroll-create-form-view",
    ),
    path(
        "deduction-tab-list/<int:pk>/",
        allowance_deduction.DeductionTab.as_view(),
        name="deduction-tab-list",
    ),
    path(
        "allowance-deduction-tab-view/<int:pk>/",
        allowance_deduction.AllowanceDeductionTabView.as_view(),
        name="allowance-deduction-tab-view",
    ),
    path(
        "deduction-detail-view/<int:pk>/",
        allowance_deduction.DeductionDetailView.as_view(),
        name="deduction-detail-view",
    ),
    path(
        "allowance-tab-list/<int:pk>/",
        allowance_deduction.AllowanceTabList.as_view(),
        name="allowance-tab-list",
    ),
    path(
        "allowance-detail-view/<int:pk>/",
        allowance_deduction.AllowanceDetailView.as_view(),
        name="allowance-detail-view",
    ),
    path(
        "view-loan/", loan_advance_salary.AdvanceSalaryView.as_view(), name="view-loan"
    ),
    path(
        "loan-generic-tab-view/",
        loan_advance_salary.LoansGenericTab.as_view(),
        name="loan-generic-tab-view",
    ),
    path(
        "loan-tab-list-view/",
        loan_advance_salary.LoanListView.as_view(),
        name="loan-tab-list-view",
    ),
    path(
        "advanced-salary-list-view/",
        loan_advance_salary.AdvancedSalaryList.as_view(),
        name="advanced-salary-list-view",
    ),
    path(
        "fines-list-view/",
        loan_advance_salary.FinesListView.as_view(),
        name="fines-list-view",
    ),
    path(
        "loan-navbar-view/",
        loan_advance_salary.LoanNavView.as_view(),
        name="loan-navbar-view",
    ),
    path(
        "loan-detail-view/<int:pk>/",
        loan_advance_salary.LoanDetailView.as_view(),
        name="loan-detail-view",
    ),
    path(
        "loan-create-form/",
        loan_advance_salary.LoanFormView.as_view(),
        name="loan-create-form",
    ),
    path(
        "loan-edit-form/<int:pk>/",
        loan_advance_salary.LoanFormView.as_view(),
        name="loan-edit-form",
    ),
    path(
        "view-allowance/", allowances.AllowanceViewPage.as_view(), name="view-allowance"
    ),
    path(
        "allowances-list-view/",
        allowances.AllowanceListView.as_view(),
        name="allowances-list-view",
    ),
    path(
        "allowances-nav-view/",
        allowances.AllowanceNavView.as_view(),
        name="allowances-nav-view",
    ),
    path(
        "allowances-card-view/",
        allowances.AllowancesCardView.as_view(),
        name="allowances-card-view",
    ),
    path(
        "allowances-deductions-tab/<int:emp_id>",
        component_views.allowances_deductions_tab,
        name="allowances-deductions-tab",
    ),
    path("create-allowance", component_views.create_allowance, name="create-allowance"),
    # path("view-allowance/", component_views.view_allowance, name="view-allowance"),
    path(
        "single-allowance-view/<int:allowance_id>",
        component_views.view_single_allowance,
        name="single-allowance-view",
    ),
    path("filter-allowance", component_views.filter_allowance, name="filter-allowance"),
    path(
        "update-allowance/<int:allowance_id>/",
        component_views.update_allowance,
        name="update-allowance",
        kwargs={"model": Allowance},
    ),
    path(
        "delete-allowance/<int:allowance_id>",
        component_views.delete_allowance,
        name="delete-allowance",
    ),
    path(
        "delete-allowances/<int:allowance_id>/<int:emp_id>/",
        component_views.delete_allowance,
        name="delete-allowances",
    ),
    path(
        "delete-employee-allowance/<int:allowance_id>/",
        component_views.delete_allowance,
        name="delete-employee-allowance",
    ),
    path("create-deduction", component_views.create_deduction, name="create-deduction"),
    # path("view-deduction/", component_views.view_deduction, name="view-deduction"),
    path(
        "deduction-view-list/",
        deduction.DeductionListView.as_view(),
        name="deduction-view-list",
    ),
    path(
        "deduction-view-nav/",
        deduction.DeductionNav.as_view(),
        name="deduction-view-nav",
    ),
    path(
        "deduction-view-card/",
        deduction.DeductionCardView.as_view(),
        name="deduction-view-card",
    ),
    path("view-deduction/", deduction.DeductionView.as_view(), name="view-deduction"),
    path(
        "single-deduction-view/<int:deduction_id>",
        component_views.view_single_deduction,
        name="single-deduction-view",
    ),
    path("filter-deduction", component_views.filter_deduction, name="filter-deduction"),
    path(
        "update-deduction/<int:deduction_id>/",
        component_views.update_deduction,
        name="update-deduction",
        kwargs={"model": Deduction},
    ),
    path(
        "delete-deduction/<int:deduction_id>/",
        component_views.delete_deduction,
        name="delete-deduction",
    ),
    path(
        "delete-deduction/<int:deduction_id>/<int:emp_id>/",
        component_views.delete_deduction,
        name="delete-deduction",
    ),
    path("create-payslip", component_views.create_payslip, name="create-payslip"),
    path(
        "check-contract-start-date",
        component_views.check_contract_start_date,
        name="check-contract-start-date",
    ),
    path("generate-payslip", component_views.generate_payslip, name="generate-payslip"),
    path(
        "validate-start-date",
        component_views.validate_start_date,
        name="validate-start-date",
    ),
    path("filter-payslip", component_views.filter_payslip, name="filter-payslip"),
    path(
        "payslip-info-export",
        component_views.payslip_export,
        name="payslip-info-export",
    ),
    path(
        "view-individual-payslip/<int:employee_id>/<str:start_date>/<str:end_date>/",
        component_views.view_individual_payslip,
        name="view-individual-payslip",
    ),
    # path("view-payslip/", component_views.view_payslip, name="view-payslip"),
    path(
        "hx-create-allowance",
        component_views.hx_create_allowance,
        name="hx-create-allowance",
    ),
    path("send-slip", component_views.send_slip, name="send-slip"),
    path("add-bonus/", component_views.add_bonus, name="add-bonus"),
    path(
        "add-payslip-deduction/",
        component_views.add_deduction,
        name="add-payslip-deduction",
    ),
    # path("view-loan/", component_views.view_loans, name="view-loan"),
    path("create-loan/", component_views.create_loan, name="create-loan"),
    path(
        "view-installments/",
        component_views.view_installments,
        name="view-installments",
    ),
    path(
        "edit-installment-amount/",
        component_views.edit_installment_amount,
        name="edit-installment-amount",
    ),
    path("delete-loan/", component_views.delete_loan, name="delete-loan"),
    path("search-loan/", component_views.search_loan, name="search-loan"),
    # path(
    #     "asset-fine/",
    #     component_views.asset_fine,
    #     name="asset-fine",
    # ),
    path(
        "asset-fine/",
        asset_fine.AssetFineFormView.as_view(),
        name="asset-fine",
    ),
    # path(
    #     "view-reimbursement",
    #     component_views.view_reimbursement,
    #     name="view-reimbursement",
    # ),
    path(
        "create-reimbursement",
        component_views.create_reimbursement,
        name="create-reimbursement",
    ),
    path(
        "search-reimbursement",
        component_views.search_reimbursement,
        name="search-reimbursement",
    ),
    path(
        "get-assigned-leaves/",
        component_views.get_assigned_leaves,
        name="get-assigned-leaves",
    ),
    path(
        "approve-reimbursements",
        component_views.approve_reimbursements,
        name="approve-reimbursements",
    ),
    path(
        "delete-reimbursements",
        component_views.delete_reimbursements,
        name="delete-reimbursement",
    ),
    path(
        "reimbursement-individual-view/<int:instance_id>/",
        component_views.reimbursement_individual_view,
        name="reimbursement-individual-view",
    ),
    path(
        "reimbursement-attachements/<int:instance_id>/",
        component_views.reimbursement_attachments,
        name="reimbursement-attachments",
    ),
    path(
        "delete-attachments/<int:_reimbursement_id>/",
        component_views.delete_attachments,
        name="delete-attachments",
    ),
    path(
        "get-contribution-report",
        component_views.get_contribution_report,
        name="get-contribution-report",
    ),
    path(
        "payslip-detailed-export",
        component_views.payslip_detailed_export,
        name="payslip-detailed-export",
    ),
    path(
        "view-reimbursement",
        reimbursements.ReimbursementsView.as_view(),
        name="view-reimbursement",
    ),
    path(
        "reimbursement-nav",
        reimbursements.ReimbursementsNav.as_view(),
        name="reimbursement-nav",
    ),
    path(
        "tab-reimbursement",
        reimbursements.ReimbursementsAndEncashmentsTabView.as_view(),
        name="tab-reimbursement",
    ),
    path(
        "detail-view-reimbursement/<int:pk>/",
        reimbursements.ReimbursementsDetailView.as_view(),
        name="detail-view-reimbursement",
    ),
    path(
        "detail-view-leave-encashment/<int:pk>/",
        reimbursements.LeaveEncashmentsDetailedView.as_view(),
        name="detail-view-leave-encashment",
    ),
    path(
        "detail-view-bonus-encashment/<int:pk>/",
        reimbursements.BonusEncashmentsDetailedView.as_view(),
        name="detail-view-bonus-encashment",
    ),
    path(
        "list-reimbursement",
        reimbursements.ReimbursementsListView.as_view(),
        name="list-reimbursement",
    ),
    path(
        "list-leave-encash",
        reimbursements.LeaveEncashmentsListView.as_view(),
        name="list-leave-encash",
    ),
    path(
        "list-bonus-encash",
        reimbursements.BonusEncashmentsListView.as_view(),
        name="list-bonus-encash",
    ),
    path(
        "reimbursement-create",
        reimbursements.ReimbursementsFormView.as_view(),
        name="reimbursement-create",
    ),
    path(
        "reimbursement-update/<int:pk>",
        reimbursements.ReimbursementsFormView.as_view(),
        name="reimbursement-update",
    ),
]
