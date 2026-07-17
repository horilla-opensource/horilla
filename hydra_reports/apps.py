from django.apps import AppConfig


class HydraReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_reports"
    verbose_name = "Hydra Reports"

    def ready(self):
        from hydra.hydra_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
