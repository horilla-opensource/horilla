from django.urls import path

from hydra_reports import views


urlpatterns = [
    path("", views.operational_report, name="hydra-operational-report"),
    path(
        "export/",
        views.operational_report_export,
        name="hydra-operational-report-export",
    ),
]
