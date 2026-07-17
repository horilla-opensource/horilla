from django.apps import AppConfig


class HydraPeopleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_people"
    verbose_name = "Hydra People"

    def ready(self):
        from hydra.hydra_settings import APPS
        from hydra_people import signals  # noqa: F401

        if self.label not in APPS:
            APPS.append(self.label)

        super().ready()
