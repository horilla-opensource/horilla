"""
dynamic_fields/urls.py
"""

from django.urls import path

from dynamic_fields import views

urlpatterns = [
    path(
        "add-dynamic-field",
        views.DynamicFieldFormView.as_view(),
        name="add-dynamic-field",
    ),
    path(
        "edit-verbose-name/<int:pk>/",
        views.DynamicFieldFormView.as_view(),
        name="edit-verbose-name",
    ),
    path(
        "remove-dynamic-field",
        views.RemoveDf.as_view(),
        name="remove-dynamic-field",
    ),
]
