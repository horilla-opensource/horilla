"""
methods.py

This page is used to write reusable methods.

"""


def is_stagemanager(request):
    """
    This method is used to check stage manager, if the employee is also
    recruitment manager it returns true
    """
    try:
        employee = request.user.employee_get
        return employee.recruitment_set.exists() or employee.stage_set.exists()
    except Exception:
        return False


def is_recruitmentmanager(request):
    """
    This method is used to check the employee is recruitment manager or not
    """
    try:
        employee = request.user.employee_get
        return employee.recruitment_set.exists()
    except Exception:
        return False


def stage_manages(request, stage):
    """
    This method is used to check the employee manager to this stage."""
    try:
        employee = request.user.employee_get

        return (
            stage.stage_manager.filter(id=employee.id).exists()
            or stage.recruitment_id.recruitment_managers.filter(id=employee.id).exists()
        )
    except Exception:
        return False


def recruitment_manages(request, recruitment):
    """
    This method is used to check the employee is manager to the current recruitment
    """
    try:
        employee = request.user.employee_get
        return recruitment.recruitment_managers.filter(id=employee.id).exists()
    except Exception:
        return False
