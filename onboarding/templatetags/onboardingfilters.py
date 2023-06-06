"""
onboardingfilters.py

This page is used to write custom template filters.
"""

from django.template.defaultfilters import register
from django import template


# from django.forms.boundfield

register = template.Library()


@register.filter(name="is_taskmanager")
def is_taskmanager(user):
    """
    Method to check the user is task manager

    Args:
        user (obj): User instance

    Returns:
        bool: True if task manager
    """
    try:
        employee = user.employee_get
        return (
            employee.onboardingtask_set.all().exists()
            or employee.onboardingstage_set.all().exists()
            or employee.recruitment_set.exists()
        )
    except Exception:
        return False


@register.filter(name="task_manages")
def task_manages(user, recruitment):
    """
    check weather the user manages any task, stage, and recruitment

    Args:
        user (obj): django User instance
        recruitment (obj): Recruitment instance

    Returns:
        bool: returns true if user manges any them
    """
    try:
        employee = user.employee_get
        return (
            recruitment.onboarding_task.filter(employee_id=employee).exists()
            or recruitment.onboardingstage_set.filter(employee_id=employee).exists()
            or recruitment.recruitment_managers.filter(id=user.employee_get.id).exists()
        )
    except Exception:
        return False


@register.filter(name="stage_manages")
def stage_manages(user, stage):
    """
    check weather the user manages stage or not

    Args:
        user (obj): django User model instance
        stage (obj): OnboardingStage model instance

    Returns:
        bool: true if the user in any manager in the stage.
    """
    try:
        employee = user.employee_get
        return (
            stage.employee_id.filter(id=employee.id).exists()
            or stage.recruitment_id.filter(recruitment_managers=employee).exists()
        )
    except Exception:
        return False


@register.filter(name="task_manager")
def task_manager(user, task):
    """
    This method check weather the user manages onboarding task

    Args:
        user (obj): django User model instance
        task (obj): onboarding task instance

    Returns:
        bool: returns true if the user in any manager in the task
    """
    try:
        employee = user.employee_get
        return (
            task.onboarding_task_id.employee_id.filter(id=employee.id).exists()
            or task.candidate_id.onboarding_stage.onboarding_stage_id.employee_id.filter(
                id=employee.id
            ).exists()
            or task.onboarding_task_id.recruitment_id.first()
            .recruitment_managers.filter(id=user.employee_get.id)
            .exists()
        )
    except Exception:
        return False
