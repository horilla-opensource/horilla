from django.apps import AppConfig


class HydraHousingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_housing"
    verbose_name = "Hydra Housing"

    def ready(self):
        from horilla.horilla_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
