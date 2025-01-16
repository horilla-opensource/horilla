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

        from horilla.settings import MIDDLEWARE
        from horilla.urls import urlpatterns

        urlpatterns.append(
            path("attendance/", include("attendance.urls")),
        )
        middleware_path = "attendance.middleware.AttendanceMiddleware"
        if middleware_path not in MIDDLEWARE:
            MIDDLEWARE.append(middleware_path)

        APP_URLS.append("attendance.urls")  # Used to remove Dynamically Added Urls
        try:
            self.create_enable_disable_check_in()
        except:
            pass
        super().ready()

    def create_enable_disable_check_in(self):
        """
        Checks if an AttendanceGeneralSetting object exists for each company.
        If it doesn't exist, creates one.
        """
        from attendance.models import AttendanceGeneralSetting
        from base.models import Company

        companies = Company.objects.all()
        for company in companies:
            if not AttendanceGeneralSetting.objects.filter(company_id=company).exists():
                try:
                    AttendanceGeneralSetting.objects.create(company_id=company)
                except:
                    pass
        AttendanceGeneralSetting.objects.get_or_create(company_id=None)
