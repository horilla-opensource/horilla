"""
component_urls.py

This module is used to bind the urls related to payslip and its pay-heads methods
"""

from django.urls import path

from payroll.models.models import Allowance, Deduction
from payroll.views import component_views

urlpatterns = [
    path(
        "allowances-deductions-tab/<int:emp_id>",
        component_views.allowances_deductions_tab,
        name="allowances-deductions-tab",
    ),
    path("create-allowance", component_views.create_allowance, name="create-allowance"),
    path("view-allowance/", component_views.view_allowance, name="view-allowance"),
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
        "delete-allowance/<int:allowance_id>/",
        component_views.delete_allowance,
        name="delete-allowance",
    ),
    path(
        "delete-employee-allowance/<int:allowance_id>/",
        component_views.delete_allowance,
        name="delete-employee-allowance",
    ),
    path("create-deduction", component_views.create_deduction, name="create-deduction"),
    path("view-deduction/", component_views.view_deduction, name="view-deduction"),
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
    path("view-payslip/", component_views.view_payslip, name="view-payslip"),
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
    path("view-loan/", component_views.view_loans, name="view-loan"),
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
    path(
        "asset-fine/",
        component_views.asset_fine,
        name="asset-fine",
    ),
    path(
        "view-reimbursement/",
        component_views.view_reimbursement,
        name="view-reimbursement",
    ),
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
]
