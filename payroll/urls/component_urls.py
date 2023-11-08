"""
component_urls.py

This module is used to bind the urls related to payslip and its pay-heads methods
"""
from django.urls import path
from payroll.views import component_views
from payroll.models.models import Allowance, Deduction

urlpatterns = [
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
    path("create-payslip", component_views.create_payslip, name="create-payslip"),
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
]
