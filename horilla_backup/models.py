from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class LocalBackup(models.Model):
    backup_path = models.CharField(
        max_length=255,
        help_text=_("Specify the path in the server were the backup files should keep"),
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
    oauth_credentials_file = models.FileField(
        upload_to="gdrive_oauth_credentials_file",
        verbose_name=_("OAuth Credentials File"),
        blank=True,
        null=True,
        help_text=_(
            "Make sure your file is in JSON format and contains your Google OAuth 2.0 client credentials (web application type)"
        ),
    )
    gdrive_folder_id = models.CharField(
        max_length=255,
        verbose_name=_("Gdrive Folder ID"),
        help_text=_(
            "Google Drive folder ID where backups will be stored. The authenticated user must have write access to this folder."
        ),
    )
    access_token = models.TextField(
        blank=True, null=True, help_text=_("OAuth access token (automatically managed)")
    )
    refresh_token = models.TextField(
        blank=True,
        null=True,
        help_text=_("OAuth refresh token (automatically managed)"),
    )
    token_expiry = models.DateTimeField(
        blank=True, null=True, help_text=_("Token expiry time (automatically managed)")
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
