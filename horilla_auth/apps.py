from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_auth"
    verbose_name = _("Horilla Auth")
