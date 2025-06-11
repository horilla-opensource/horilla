"""
Accessibility
"""

from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.models import User

from base.methods import check_manager
from employee.models import Employee
from recruitment.methods import (
    in_all_managers,
    is_recruitmentmanager,
    is_stagemanager,
    stage_manages,
)
from recruitment.models import Candidate, RecruitmentGeneralSetting, RejectedCandidate


def convert_emp(request, instance, user_perm):
    """
    Covert employee accessibility
    """
    mails = list(Candidate.objects.values_list("email", flat=True))
    existing_emails = list(
        User.objects.filter(username__in=mails).values_list("email", flat=True)
    )
    if not instance.email in existing_emails and not instance.start_onboard:
        return True


def add_skill_zone(request, instance, user_perm):
    """
    Add skill zone  accessibility
    """

    mails = list(Candidate.objects.values_list("email", flat=True))
    existing_emails = list(
        User.objects.filter(username__in=mails).values_list("email", flat=True)
    )
    if not instance.email in existing_emails and request.user.has_perm(
        "recruitment.add_skillzonecandidate"
    ):
        return True


def add_reject(request, instance, user_perm):
    """
    add reject accessibility
    """
    first = RejectedCandidate.objects.filter(candidate_id=instance).first()
    mails = list(Candidate.objects.values_list("email", flat=True))
    existing_emails = list(
        User.objects.filter(username__in=mails).values_list("email", flat=True)
    )
    if not instance.email in existing_emails:
        if request.user.has_perm(
            "recruitment.add_rejectedcandidate"
        ) or is_stagemanager(request):
            if not first:
                return True


def edit_reject(request, instance, user_perm):
    """
    Edit reject accessibility
    """
    first = RejectedCandidate.objects.filter(candidate_id=instance).first()
    mails = list(Candidate.objects.values_list("email", flat=True))
    existing_emails = list(
        User.objects.filter(username__in=mails).values_list("email", flat=True)
    )
    if not instance.email in existing_emails:
        if request.user.has_perm(
            "recruitment.add_rejectedcandidate"
        ) or is_stagemanager(request):
            if first:
                return True


def archive_status(request, instance, user_perm):
    """
    To acces archive in list candidates
    """
    if instance.is_active:
        return True


def unarchive_status(request, instance, user_perm):
    """
    To acces un-archive in list candidates
    """
    if not instance.is_active:
        return True


def onboarding_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessibility for onboarding tab in candidate individual view
    """
    candidate = Candidate.objects.get(pk=instance.pk)
    if (
        candidate.cand_onboarding_task.exists()
        and in_all_managers(request)
        or request.user.has_perm("onboarding.view_onboardingtask")
    ):
        return True
    return False


def rating_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    accessebility for rating tab in candidate individual view
    """
    candidate = Candidate.objects.get(pk=instance.pk)
    stage_manage = stage_manages(request.user.employee_get, candidate.recruitment_id)
    if (
        stage_manage
        or request.user.has_perm("recruitment.view_candidate")
        or request.user.has_perm("recruitment.view_candidate")
    ):
        return True
    return False


def if_manager_accessibility(request, instance, *args, **kwargs):
    """
    If manager accessibility
    """
    return (
        is_recruitmentmanager(request)
        or is_stagemanager(request)
        or request.user.has_perm("recruitment.view_candidate")
    )


def empl_scheduled_interview_accessibility(
    request, instance: object = None, user_perms: PermWrapper = [], *args, **kwargs
) -> bool:
    """
    sheduled interview tab accessibility for candidate individual view, employee individual view and employee profile
    """
    employee = Employee.objects.get(id=instance.pk)
    if (
        request.user.has_perm("recruitment.view_interviewschedule")
        or check_manager(request.user.employee_get, instance)
        or request.user == employee.employee_user_id
        or is_recruitmentmanager(request)
    ):
        return True
    return False


def view_candidate_self_tracking(request, instance, *args, **kwargs):
    if (
        request.user.has_perm("recruitment.view_candidate")
        or is_stagemanager(request)
        or is_recruitmentmanager(request)
    ):
        return True


def request_document(request, instance, *args, **kwargs):
    if (
        request.user.has_perm("recruitment.change_candidate")
        or request.user.has_perm("recruitment.add_candidatedocumentrequest")
        or is_stagemanager(request)
        or is_recruitmentmanager(request)
    ):
        return True


def check_candidate_self_tracking(request, instance, user_perm):
    """
    This method is used to get the candidate self tracking is enabled or not
    """

    candidate_self_tracking = False
    if RecruitmentGeneralSetting.objects.exists():
        candidate_self_tracking = (
            RecruitmentGeneralSetting.objects.first().candidate_self_tracking
        )
    return candidate_self_tracking
