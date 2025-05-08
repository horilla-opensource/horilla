import atexit


def shutdown_function():
    from horilla_backup.models import GoogleDriveBackup, LocalBackup

    try:
        if GoogleDriveBackup.objects.exists():
            google_drive_backup = GoogleDriveBackup.objects.first()
            google_drive_backup.active = False
            google_drive_backup.save()
        if LocalBackup.objects.exists():
            local_backup = LocalBackup.objects.first()
            local_backup.active = False
            local_backup.save()
    except:
        pass


try:
    atexit.register(shutdown_function)
except:
    pass
