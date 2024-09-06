"""
Utility functions related to biometric attendance.

This file contains utility functions related to biometric attendance,
including a function to check if the biometric system is installed.

Functions:
    biometric_is_installed(request): Checks if the biometric system is installed.
"""

from base.models import BiometricAttendance


def biometric_is_installed(_request):
    """
    Check if the biometric system is installed.

    This function checks if the biometric system is installed by querying the
    BiometricAttendance model. If no BiometricAttendance object exists, it
    creates one with 'is_installed' set to False.

    Args:
        request: The HTTP request object.

    Returns:
        dict: A dictionary containing a single key-value pair indicating whether
        the biometric system is installed. The key is 'is_installed', and the value
        is a boolean indicating the installation status.
    """
    instance = BiometricAttendance.objects.first()
    if not instance:
        BiometricAttendance.objects.create(is_installed=False)
        instance = BiometricAttendance.objects.first()
    is_installed = instance.is_installed
    return {"is_installed": is_installed}
