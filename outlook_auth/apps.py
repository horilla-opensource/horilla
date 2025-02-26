from django.apps import AppConfig


class OutlookAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "outlook_auth"

    def ready(self):
        from horilla.urls import include, path, urlpatterns

        urlpatterns.append(
            path("outlook/", include("outlook_auth.urls")),
        )
        return super().ready()
