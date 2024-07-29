"""
horilla_views/urls.py
"""

from django.urls import path

from horilla_views import views
from horilla_views.generic.cbv.views import ReloadMessages

urlpatterns = [
    path("toggle-columns", views.ToggleColumn.as_view(), name="toggle-columns"),
    path("active-tab", views.ActiveTab.as_view(), name="active-tab"),
    path("active-group", views.ActiveGroup.as_view(), name="cbv-active-group"),
    path("reload-field", views.ReloadField.as_view(), name="reload-field"),
    path("reload-messages", ReloadMessages.as_view(), name="reload-messages"),
    path("saved-filter/", views.SavedFilter.as_view(), name="saved-filter"),
    path(
        "saved-filter/<int:pk>/",
        views.SavedFilter.as_view(),
        name="saved-filter-update",
    ),
    path(
        "delete-saved-filter/<int:pk>/",
        views.DeleteSavedFilter.as_view(),
        name="delete-saved-filter",
    ),
    path(
        "active-hnv-view-type/",
        views.ActiveView.as_view(),
        name="active-hnv-view-type",
    ),
]
