from django.apps import AppConfig


class HydraArrivalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_arrivals"
    verbose_name = "Hydra Arrivals"

    def ready(self):
        from horilla.horilla_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
