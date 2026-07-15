from django.apps import AppConfig


class HydraShellConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_shell"
    verbose_name = "Hydra Shell"

    def ready(self):
        from horilla.horilla_settings import APPS

        from hydra_shell import checks  # noqa: F401

        if self.label not in APPS:
            APPS.append(self.label)

        super().ready()
