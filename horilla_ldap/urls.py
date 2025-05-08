"""
urls.py

This module is used to map url path with view methods.
"""

from django.urls import path

from horilla_ldap import views

urlpatterns = [
    path("settings/ldap-settings/", views.ldap_settings_view, name="ldap-settings"),
]
