"""
urls.py

This module is used to map url pattern or request path with view functions
"""

from django.urls import include, path

from payroll.cbv import contracts, dashboard, payslip_automation
from payroll.models.models import Contract, Payslip
from payroll.views import views

urlpatterns = [
    path("", include("payroll.urls.component_urls")),
    path("", include("payroll.urls.tax_urls")),
    path("contract-create", views.contract_create, name="contract-create"),
    path(
        "update-contract/<int:contract_id>",
        views.contract_update,
        name="update-contract",
        kwargs={"model": Contract},
    ),
    path(
        "update-contract-status/<int:contract_id>",
        views.contract_status_update,
        name="update-contract-status",
    ),
    path(
        "bulk-update-contract-status",
        views.bulk_contract_status_update,
        name="bulk-update-contract-status",
    ),
    path(
        "update-contract-filing-status/<int:contract_id>",
        views.update_contract_filing_status,
        name="update-contract-filing-status",
    ),
    path(
        "delete-contract/<int:contract_id>",
        views.contract_delete,
        name="delete-contract",
    ),
    path(
        "delete-contract-modal/<int:contract_id>",
        views.contract_delete,
        name="delete-contract-modal",
    ),
    # path("view-contract/", views.contract_view, name="view-contract"),
    path(
        "single-contract-view/<int:contract_id>/",
        views.view_single_contract,
        name="single-contract-view",
    ),
    path("payslip-pdf/<int:id>", views.payslip_pdf, name="payslip-pdf"),
    # path("contract-filter", views.contract_filter, name="contract-filter"),
    path("settings", views.settings, name="payroll-settings"),
    path(
        "payslip-status-update/<int:payslip_id>/",
        views.update_payslip_status,
        name="payslip-status-update",
    ),
    path(
        "payslip-status-update-no-id",
        views.update_payslip_status_no_id,
        name="payslip-status-update-no-id",
    ),
    path(
        "bulk-payslip-status-update",
        views.bulk_update_payslip_status,
        name="bulk-payslip-status-update",
    ),
    path(
        "view-payslip/<int:payslip_id>/",
        views.view_created_payslip,
        name="view-created-payslip",
        kwargs={"model": Payslip},
    ),
    path(
        "view-payslip-pdf/<int:payslip_id>/",
        views.view_payslip_pdf,
        name="view-payslip-pdf",
    ),
    path(
        "delete-payslip/<int:payslip_id>/", views.delete_payslip, name="delete-payslip"
    ),
    path(
        "contract-info-initial",
        views.contract_info_initial,
        name="contract-info-initial",
    ),
    path(
        "view-payroll-dashboard/",
        views.view_payroll_dashboard,
        name="view-payroll-dashboard",
    ),
    path(
        "dashboard-employee-chart",
        views.dashboard_employee_chart,
        name="dashboard-employee-chart",
    ),
    path(
        "dashboard-payslip-details",
        views.payslip_details,
        name="dashboard-payslip-details",
    ),
    path(
        "dashboard-department-chart",
        views.dashboard_department_chart,
        name="dashboard-department-chart",
    ),
    path(
        "dashboard-department-chart-list",
        dashboard.DashboardDepartmentPayslip.as_view(),
        name="dashboard-department-chart-list",
    ),
    # path(
    #     "dashboard-contract-ending",
    #     views.contract_ending,
    #     name="dashboard-contract-ending",
    # ),
    path(
        "dashboard-contract-ending",
        dashboard.DashboardContractList.as_view(),
        name="dashboard-contract-ending",
    ),
    path(
        "dashboard-contract-expired",
        dashboard.DashboardContractListExpired.as_view(),
        name="dashboard-contract-expired",
    ),
    path(
        "dashboard-export/",
        views.payslip_export,
        name="dashboard-export",
    ),
    path(
        "payslip-bulk-delete",
        views.payslip_bulk_delete,
        name="payslip-bulk-delete",
    ),
    path(
        "update-batch-group-name",
        views.slip_group_name_update,
        name="update-batch-group-name",
    ),
    path("contract-export", views.contract_export, name="contract-export"),
    path(
        "contract-bulk-delete",
        views.contract_bulk_delete,
        name="contract-bulk-delete",
    ),
    path("contract-select/", views.contract_select, name="contract-select"),
    path(
        "contract-select-filter/",
        views.contract_select_filter,
        name="contract-select-filter",
    ),
    path("payslip-select/", views.payslip_select, name="payslip-select"),
    path(
        "payslip-select-filter/",
        views.payslip_select_filter,
        name="payslip-select-filter",
    ),
    path(
        "payroll-request-add-comment/<int:payroll_id>/",
        views.create_payrollrequest_comment,
        name="payroll-request-add-comment",
    ),
    path(
        "payroll-request-view-comment/<int:payroll_id>/",
        views.view_payrollrequest_comment,
        name="payroll-request-view-comment",
    ),
    path(
        "payroll-request-delete-comment/<int:comment_id>/",
        views.delete_payrollrequest_comment,
        name="payroll-request-delete-comment",
    ),
    path(
        "delete-reimbursement-comment-file/",
        views.delete_reimbursement_comment_file,
        name="delete-reimbursement-comment-file",
    ),
    path(
        "initial-notice-period",
        views.initial_notice_period,
        name="initial-notice-period",
    ),
    path("view-contract/", contracts.ContractsView.as_view(), name="view-contract"),
    path("contract-filter/", contracts.ContractsList.as_view(), name="contract-filter"),
    path("contracts-nav/", contracts.ContractsNav.as_view(), name="contracts-nav"),
    path(
        "contracts-export/",
        contracts.ContractsExportView.as_view(),
        name="contracts-export",
    ),
    path(
        "contracts-detail-view/<int:pk>/",
        contracts.ContractsDetailView.as_view(),
        name="contracts-detail-view",
    ),
    # ===========================Auto payslip generate================================
    path(
        "auto-payslip-settings-view/",
        views.auto_payslip_settings_view,
        name="auto-payslip-settings-view",
    ),
    path(
        "create-auto-payslip",
        views.create_or_update_auto_payslip,
        name="create-auto-payslip",
    ),
    path(
        "update-auto-payslip/<int:auto_id>",
        views.create_or_update_auto_payslip,
        name="update-auto-payslip",
    ),
    path(
        "delete-auto-payslip/<int:auto_id>",
        views.delete_auto_payslip,
        name="delete-auto-payslip",
    ),
    path(
        "activate-auto-payslip-generate",
        views.activate_auto_payslip_generate,
        name="activate-auto-payslip-generate",
    ),
    path(
        "pay-slip-automation-list",
        payslip_automation.PaySlipAutomationListView.as_view(),
        name="pay-slip-automation-list",
    ),
    path(
        "pay-slip-automation-nav",
        payslip_automation.PaySlipAutomationNav.as_view(),
        name="pay-slip-automation-nav",
    ),
    path(
        "pay-slip-automation-create",
        payslip_automation.PaySlipAutomationFormView.as_view(),
        name="pay-slip-automation-create",
    ),
    path(
        "pay-slip-automation-update/<int:pk>/",
        payslip_automation.PaySlipAutomationFormView.as_view(),
        name="pay-slip-automation-update",
    ),
    path(
        "pay-slip-automation-delete/<int:auto_id>/",
        payslip_automation.DeleteAutoPayslipView.as_view(),
        name="pay-slip-automation-delete",
    ),
]
