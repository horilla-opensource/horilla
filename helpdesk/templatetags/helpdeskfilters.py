from django import template
from django.template.defaultfilters import register

from helpdesk.models import ClaimRequest, DepartmentManager

register = template.Library()


@register.filter(name="claim_request_exists")
def claim_request_exists(ticket, employee):
    return ClaimRequest.objects.filter(ticket_id=ticket, employee_id=employee).exists()


@register.filter(name="is_department_manager")
def is_department_manager(employee, ticket):
    """
    Check requested user is a department manger or not
    """
    if ticket.assigning_type == "job_position":
        job_position = ticket.get_raised_on_object()
        department = job_position.department_id
    elif ticket.assigning_type == "department":
        department = ticket.get_raised_on_object()
    else:
        return False
    return DepartmentManager.objects.filter(
        manager=employee, department=department
    ).exists()


@register.filter(name="has_reviewed_password_reset")
def has_reviewed_password_reset(ticket):
    """
    Returns True if the ticket has an associated PasswordResetRequest
    whose iso_status is not 'PENDING' (i.e., it has been approved or rejected).
    """
    pr_request = getattr(ticket, "password_reset_request", None)
    if pr_request and pr_request.iso_status != "PENDING":
        return True
    return False

