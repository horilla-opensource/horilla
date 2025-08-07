"""
recruitment/accessibility.py

"""

from recruitment.templatetags.recruitmentfilters import recruitment_manages


def add_candidate_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Candidate add accessibility
    """
    return (
        request.user.has_perm("recruitment.add_candidate")
        or request.user.employee_get in instance.stage_managers.all()
        or request.user.employee_get
        in instance.recruitment_id.recruitment_managers.all()
    )


def edit_stage_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Edit stage accessibility
    """
    return (
        request.user.has_perm("recruitment.change_stage")
        or recruitment_manages(request.user, instance.recruitment_id)
        or request.user.employee_get in instance.stage_managers.all()
    )


def delete_stage_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Delete stage accessibility
    """
    return request.user.has_perm("recruitment.delete_stage")
