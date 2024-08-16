from django.apps import AppConfig


class AttendanceConfig(AppConfig):
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

        super().ready()
