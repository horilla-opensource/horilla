"""
Biometric App sidebar configuration
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as trans

from attendance.sidebar import SUBMENUS
from base.context_processors import biometric_app_exists
from biometric.context_processors import biometric_is_installed

biometric_submenu = {
    "menu": trans("Biometric Devices"),
    "redirect": reverse_lazy("view-biometric-devices"),
    "accessibility": "biometric.sidebar.biometric_device_accessibility",
}

SUBMENUS.insert(1, biometric_submenu)


def biometric_device_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Determine if the biometric device submenu should be accessible to the user.

    This function checks if the biometric app exists, if the user has the
    necessary permissions to view biometric devices, and if the biometric
    system is installed.

    Args:
        request: The HTTP request object.
        submenu: The submenu being accessed.
        user_perms: The permissions of the user.
        *args: Additional arguments.
        **kwargs: Additional keyword arguments.

    Returns:
        bool: True if the submenu should be accessible, False otherwise.
    """
    return (
        biometric_app_exists(None).get("biometric_app_exists")
        and request.user.has_perm("biometric.view_biometricdevices")
        and biometric_is_installed(None)["is_installed"]
    )
