from django.apps import AppConfig


class HydraTasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_tasks"
    verbose_name = "Hydra Tasks"

    def ready(self):
        from hydra.hydra_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
