from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

from attendance.sidebar import SUBMENUS
from base.context_processors import biometric_app_exists
from biometric.context_processors import biometric_is_installed

biometric_submenu = {
    "menu": trans("Biometric Devices"),
    "redirect": reverse("view-biometric-devices"),
    "accessibility": "biometric.sidebar.biometric_device_accessibility",
}

SUBMENUS.insert(1, biometric_submenu)


def biometric_device_accessibility(request, submenu, user_perms, *args, **kwargs):
    return (
        biometric_app_exists(None).get("biometric_app_exists")
        and request.user.has_perm("biometric.view_biometricdevices")
        and biometric_is_installed(None)["is_installed"]
    )
