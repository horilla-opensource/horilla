from django.urls import path

from .views import *

urlpatterns = [
    # path("local/", local_setup, name="local"),
    # path("start-stop/", local_Backup_stop_or_start, name="start_stop"),
    # path("delete/", local_Backup_delete, name="backup_delete"),
    path("gdrive/", gdrive_setup, name="gdrive"),
    path("gdrive-start-stop/", gdrive_Backup_stop_or_start, name="gdrive_start_stop"),
    path("gdrive-delete/", gdrive_Backup_delete, name="gdrive_delete"),
]
