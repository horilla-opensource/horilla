"""
accessibility/urls.py
"""

from django.urls import path

from accessibility import views as accessibility

urlpatterns = [
    path(
        "settings/user-accessibility/",
        accessibility.user_accessibility,
        name="user-accessibility",
    ),
    path(
        "settings/load-accessibility-form/",
        accessibility.load_accessibility_form,
        name="load-accessibility-form",
    ),
    path(
        "get-initial-accessibility-data/",
        accessibility.get_accessibility_data,
        name="get-initial-accessibility-data",
    ),
]
