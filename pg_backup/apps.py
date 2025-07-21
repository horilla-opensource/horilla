from django.apps import AppConfig


class PgGitBackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pg_backup"

    def ready(self):
        from pg_backup import scheduler

        return super().ready()
