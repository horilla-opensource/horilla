import os
import tempfile
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm

from .gdrive import authenticate
from .models import *


class LocalBackupSetupForm(ModelForm):
    verbose_name = "Server Backup"
    backup_db = forms.BooleanField(
        required=False, help_text="Enable to backup database to server."
    )
    backup_media = forms.BooleanField(
        required=False, help_text="Enable to backup all media files to server."
    )
    interval = forms.BooleanField(
        required=False,
        help_text="Enable to automate the backup in a period of seconds.",
    )
    fixed = forms.BooleanField(
        required=False, help_text="Enable to automate the backup in a fixed time."
    )

    class Meta:
        model = LocalBackup
        exclude = ["active"]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        backup_db = cleaned_data.get("backup_db")
        backup_media = cleaned_data.get("backup_media")
        interval = cleaned_data.get("interval")
        fixed = cleaned_data.get("fixed")
        seconds = cleaned_data.get("seconds")
        hour = cleaned_data.get("hour")
        minute = cleaned_data.get("minute")
        backup_path = cleaned_data.get("backup_path")
        path = Path(backup_path)
        if not path.exists():
            raise ValidationError({"backup_path": _("The directory does not exist.")})
        if backup_db == False and backup_media == False:
            raise forms.ValidationError("Please select any backup option.")
        if interval == False and fixed == False:
            raise forms.ValidationError("Please select any backup automate option.")
        if interval == True and seconds == None:
            raise ValidationError({"seconds": _("This field is required.")})
        if fixed == True and hour == None:
            raise ValidationError({"hour": _("This field is required.")})
        if seconds:
            if seconds < 0:
                raise ValidationError(
                    {"seconds": _("Negative value is not accepatable.")}
                )
        if hour:
            if hour < 0 or hour > 24:
                raise ValidationError({"hour": _("Enter a hour between 0 to 24.")})
        if minute:
            if minute < 0 or minute > 60:
                raise ValidationError({"minute": _("Enter a minute between 0 to 60.")})
        return cleaned_data


class GdriveBackupSetupForm(ModelForm):
    verbose_name = "Gdrive Backup"
    backup_db = forms.BooleanField(
        required=False,
        label="Backup DB",
        help_text="Enable to backup database to Gdrive",
    )
    backup_media = forms.BooleanField(
        required=False,
        label="Backup Media",
        help_text="Enable to backup all media files to Gdrive",
    )
    interval = forms.BooleanField(
        required=False,
        help_text="Enable to automate the backup in a period of seconds.",
    )
    fixed = forms.BooleanField(
        required=False, help_text="Enable to automate the backup in a fixed time."
    )

    class Meta:
        model = GoogleDriveBackup
        exclude = [
            "active",
            "access_token",
            "refresh_token",
            "token_expiry",
        ]  # Exclude token fields

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean(self):
        cleaned_data = super().clean()
        backup_db = cleaned_data.get("backup_db")
        backup_media = cleaned_data.get("backup_media")
        interval = cleaned_data.get("interval")
        fixed = cleaned_data.get("fixed")
        seconds = cleaned_data.get("seconds")
        hour = cleaned_data.get("hour")
        minute = cleaned_data.get("minute")
        oauth_credentials_file = cleaned_data.get("oauth_credentials_file")

        # Get instance if updating
        instance = self.instance if hasattr(self, "instance") else None

        # Only validate file if it's provided (new file upload) or if creating new instance
        if oauth_credentials_file:
            try:
                # Read file content from InMemoryUploadedFile
                file_data = oauth_credentials_file.read()
                file_name = oauth_credentials_file.name

                # Always write to temp file for validation (because .path isn't supported)
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".json", mode="w+b"
                ) as tmp_file:
                    tmp_file.write(file_data)
                    tmp_file.flush()
                    temp_path = tmp_file.name

                # Validate OAuth credentials file format
                import json

                with open(temp_path, "r") as f:
                    oauth_config = json.load(f)

                # Check if it's a valid OAuth 2.0 web application credentials file
                if "web" not in oauth_config:
                    raise ValueError(
                        "OAuth credentials file must contain 'web' key for web application type."
                    )

                if "client_id" not in oauth_config.get("web", {}):
                    raise ValueError(
                        "OAuth credentials file must contain 'client_id' in 'web' section."
                    )

                if "client_secret" not in oauth_config.get("web", {}):
                    raise ValueError(
                        "OAuth credentials file must contain 'client_secret' in 'web' section."
                    )

                # Clean up temp file
                os.remove(temp_path)

            except json.JSONDecodeError:
                raise forms.ValidationError(
                    "Please provide a valid OAuth credentials file (must be valid JSON)."
                )
            except Exception as e:
                raise forms.ValidationError(
                    f"Please provide a valid OAuth credentials file. Error: {str(e)}"
                )
        elif not instance or not instance.pk:
            # If creating new instance and no file provided, raise error
            raise forms.ValidationError(
                "Please provide a valid OAuth credentials file."
            )
        if backup_db == False and backup_media == False:
            raise forms.ValidationError("Please select any backup option.")
        if interval == False and fixed == False:
            raise forms.ValidationError("Please select any backup automate option.")
        if interval == True and seconds == None:
            raise ValidationError({"seconds": _("This field is required.")})
        if fixed == True and hour == None:
            raise ValidationError({"hour": _("This field is required.")})
        if seconds:
            if seconds < 0:
                raise ValidationError(
                    {"seconds": _("Negative value is not accepatable.")}
                )
        if hour:
            if hour < 0 or hour > 24:
                raise ValidationError({"hour": _("Enter a hour between 0 to 24.")})
        if minute:
            if minute < 0 or minute > 60:
                raise ValidationError({"minute": _("Enter a minute between 0 to 60.")})
        return cleaned_data
