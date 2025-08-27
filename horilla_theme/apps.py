from django.apps import AppConfig


class HorillaThemeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_theme"

    def ready(self):
        from . import forms, overrides

        return super().ready()
