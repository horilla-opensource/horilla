import os

from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command

from horilla import settings

from .gdrive import *

# from horilla.settings import DBBACKUP_STORAGE_OPTIONS
from .models import *
from .pgdump import *
from .zip import *

scheduler = BackgroundScheduler()

# def backup_database():
#     folder_path = DBBACKUP_STORAGE_OPTIONS['location']
#     local_backup = LocalBackup.objects.first()
#     if folder_path and local_backup:
#         DBBACKUP_STORAGE_OPTIONS['location'] = local_backup.backup_path
#         folder_path = DBBACKUP_STORAGE_OPTIONS['location']
#         if local_backup.backup_db:
#             call_command('dbbackup')
#         if local_backup.backup_media:
#             call_command("mediabackup")
#         files = sorted(os.listdir(folder_path), key=lambda x: os.path.getctime(os.path.join(folder_path, x)))

#         # Remove all files except the last two
#         if len(files) > 2:
#             for file_name in files[:-2]:
#                 file_path = os.path.join(folder_path, file_name)
#                 if os.path.isfile(file_path):
#                     try:
#                         os.remove(file_path)
#                     except:
#                         pass


# def start_backup_job():
#     """
#     Start the backup job based on the LocalBackup configuration.
#     """
#     # Check if any LocalBackup object exists
#     if LocalBackup.objects.exists():
#         local_backup = LocalBackup.objects.first()

#             # Remove existing job if it exists
#         try:
#             scheduler.remove_job('backup_job')
#         except:
#             pass

#         # Add new job based on LocalBackup configuration
#         if local_backup.interval:
#             scheduler.add_job(backup_database, 'interval', seconds=local_backup.seconds, id='backup_job')
#         else:
#             scheduler.add_job(backup_database, trigger='cron', hour=local_backup.hour, minute=local_backup.minute, id='backup_job')
#         # Start the scheduler if it's not already running
#         if not scheduler.running:
#             scheduler.start()
#     else:
#         stop_backup_job()


# def stop_backup_job():
#     """
#     Stop the backup job if it exists.
#     """
#     try:
#         scheduler.remove_job('backup_job')
#     except:
#         pass


# def restart_backup_job():
#     """
#     Restart the backup job by stopping it and starting it again.
#     """
#     stop_backup_job()
#     start_backup_job()


def google_drive_backup():
    if GoogleDriveBackup.objects.exists():
        google_drive = GoogleDriveBackup.objects.first()
        gdrive_folder_id = google_drive.gdrive_folder_id

        # Check if OAuth tokens exist
        if not google_drive.access_token:
            # Log error or skip backup if not authorized
            print(
                "Google Drive backup skipped: OAuth tokens not found. Please authorize the application."
            )
            return

        try:
            db_backup_success = False
            media_backup_success = False

            if google_drive.backup_db:
                try:
                    print("=== Starting Database Backup ===")
                    db = settings.DATABASES["default"]
                    dump_postgres_db(
                        db_name=db["NAME"],
                        username=db["USER"],
                        output_file="backupdb.dump",
                        password=db["PASSWORD"],
                    )
                    upload_file("backupdb.dump", google_drive, gdrive_folder_id)
                    os.remove("backupdb.dump")
                    db_backup_success = True
                    print("=== Database Backup Completed Successfully ===")
                except Exception as db_error:
                    print(f"Database backup failed: {str(db_error)}")
                    import traceback

                    print(traceback.format_exc())
                    # Clean up dump file if it exists
                    if os.path.exists("backupdb.dump"):
                        try:
                            os.remove("backupdb.dump")
                        except:
                            pass

            if google_drive.backup_media:
                try:
                    print("=== Starting Media Backup ===")
                    folder_to_zip = settings.MEDIA_ROOT
                    output_zip_file = "media.zip"

                    # Check if media folder exists
                    if not os.path.exists(folder_to_zip):
                        raise Exception(f"Media folder does not exist: {folder_to_zip}")

                    # Check if media folder has any files
                    media_files = []
                    for root, dirs, files in os.walk(folder_to_zip):
                        media_files.extend(files)

                    if not media_files:
                        print(
                            f"Warning: Media folder appears to be empty: {folder_to_zip}"
                        )
                        # Still create an empty zip to indicate backup was attempted

                    print(
                        f"Zipping media folder: {folder_to_zip} ({len(media_files)} files found)"
                    )
                    zip_folder(folder_to_zip, output_zip_file)

                    # Check if zip file was created
                    if not os.path.exists(output_zip_file):
                        raise Exception("Failed to create media.zip file")

                    zip_size = os.path.getsize(output_zip_file)
                    print(f"Media zip created successfully. Size: {zip_size} bytes")

                    print(
                        f"Uploading media.zip to Google Drive (folder ID: {gdrive_folder_id})..."
                    )
                    upload_file(output_zip_file, google_drive, gdrive_folder_id)
                    print(f"Media backup uploaded successfully to Google Drive")

                    # Clean up zip file
                    os.remove(output_zip_file)
                    print(f"Temporary media.zip file removed")
                    media_backup_success = True
                    print("=== Media Backup Completed Successfully ===")
                except Exception as media_error:
                    print(f"=== Media Backup Failed ===")
                    print(f"Error: {str(media_error)}")
                    import traceback

                    print(traceback.format_exc())
                    # Remove zip file if it exists
                    if os.path.exists("media.zip"):
                        try:
                            os.remove("media.zip")
                        except:
                            pass
                    # Don't re-raise - allow DB backup to continue even if media fails

            # Summary
            db_enabled = google_drive.backup_db
            media_enabled = google_drive.backup_media

            if db_enabled and not db_backup_success:
                print("WARNING: Database backup failed")
            if media_enabled and not media_backup_success:
                print("WARNING: Media backup failed")

            # Determine overall status
            if db_enabled and media_enabled:
                # Both enabled
                if db_backup_success and media_backup_success:
                    print("=== Backup Job Completed Successfully ===")
                elif db_backup_success or media_backup_success:
                    print("=== Backup Job Completed (with some failures) ===")
                else:
                    print("=== Backup Job Failed ===")
            elif db_enabled:
                # Only DB enabled
                if db_backup_success:
                    print("=== Database Backup Completed Successfully ===")
                else:
                    print("=== Database Backup Failed ===")
            elif media_enabled:
                # Only Media enabled
                if media_backup_success:
                    print("=== Media Backup Completed Successfully ===")
                else:
                    print("=== Media Backup Failed ===")
        except Exception as e:
            # Log the error - in production you might want to use proper logging
            print(f"=== Google Drive Backup Job Failed ===")
            print(f"Error: {str(e)}")
            import traceback

            print(traceback.format_exc())
            # Optionally, you could disable the backup if tokens are invalid
            # google_drive.active = False
            # google_drive.save()


def start_gdrive_backup_job():
    """
    Start the backup job based on the LocalBackup configuration.
    """
    # Check if any Gdrive Backup object exists
    if GoogleDriveBackup.objects.exists():
        gdrive_backup = GoogleDriveBackup.objects.first()

        # Remove existing job if it exists
        try:
            scheduler.remove_job("backup_job")
        except:
            pass
        # Add new job based on Gdrive Backup configuration
        if gdrive_backup.interval:
            scheduler.add_job(
                google_drive_backup,
                "interval",
                seconds=gdrive_backup.seconds,
                id="gdrive_backup_job",
            )
        else:
            scheduler.add_job(
                google_drive_backup,
                trigger="cron",
                hour=gdrive_backup.hour,
                minute=gdrive_backup.minute,
                id="gdrive_backup_job",
            )

        # Start the scheduler if it's not already running
        if not scheduler.running:
            scheduler.start()
    else:
        stop_gdrive_backup_job()


def stop_gdrive_backup_job():
    """
    Stop the backup job if it exists.
    """
    try:
        scheduler.remove_job("gdrive_backup_job")
    except:
        pass


# def restart_gdrive_backup_job():
#     """
#     Restart the backup job by stopping it and starting it again.
#     """
#     stop_gdrive_backup_job()
#     start_gdrive_backup_job()
