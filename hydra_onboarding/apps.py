from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HydraOnboardingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_onboarding"
    verbose_name = _("Hydra onboarding content")
