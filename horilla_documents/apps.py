from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaDoumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_documents"
    verbose_name = _("Documents")
