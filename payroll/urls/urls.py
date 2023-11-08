"""
urls.py

This module is used to map url pattern or request path with view functions
"""
from django.urls import path, include
from payroll.views import views
from payroll.models.models import Contract, Payslip

urlpatterns = [
    path("", include("payroll.urls.component_urls")),
    path("", include("payroll.urls.tax_urls")),
    path("get-language-code/", views.get_language_code, name="get-language-code"),
    path("contract-create", views.contract_create, name="contract-create"),
    path(
        "update-contract/<int:contract_id>",
        views.contract_update,
        name="update-contract",
        kwargs={"model": Contract},
    ),
    path(
        "delete-contract/<int:contract_id>",
        views.contract_delete,
        name="delete-contract",
    ),
    path("view-contract/", views.contract_view, name="view-contract"),
    path(
        "single-contract-view/<int:contract_id>/",
        views.view_single_contract,
        name="single-contract-view",
    ),
    path("payslip-pdf/<int:id>", views.payslip_pdf, name="payslip-pdf"),
    path("contract-filter", views.contract_filter, name="contract-filter"),
    path("contract-create", views.work_record_create, name="contract-create"),
    path("work-record-view", views.work_record_view, name="work-record-view"),
    path(
        "work-record-employees-view",
        views.work_record_employee_view,
        name="work-record-employees-view",
    ),
    path("settings", views.settings, name="payroll-settings"),
    path(
        "payslip-status-update/<int:payslip_id>/",
        views.update_payslip_status,
        name="payslip-status-update",
    ),
    path(
        "payslip-status-update",
        views.update_payslip_status,
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
        "dashboard-contract-ending",
        views.contract_ending,
        name="dashboard-contract-ending",
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
]
