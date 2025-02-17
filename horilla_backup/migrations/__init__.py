import atexit
from django.db import connection

def shutdown_function():
    from horilla_backup.models import GoogleDriveBackup, LocalBackup

    # Check if the database is ready and the tables exist
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'horilla_backup_googledrivebackup';"
        )
        table_exists = cursor.fetchone()[0] > 0

    if not table_exists:
        return  # Skip shutdown tasks if the table doesn't exist

    if GoogleDriveBackup.objects.exists():
        google_drive_backup = GoogleDriveBackup.objects.first()
        google_drive_backup.active = False
        google_drive_backup.save()

    if LocalBackup.objects.exists():
        local_backup = LocalBackup.objects.first()
        local_backup.active = False
        local_backup.save()

try:
    atexit.register(shutdown_function)
except:
    pass
