"""
horilla_automations/urls.py
"""

from django.urls import path

from horilla_automations.views import cbvs, views

urlpatterns = [
    path(
        "configuration/mail-automations",
        cbvs.AutomationSectionView.as_view(),
        name="mail-automations",
    ),
    path(
        "mail-automations-nav",
        cbvs.AutomationNavView.as_view(),
        name="mail-automations-nav",
    ),
    path(
        "create-automation",
        cbvs.AutomationFormView.as_view(),
        name="create-automation",
    ),
    path(
        "update-automation/<int:pk>/",
        cbvs.AutomationFormView.as_view(),
        name="update-automation",
    ),
    path(
        "mail-automations-list-view",
        cbvs.AutomationListView.as_view(),
        name="mail-automations-list-view",
    ),
    path(
        "get-to-mail-field",
        views.get_to_field,
        name="get-to-mail-field",
    ),
    path(
        "automation-detailed-view/<int:pk>/",
        cbvs.AutomationDetailedView.as_view(),
        name="automation-detailed-view",
    ),
    path(
        "delete-automation/<int:pk>/",
        views.delete_automation,
        name="delete-automation",
    ),
    path(
        "load-automations",
        cbvs.LoadAutomationsView.as_view(),
        name="load-automations",
    ),
    path(
        "refresh-automations",
        views.refresh_automations,
        name="refresh-automations",
    ),
]
