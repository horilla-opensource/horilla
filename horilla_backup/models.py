from django.db import models

# Create your models here.


class LocalBackup(models.Model):
    backup_path = models.CharField(
        max_length=255,
        help_text="Specify the path in the server were the backup files should keep",
    )
    backup_media = models.BooleanField(blank=True, null=True)
    backup_db = models.BooleanField(blank=True, null=True)
    interval = models.BooleanField(blank=True, null=True)
    fixed = models.BooleanField(blank=True, null=True)
    seconds = models.IntegerField(blank=True, null=True)
    hour = models.IntegerField(blank=True, null=True)
    minute = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Check if there's an existing instance
        if self.interval == False:
            self.seconds = None
        if self.fixed == False:
            self.hour = None
            self.minute = None
        if LocalBackup.objects.exists():
            # Get the existing instance
            existing_instance = LocalBackup.objects.first()
            # Update the fields of the existing instance with the new data
            for field in self._meta.fields:
                if field.name != "id":  # Avoid changing the primary key
                    setattr(existing_instance, field.name, getattr(self, field.name))
            # Save the updated instance
            super(LocalBackup, existing_instance).save(*args, **kwargs)
            return existing_instance
        else:
            # If no existing instance, proceed with regular save
            super(LocalBackup, self).save(*args, **kwargs)
            return self


class GoogleDriveBackup(models.Model):
    service_account_file = models.FileField(
        upload_to="gdrive_service_account_file",
        verbose_name="Service Account File",
        help_text="Make sure your file is in JSON format and contains your Google Service Account credentials",
    )
    gdrive_folder_id = models.CharField(
        max_length=255,
        verbose_name="Gdrive Folder ID",
        help_text="Shared Gdrive folder Id with access granted to Gmail service account. Enable full permissions for seamless connection.",
    )
    backup_media = models.BooleanField(blank=True, null=True)
    backup_db = models.BooleanField(blank=True, null=True)
    interval = models.BooleanField(blank=True, null=True)
    fixed = models.BooleanField(blank=True, null=True)
    seconds = models.IntegerField(blank=True, null=True)
    hour = models.IntegerField(blank=True, null=True)
    minute = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Check if there's an existing instance
        if self.interval == False:
            self.seconds = None
        if self.fixed == False:
            self.hour = None
            self.minute = None
        if GoogleDriveBackup.objects.exists():
            # Get the existing instance
            existing_instance = GoogleDriveBackup.objects.first()
            # Update the fields of the existing instance with the new data
            for field in self._meta.fields:
                if field.name != "id":  # Avoid changing the primary key
                    setattr(existing_instance, field.name, getattr(self, field.name))
            # Save the updated instance
            super(GoogleDriveBackup, existing_instance).save(*args, **kwargs)
            return existing_instance
        else:
            # If no existing instance, proceed with regular save
            super(GoogleDriveBackup, self).save(*args, **kwargs)
            return self
