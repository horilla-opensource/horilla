"""
accessibility/urls.py
"""

from django.urls import path

from accessibility import views as accessibility

urlpatterns = [
    path(
        "user-accessibility/",
        accessibility.user_accessibility,
        name="user-accessibility",
    ),
    path(
        "get-initial-accessibility-data",
        accessibility.get_accessibility_data,
        name="get-initial-accessibility-data",
    ),
]
