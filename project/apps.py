from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project"

    def ready(self):
        from horilla.horilla_settings import APPS

        APPS.append("project")
        super().ready()
