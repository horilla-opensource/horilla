from django.apps import AppConfig


class HydraCoordinationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_coordination"
    verbose_name = "Hydra Coordination"

    def ready(self):
        from hydra.hydra_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)

        super().ready()
