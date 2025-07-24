"""
Module: urls

Description:
This module defines URL patterns for routing HTTP requests to views
in the biometric management application.
It imports the `path` function from `django.urls` for defining URL
patterns and imports views for handling requests.
Additionally, it imports the `BiometricDevices` model for use in URL patterns
that require device IDs.

"""

from django.urls import path

from . import views
from .models import BiometricDevices

urlpatterns = [
    path(
        "view-biometric-devices/",
        views.biometric_devices_view,
        name="view-biometric-devices",
    ),
    path(
        "biometric-device-live-capture",
        views.biometric_device_live,
        name="biometric-device-live-capture",
    ),
    path(
        "biometric-device-schedule/<uuid:device_id>/",
        views.biometric_device_schedule,
        name="biometric-device-schedule",
    ),
    path(
        "biometric-device-unschedule/<uuid:device_id>/",
        views.biometric_device_unschedule,
        name="biometric-device-unschedule",
    ),
    path(
        "biometric-device-test/<uuid:device_id>/",
        views.biometric_device_test,
        name="biometric-device-test",
    ),
    path(
        "biometric-device-fetch-logs/<uuid:device_id>/",
        views.biometric_device_fetch_logs,
        name="biometric-device-fetch-logs",
    ),
    path(
        "biometric-device-bulk-fetch-logs/",
        views.biometric_device_bulk_fetch_logs,
        name="biometric-device-bulk-fetch-logs",
    ),
    path(
        "biometric-device-add",
        views.biometric_device_add,
        name="biometric-device-add",
    ),
    path(
        "biometric-device-edit/<uuid:device_id>/",
        views.biometric_device_edit,
        name="biometric-device-edit",
    ),
    path(
        "biometric-device-delete/<uuid:device_id>/",
        views.biometric_device_delete,
        name="biometric-device-delete",
    ),
    path(
        "biometric-device-archive/<uuid:device_id>/",
        views.biometric_device_archive,
        name="biometric-device-archive",
    ),
    path(
        "biometric-device-employees/<uuid:device_id>/",
        views.biometric_device_employees,
        name="biometric-device-employees",
        kwargs={"model": BiometricDevices},
    ),
    path(
        "search-employee-in-device",
        views.search_employee_device,
        name="search-employee-in-device",
    ),
    path(
        "find-employee-badge-id",
        views.find_employee_badge_id,
        name="find-employee-badge-id",
    ),
    path(
        "add-biometric-user/<uuid:device_id>/",
        views.add_biometric_user,
        name="add-biometric-user",
    ),
    path(
        "map-biometric-users/<uuid:device_id>/",
        views.map_biometric_users,
        name="map-biometric-users",
    ),
    path(
        "add-dahua-biometric-user/<uuid:device_id>/",
        views.add_dahua_biometric_user,
        name="add-dahua-biometric-user",
    ),
    path(
        "delete-dahua-user/<uuid:obj_id>",
        views.delete_dahua_user,
        name="delete-dahua-user",
    ),
    path(
        "delete-dahua-user",
        views.delete_dahua_user,
        name="delete-dahua-user",
    ),
    path(
        "delete-etimeoffice-user",
        views.delete_etimeoffice_user,
        name="delete-etimeoffice-user",
    ),
    path(
        "delete-etimeoffice-user/<uuid:obj_id>",
        views.delete_etimeoffice_user,
        name="delete-etimeoffice-user",
    ),
    path(
        "enable-cosec-face-recognition/<str:user_id>/<uuid:device_id>/",
        views.enable_cosec_face_recognition,
        name="enable-cosec-face-recognition",
    ),
    path(
        "edit-cosec-user/<str:user_id>/<uuid:device_id>/",
        views.edit_cosec_user,
        name="edit-cosec-user",
    ),
    path(
        "delete-biometric-user/<int:uid>/<uuid:device_id>/",
        views.delete_biometric_user,
        name="delete-biometric-user",
    ),
    path(
        "delete-cosec-user/<str:user_id>/<uuid:device_id>/",
        views.delete_horilla_cosec_user,
        name="delete-cosec-user",
    ),
    path(
        "biometric-users-bulk-delete",
        views.bio_users_bulk_delete,
        name="biometric-users-bulk-delete",
    ),
    path(
        "cosec-users-bulk-delete",
        views.cosec_users_bulk_delete,
        name="cosec-users-bulk-delete",
    ),
]
