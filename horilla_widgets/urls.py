"""
horilla_widget/urls.py
"""

from django.urls import path

from horilla_widgets import views

urlpatterns = [
    path("get-filter-form", views.get_filter_form, name="get-filter-form"),
]
