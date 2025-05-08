from helpdesk.models import DepartmentManager


def is_department_manager(request, ticket):
    """
    Method used to find the user is a department manger of given ticket
    """
    user_emp = request.user.employee_get
    if ticket.assigning_type == "job_position":
        job_position = ticket.get_raised_on_object()
        department = job_position.department_id
    elif ticket.assigning_type == "department":
        department = ticket.get_raised_on_object()
    else:
        return False
    return DepartmentManager.objects.filter(
        manager=user_emp, department=department
    ).exists()
