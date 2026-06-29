"""
Central role / access helpers for the HRM access-control overhaul.

Single source of truth for "who can see/edit whom", reused by views, decorators
and templates. Access is driven by the reporting-manager chain:

  * HR / admin       -> Django superuser (sees and edits everyone).
  * Operations Mgr   -> member of the "Operations Manager" group.
  * Manager          -> anyone who is a reporting_manager of >= 1 employee;
                        has full view + edit on their whole subordinate chain
                        (direct AND indirect).
  * Everyone else     -> may see other people's limited public profile only.

CEO is an explicit HR-set flag (Employee.is_ceo) and is hidden from non-HR users.

All Employee imports are done lazily to avoid a base <-> employee import cycle.
"""

OPERATIONS_MANAGER_GROUP = "Operations Manager"


def get_employee(user):
    """Return the Employee linked to a user, or None."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "employee_get", None)


def is_hr(user):
    """HR / admin == Django superuser."""
    return bool(user and getattr(user, "is_authenticated", False) and user.is_superuser)


def is_operations_manager(user):
    """Member of the 'Operations Manager' group (HR aside)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=OPERATIONS_MANAGER_GROUP).exists()


def is_manager(employee):
    """True if this employee is the reporting manager of at least one employee."""
    if not employee:
        return False
    return employee.reporting_manager.exists()


def nested_subordinate_ids(employee):
    """
    Set of Employee ids in the reporting chain *below* `employee`
    (direct and indirect subordinates), excluding the employee itself.
    """
    from employee.models import Employee

    if not employee:
        return set()

    result = set()
    current = [employee.id]
    while current:
        subs = list(
            Employee.objects.filter(
                employee_work_info__reporting_manager_id__in=current
            )
            .exclude(id__in=result)
            .values_list("id", flat=True)
        )
        if not subs:
            break
        result.update(subs)
        current = subs
    return result


def manages(viewer_employee, target_employee):
    """True if target is anywhere in viewer's subordinate chain."""
    if not viewer_employee or not target_employee:
        return False
    return target_employee.id in nested_subordinate_ids(viewer_employee)


def full_access_ids(user):
    """
    Ids of employees the (non-HR) user may fully view/edit: their whole
    subordinate chain plus themselves. HR is handled separately (`is_hr`).
    """
    employee = get_employee(user)
    if not employee:
        return set()
    return nested_subordinate_ids(employee) | {employee.id}


def can_view_full_profile(user, target_employee):
    """Full profile access: HR, self, or a manager (chain) of the target."""
    if is_hr(user):
        return True
    viewer = get_employee(user)
    if viewer and target_employee and viewer.id == target_employee.id:
        return True
    return manages(viewer, target_employee)


def can_edit_employee(user, target_employee):
    """Edit access: HR or a manager (chain) of the target (not self-edit here)."""
    if is_hr(user):
        return True
    return manages(get_employee(user), target_employee)


def is_ceo(employee):
    return bool(employee and getattr(employee, "is_ceo", False))


def visible_employees_qs(user, queryset):
    """Hide CEO rows from non-HR viewers."""
    if is_hr(user):
        return queryset
    return queryset.filter(is_ceo=False)
