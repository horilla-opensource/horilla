"""
App configuration for the 'payroll' app.
"""

from django.apps import AppConfig
from django.db.models.signals import post_migrate


class PayrollConfig(AppConfig):
    """
    AppConfig for the 'payroll' app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "payroll"

    def ready(self) -> None:
        ready = super().ready()
        from django.urls import include, path

        from horilla.horilla_settings import APPS
        from horilla.urls import urlpatterns
        from payroll import signals

        APPS.append("payroll")
        urlpatterns.append(
            path("payroll/", include("payroll.urls.urls")),
        )
        try:
            from payroll.scheduler import auto_payslip_generate

            auto_payslip_generate()
        except:
            """
            Migrations are not affected
            """

        return ready
