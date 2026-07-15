from django.apps import AppConfig


class HydraLinksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_links"
    verbose_name = "Hydra Public Links"

    def ready(self):
        from horilla.horilla_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
