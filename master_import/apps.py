from django.apps import AppConfig


class MasterImportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "master_import"
    verbose_name = "Master Data Import"
