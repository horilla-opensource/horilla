"""
Custom template filters for the PMS application.

This module includes custom template filters used in the PMS (Performance Management System) application.
The filters help with various operations like replacing underscores in strings, counting key results for objectives,
and checking if a user is a manager or owner of an objective or feedback.

Filters:
    - replace: Replaces underscores in a string with spaces.
    - kr_count: Counts and returns the key results for a given objective.
    - is_manager_or_owner: Checks if the user is a manager or owner of the given objective.
    - is_manager: Checks if the user is a manager of the given objective.
    - is_feedback_manager_or_owner: Checks if the user is a manager or owner of the given feedback.
    - is_feedback_answer: Checks if the user is a manager, owner, or subordinate of the given feedback.
"""

from django.template.defaultfilters import register

from base.methods import filtersubordinatesemployeemodel
from employee.models import Employee, EmployeeWorkInformation
from pms.models import AnonymousFeedback, EmployeeObjective, Feedback, Objective


@register.filter(name="replace")
def replace(string):
    """
    This method is used to return str of the fk fields
    """

    return string.replace("_", " ")


@register.filter(name="kr_count")
def kr_count(objective_id):
    """
    Retrieves a list of all key results associated with a given objective.

    This filter function takes an objective ID as input, retrieves the corresponding
    Objective instance, and then collects all key results from the employee objectives
    associated with that objective.

    Args:
        objective_id (int): The ID of the objective for which to retrieve key results.

    Returns:
        list: A list of all key results (KR) associated with the given objective.
    """
    objective = Objective.objects.get(id=objective_id)
    empl_objectives = objective.employee_objective.all()
    kr_list = []
    for obj in empl_objectives:
        for kr in obj.employee_key_result.all():
            kr_list.append(kr)
    return kr_list


@register.filter(name="is_manager_or_owner")
def is_manager_or_owner(objective, user):
    """
    This method will return true, if the user is manger of the objective, or owner
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    if (
        EmployeeObjective.objects.filter(
            id=objective.id, objective_id__managers=employee
        ).exists()
        or EmployeeObjective.objects.filter(
            id=objective.id, employee_id=employee
        ).exists()
    ):
        return True
    return False


@register.filter(name="is_manager")
def is_manager(objective, user):
    """
    This method will return true, if the user is manger of the objective, or owner
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    if EmployeeObjective.objects.filter(
        id=objective.id, objective_id__managers=employee
    ).exists():
        return True
    return False


@register.filter(name="is_feedback_manager_or_owner")
def is_feedback_manager_or_owner(feedback, user):
    """
    This method will return true, if the user is manger or owner of the feedback,
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    if Feedback.objects.filter(id=feedback.id, manager_id=employee).exists():
        return True
    elif Feedback.objects.filter(id=feedback.id, employee_id=employee).exists():
        return True
    elif EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee, employee_id=feedback.employee_id
    ).exists():
        return True
    return False


@register.filter(name="is_feedback_answer")
def is_feedback_answer(feedback, user):
    """
    This method will return true, if the user is manger or owner of the feedback,
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    if Feedback.objects.filter(id=feedback.id, manager_id=employee).exists():
        return True
    elif Feedback.objects.filter(id=feedback.id, employee_id=employee).exists():
        return True
    elif Feedback.objects.filter(id=feedback.id, subordinate_id=employee).exists():
        return True
    return False


@register.filter(name="is_anonymous_feedback_owner")
def is_anonymous_feedback_owner(user, feedback):
    """
    This method will return true, if the user is owner of the feedback
    """
    if str(user.id) == feedback.anonymous_feedback_id:
        return True
    return False


@register.filter(name="assignees_count")
def assignees_count(objective, request):
    """
    Args:
        objective: The objective for which to retrieve assignees.
        user: The user requesting the assignees.
    Returns:
        int: The count of assignees for the given objective.
    """

    if (
        request.user.has_perm("pms.view_objective")
        or objective.managers.filter(id=request.user.employee_get.id).exists()
    ):
        return objective.employee_objective.count()
    sub_employees = filtersubordinatesemployeemodel(
        request,
        queryset=Employee.objects.filter(is_active=True),
    )
    if sub_employees.exists():
        subordinate_objectives = objective.employee_objective.filter(
            employee_id__in=sub_employees
        )
    return subordinate_objectives.count()
