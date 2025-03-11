"""
This module defines the configuration for the 'attendance' app within the Horilla HRMS project.
"""

from django.apps import AppConfig

from horilla.horilla_settings import APP_URLS


class AttendanceConfig(AppConfig):
    """
    Configures the 'attendance' app and performs additional setup during the app's
    initialization. This includes appending the 'attendance' URL patterns to the
    project's main urlpatterns and dynamically adding the 'AttendanceMiddleware'
    to the middleware stack if it's not already present.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "attendance"

    def ready(self):
        from django.urls import include, path

        from attendance import scheduler, signals
        from horilla.horilla_settings import APPS
        from horilla.settings import MIDDLEWARE
        from horilla.urls import urlpatterns

        APPS.append("attendance")
        urlpatterns.append(
            path("attendance/", include("attendance.urls")),
        )
        middleware_path = "attendance.middleware.AttendanceMiddleware"
        if middleware_path not in MIDDLEWARE:
            MIDDLEWARE.append(middleware_path)

        APP_URLS.append("attendance.urls")

        super().ready()
