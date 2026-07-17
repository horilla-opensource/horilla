from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, register


@register()
def private_storage_check(app_configs, **kwargs):
    private_root = Path(settings.HYDRA_PRIVATE_MEDIA_ROOT).resolve()
    public_root = Path(settings.MEDIA_ROOT).resolve()
    if (
        private_root == public_root
        or public_root in private_root.parents
        or private_root in public_root.parents
    ):
        errors = [
            Error(
                "HYDRA_PRIVATE_MEDIA_ROOT must be outside MEDIA_ROOT.",
                hint="Configure a non-public directory that is not served by /media/.",
                id="hydra_documents.E001",
            )
        ]
    else:
        errors = []
    quarantine_root = Path(settings.HYDRA_DOCUMENT_QUARANTINE_ROOT).resolve()
    roots = (public_root, private_root)
    if any(
        quarantine_root == root
        or root in quarantine_root.parents
        or quarantine_root in root.parents
        for root in roots
    ):
        errors.append(
            Error(
                "HYDRA_DOCUMENT_QUARANTINE_ROOT must be isolated from public and private media.",
                hint="Configure a dedicated non-public quarantine directory.",
                id="hydra_documents.E002",
            )
        )
    return errors


class HydraDocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_documents"
    verbose_name = "Hydra Private Documents"

    def ready(self):
        from horilla.horilla_settings import APPS

        if self.label not in APPS:
            APPS.append(self.label)
        super().ready()
