from django.template.defaultfilters import register

from employee.models import Employee
from pms.models import EmployeeObjective, Feedback, Objective


@register.filter(name="replace")
def replace(string):
    """
    This method is used to return str of the fk fields
    """

    return string.replace("_", " ")


@register.filter(name="kr_count")
def kr_count(objective_id):
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
