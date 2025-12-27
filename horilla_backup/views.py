import json
import os

from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from horilla.decorators import (
    hx_request_required,
    login_required,
    manager_can_enter,
    owner_can_enter,
    permission_required,
)

from .forms import *
from .gdrive import *
from .pgdump import *
from .scheduler import *
from .zip import *

# @login_required
# @permission_required("backup.add_localbackup")
# def local_setup(request):
#     """
#     function used to setup local backup.

#     Parameters:
#     request (HttpRequest): The HTTP request object.

#     Returns:
#     GET : return local backup setup template
#     POST : return settings
#     """
#     form = LocalBackupSetupForm()
#     show = False
#     active = False
#     if LocalBackup.objects.exists():
#         form = LocalBackupSetupForm(instance=LocalBackup.objects.first())
#         show = True
#         active = LocalBackup.objects.first().active
#     if request.method == "POST":
#         form = LocalBackupSetupForm(request.POST, request.FILES)
#         if form.is_valid():
#             form.save()
#             stop_backup_job()
#             messages.success(request, _("Local backup automation setup updated."))
#             return redirect("local")
#     return render(request, "backup/local_setup_form.html", {"form": form, "show":show, "active":active})


# @login_required
# @permission_required("backup.change_localbackup")
# def local_Backup_stop_or_start(request):
#     """
#     function used to stop or start local backup.

#     Parameters:
#     request (HttpRequest): The HTTP request object.

#     Returns:
#     GET : return local backup setup template
#     POST : return settings
#     """
#     if LocalBackup.objects.exists():
#         local_backup = LocalBackup.objects.first()
#         if local_backup.active == True:
#             local_backup.active = False
#             stop_backup_job()
#             message = "Local Backup Automation Stopped Successfully."
#         else:
#             local_backup.active = True
#             start_backup_job()
#             message = "Local Backup Automation Started Successfully."
#         local_backup.save()
#         messages.success(request, _(message))
#     return redirect("local")


# @login_required
# @permission_required("backup.delete_localbackup")
# def local_Backup_delete(request):
#     """
#     function used to delete local backup.

#     Parameters:
#     request (HttpRequest): The HTTP request object.

#     Returns:
#     GET : return local backup setup template
#     POST : return settings
#     """
#     if LocalBackup.objects.exists():
#         local_backup = LocalBackup.objects.first()
#         local_backup.delete()
#         stop_backup_job()
#         messages.success(request, _("Local Backup Automation Removed Successfully."))
#     return redirect("local")


@login_required
@permission_required("backup.add_localbackup")
def gdrive_setup(request):
    """
    function used to setup gdrive backup.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return gdrive backup setup template
    POST : return gdrive backup update template
    """
    form = GdriveBackupSetupForm()
    show = False
    active = False
    needs_auth = False

    if connection.vendor != "postgresql":
        return render(request, "backup/404.html")

    if GoogleDriveBackup.objects.exists():
        instance = GoogleDriveBackup.objects.first()
        form = GdriveBackupSetupForm(instance=instance)
        show = True
        active = GoogleDriveBackup.objects.first().active

        # Check if OAuth tokens exist - need both credentials file and access token
        if instance.oauth_credentials_file:
            if not instance.access_token:
                needs_auth = True
        else:
            # No credentials file uploaded yet
            needs_auth = False  # Don't show auth button if no credentials file

        if request.method == "POST":
            form = GdriveBackupSetupForm(request.POST, request.FILES, instance=instance)
            if form.is_valid():
                google_drive = form.save()
                google_drive.active = False
                google_drive.save()
                stop_gdrive_backup_job()

                # If credentials file was updated, reset tokens
                if "oauth_credentials_file" in request.FILES:
                    google_drive.access_token = None
                    google_drive.refresh_token = None
                    google_drive.token_expiry = None
                    google_drive.save()
                    messages.success(
                        request,
                        _(
                            "OAuth credentials file uploaded. Please authorize Google Drive access."
                        ),
                    )
                else:
                    messages.success(
                        request, _("gdrive backup automation setup updated.")
                    )
                return redirect("gdrive")

        # Re-check needs_auth after potential updates
        if instance.oauth_credentials_file and not instance.access_token:
            needs_auth = True

        return render(
            request,
            "backup/gdrive_setup_form.html",
            {"form": form, "show": show, "active": active, "needs_auth": needs_auth},
        )

    if request.method == "POST":
        form = GdriveBackupSetupForm(request.POST, request.FILES)
        if form.is_valid():
            google_drive = form.save()
            # After saving, check if tokens are needed
            if not google_drive.access_token:
                needs_auth = True
            messages.success(request, _("gdrive backup automation setup Created."))
            return redirect("gdrive")

    return render(
        request,
        "backup/gdrive_setup_form.html",
        {"form": form, "show": show, "active": active, "needs_auth": needs_auth},
    )


@login_required
@permission_required("backup.change_localbackup")
def gdrive_Backup_stop_or_start(request):
    """
    function used to stop or start gdrive backup.

    Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return gdrive backup setup template
    POST : return gdrive backup update template
    """
    if GoogleDriveBackup.objects.exists():
        gdive_backup = GoogleDriveBackup.objects.first()
        if gdive_backup.active == True:
            gdive_backup.active = False
            stop_gdrive_backup_job()
            message = "Gdrive Backup Automation Stopped Successfully."
        else:
            gdive_backup.active = True
            start_gdrive_backup_job()
            message = "Gdrive Backup Automation Started Successfully."
        gdive_backup.save()
        messages.success(request, _(message))
    return redirect("gdrive")


@login_required
@permission_required("backup.delete_localbackup")
def gdrive_Backup_delete(request):
    """
    function used to delete gdrive backup.

        Parameters:
    request (HttpRequest): The HTTP request object.

    Returns:
    GET : return gdrive backup setup template
    """
    if GoogleDriveBackup.objects.exists():
        gdrive_backup = GoogleDriveBackup.objects.first()
        gdrive_backup.delete()
        stop_gdrive_backup_job()
        messages.success(request, _("Gdrive Backup Automation Removed Successfully."))
    return redirect("gdrive")


@login_required
@permission_required("backup.add_localbackup")
def gdrive_authorize(request):
    """
    Initiate OAuth authorization flow for Google Drive.
    """
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # For local development with HTTP

    if not GoogleDriveBackup.objects.exists():
        messages.error(request, _("Please set up Google Drive backup first."))
        return redirect("gdrive")

    google_drive = GoogleDriveBackup.objects.first()

    if not google_drive.oauth_credentials_file:
        messages.error(request, _("Please upload OAuth credentials file first."))
        return redirect("gdrive")

    try:
        # Read OAuth credentials file
        oauth_file_path = google_drive.oauth_credentials_file.path
        with open(oauth_file_path, "r") as f:
            client_config = json.load(f)

        # Use redirect URI from credentials file if available, otherwise construct it
        if (
            "web" in client_config
            and "redirect_uris" in client_config["web"]
            and len(client_config["web"]["redirect_uris"]) > 0
        ):
            redirect_uri = client_config["web"]["redirect_uris"][0]
        else:
            scheme = "https" if not settings.DEBUG else "http"
            host = request.get_host()
            redirect_uri = f"{scheme}://{host}/google/callback/"

        # Store client config and redirect URI in session for callback
        request.session["gdrive_oauth_client_config"] = json.dumps(client_config)
        request.session["gdrive_oauth_redirect_uri"] = redirect_uri

        # Generate authorization URL
        authorization_url, flow, state = get_authorization_url(
            oauth_file_path, redirect_uri
        )

        # Store state in session for verification
        request.session["gdrive_oauth_state"] = state

        return redirect(authorization_url)
    except Exception as e:
        messages.error(request, _(f"Failed to initiate authorization: {str(e)}"))
        return redirect("gdrive")


@login_required
@permission_required("backup.add_localbackup")
def gdrive_callback(request):
    """
    Handle OAuth callback from Google.
    """
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # For local development with HTTP

    if not GoogleDriveBackup.objects.exists():
        messages.error(request, _("Google Drive backup not configured."))
        return redirect("gdrive")

    google_drive = GoogleDriveBackup.objects.first()

    # Check for error in callback
    if "error" in request.GET:
        error = request.GET.get("error")
        messages.error(request, _(f"Authorization failed: {error}"))
        return redirect("gdrive")

    # Check for authorization code
    if "code" not in request.GET:
        messages.error(request, _("Authorization code not received."))
        return redirect("gdrive")

    # Verify session data exists
    if (
        "gdrive_oauth_client_config" not in request.session
        or "gdrive_oauth_redirect_uri" not in request.session
    ):
        messages.error(request, _("Session expired. Please try authorizing again."))
        return redirect("gdrive")

    try:
        # Recreate flow from stored client config
        client_config = json.loads(request.session["gdrive_oauth_client_config"])
        redirect_uri = request.session["gdrive_oauth_redirect_uri"]

        flow = Flow.from_client_config(client_config, SCOPES, redirect_uri=redirect_uri)

        # Exchange authorization code for tokens
        full_url = request.build_absolute_uri()
        flow.fetch_token(authorization_response=full_url)
        creds = flow.credentials

        # Store tokens in model
        google_drive.access_token = creds.token
        if creds.refresh_token:
            google_drive.refresh_token = creds.refresh_token
        if creds.expiry:
            from django.utils import timezone

            if timezone.is_naive(creds.expiry):
                google_drive.token_expiry = timezone.make_aware(
                    creds.expiry, timezone.utc
                )
            else:
                google_drive.token_expiry = creds.expiry
        google_drive.save()

        # Clean up session
        if "gdrive_oauth_client_config" in request.session:
            del request.session["gdrive_oauth_client_config"]
        if "gdrive_oauth_redirect_uri" in request.session:
            del request.session["gdrive_oauth_redirect_uri"]
        if "gdrive_oauth_state" in request.session:
            del request.session["gdrive_oauth_state"]

        messages.success(request, _("Google Drive authorization successful!"))
        return redirect("gdrive")
    except Exception as e:
        import traceback

        print(f"OAuth callback error: {traceback.format_exc()}")
        messages.error(request, _(f"Authorization failed: {str(e)}"))
        return redirect("gdrive")
