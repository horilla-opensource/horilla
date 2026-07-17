from django.apps import AppConfig


class HydraAuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hydra_audit"
    # Keep the historical label so existing tables, content types, and
    # permissions remain valid after the Python package rename.
    label = "horilla_audit"
