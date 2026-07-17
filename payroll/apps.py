"""
App configuration for the 'payroll' app.
"""

from django.apps import AppConfig
from django.db.models.signals import post_migrate

from hydra.scheduling import should_start_schedulers


class PayrollConfig(AppConfig):
    """
    AppConfig for the 'payroll' app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "payroll"

    def ready(self) -> None:
        ready = super().ready()
        from django.urls import include, path

        from hydra.hydra_settings import APPS
        from hydra.urls import urlpatterns
        from payroll import signals

        APPS.append("payroll")
        urlpatterns.append(
            path("payroll/", include("payroll.urls.urls")),
        )
        try:
            if should_start_schedulers():
                from payroll.scheduler import auto_payslip_generate

                auto_payslip_generate()
        except Exception:
            """
            Migrations are not affected
            """

        return ready
