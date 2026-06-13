"""
Utility functions related to biometric attendance.

This file contains utility functions related to biometric attendance,
including a function to check if the biometric system is installed.

Functions:
    biometric_is_installed(request): Checks if the biometric system is installed.
"""

from base.models import BiometricAttendance, Company


def biometric_is_installed(request):
    """
    Check if the biometric system is installed for the selected company.

    Args:
        request: The HTTP request object.

    Returns:
        dict: A dictionary with 'is_installed' boolean for the selected company.
    """
    selected_company = (
        request.session.get("selected_company") if hasattr(request, "session") else None
    )
    if selected_company == "all":
        company = None
    else:
        company = (
            Company.objects.filter(id=selected_company).first()
            if selected_company
            else None
        )

    instance = BiometricAttendance.objects.filter(company_id=company).first()
    if not instance:
        instance = BiometricAttendance.objects.create(
            is_installed=False, company_id=company
        )
    return {"is_installed": instance.is_installed}
