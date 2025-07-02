"""
tax_urls.py

This module is used to bind url patterns with django views that related to federal taxes
"""

from django.urls import path

from payroll.cbv import federal_tax
from payroll.views import tax_views

urlpatterns = [
    path(
        "filing-status-view/", tax_views.filing_status_view, name="filing-status-view"
    ),
    path(
        "filing-status-nav/",
        federal_tax.FilingStatusNav.as_view(),
        name="filing-status-nav",
    ),
    path(
        "create-filing-status/",
        federal_tax.FederalTaxFormView.as_view(),
        name="create-filing-status",
    ),
    # path(
    #     "create-filing-status",
    #     tax_views.create_filing_status,
    #     name="create-filing-status",
    # ),
    path(
        "filing-status-update/<int:pk>/",
        federal_tax.FederalTaxFormView.as_view(),
        name="filing-status-update",
    ),
    # path(
    #     "filing-status-update/<int:filing_status_id>",
    #     tax_views.update_filing_status,
    #     name="filing-status-update",
    # ),
    path(
        "filing-status-delete/<int:pk>",
        tax_views.filing_status_delete,
        name="filing-status-delete",
    ),
    path(
        "filing-status-search/",
        tax_views.filing_status_search,
        name="filing-status-search",
    ),
    path(
        "tax-bracket-list/<int:pk>",
        federal_tax.TaxBracketListView.as_view(),
        name="tax-bracket-list",
    ),
    path(
        "tax-bracket-create/<int:pk>",
        federal_tax.TaxBracketCreateForm.as_view(),
        name="tax-bracket-create",
    ),
    # path(
    #     "tax-bracket-create/<int:filing_status_id>",
    #     tax_views.create_tax_bracket,
    #     name="tax-bracket-create",
    # ),
    path(
        "tax-bracket-update/<int:pk>/",
        federal_tax.TaxBracketCreateForm.as_view(),
        name="tax-bracket-update",
    ),
    # path(
    #     "tax-bracket-update/<int:tax_bracket_id>/",
    #     tax_views.update_tax_bracket,
    #     name="tax-bracket-update",
    # ),
    path(
        "tax-bracket-delete/<int:pk>/",
        tax_views.delete_tax_bracket,
        name="tax-bracket-delete",
    ),
    path("update-py-code/<int:pk>/", tax_views.update_py_code, name="update-py-code"),
]
