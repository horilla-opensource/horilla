"""
onboarding/cbv/accessibility.py
"""

from onboarding.templatetags.onboardingfilters import stage_manages
from recruitment.methods import recruitment_manages


def edit_stage_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Edit accessibility
    """
    return request.user.has_perm("onboarding.change_onboardingstage") or stage_manages(
        request.user, instance
    )


def delete_stage_accessibility(
    request, instance=None, user_perms=[], *args, **kwargs
) -> bool:
    """
    Delete accessibility
    """
    return request.user.has_perm(
        "onboarding.delete_onboardingstage"
    ) or recruitment_manages(request.user, instance.recruitment_id)
