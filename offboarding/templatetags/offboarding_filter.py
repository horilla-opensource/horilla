"""
offboarding_filter.py

This page is used to write custom template filters.
"""

from django.template.defaultfilters import register
from django import template

from offboarding.models import (
    EmployeeTask,
    Offboarding,
    OffboardingStage,
    OffboardingTask,
)


register = template.Library()


@register.filter(name="stages")
def stages(stages_dict, stage):
    """
    This method will return stage drop accordingly to the offboarding
    """
    form = stages_dict[str(stage.offboarding_id.id)]
    attrs = form.fields["stage_id"].widget.attrs
    attrs["id"] = "stage" + str(stage.id) + str(stage.offboarding_id.id)
    attrs["data-initial-stage"] = stage.id
    form.fields["stage_id"].widget.attrs.update(attrs)
    return form


@register.filter(name="have_task")
def have_task(task, employee):
    """
    used to check the task is for the employee
    """
    return EmployeeTask.objects.filter(employee_id=employee, task_id=task).exists()


@register.filter(name="get_assigned_task")
def get_assigned_tak(employee, task):
    """
    This method is used to filterout the assigned task
    """
    # retun like list to access it in varialbe when first iteration of the loop
    return [
        EmployeeTask.objects.filter(employee_id=employee, task_id=task).first(),
    ]


@register.filter(name="any_manager")
def any_manager(employee):
    """
    This method is used to check the employee is in managers
    employee: Employee model instance
    """
    return (
        Offboarding.objects.filter(managers=employee).exists()
        | OffboardingStage.objects.filter(managers=employee).exists()
        | OffboardingTask.objects.filter(managers=employee).exists()
    )


@register.filter(name="is_offboarding_manager")
def is_offboarding_manager(employee):
    """
    This method is used to check the employee is manager of any offboarding
    """
    return Offboarding.objects.filter(managers=employee).exists()
