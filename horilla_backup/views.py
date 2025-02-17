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
    if connection.vendor != "postgresql":
        return render(request, "backup/404.html")
    if GoogleDriveBackup.objects.exists():
        instance = GoogleDriveBackup.objects.first()
        form = GdriveBackupSetupForm(instance=instance)
        show = True
        active = GoogleDriveBackup.objects.first().active
        if request.method == "POST":
            form = GdriveBackupSetupForm(request.POST, request.FILES, instance=instance)
            if form.is_valid():
                google_drive = form.save()
                google_drive.active = False
                google_drive.save()
                stop_gdrive_backup_job()
                messages.success(request, _("gdrive backup automation setup updated."))
                return redirect("gdrive")
        return render(
            request,
            "backup/gdrive_setup_form.html",
            {"form": form, "show": show, "active": active},
        )

    if request.method == "POST":
        form = GdriveBackupSetupForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("gdrive backup automation setup Created."))
            return redirect("gdrive")
    return render(
        request,
        "backup/gdrive_setup_form.html",
        {"form": form, "show": show, "active": active},
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
