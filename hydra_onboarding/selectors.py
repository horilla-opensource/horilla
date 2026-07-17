from django.db.models import Q
from django.shortcuts import get_object_or_404

from base.models import Company
from hydra_coordination.selectors import company_ids_for_user
from hydra_onboarding.models import (
    Course,
    CourseAssignment,
    CourseAssignmentEvent,
    CourseAssignmentRule,
    CourseVersion,
)
from hydra_people.selectors import people_for_user


ONBOARDING_VIEW_PERMISSIONS = (
    "hydra_onboarding.view_course",
    "hydra_onboarding.view_courseversion",
)


def onboarding_companies_for_user(*, user):
    if not user.is_authenticated:
        return Company._base_manager.none()
    return Company._base_manager.filter(pk__in=company_ids_for_user(user=user)).order_by(
        "company"
    )


def courses_for_user(*, user):
    if not user.is_authenticated or not user.has_perms(ONBOARDING_VIEW_PERMISSIONS):
        return Course.objects.none()
    queryset = Course.objects.select_related("company", "created_by", "modified_by")
    if user.is_superuser:
        return queryset
    return queryset.filter(company_id__in=company_ids_for_user(user=user))


def course_for_user(*, user, course_uuid):
    return get_object_or_404(courses_for_user(user=user), uuid=course_uuid)


def course_versions_for_user(*, user):
    if not user.is_authenticated or not user.has_perms(ONBOARDING_VIEW_PERMISSIONS):
        return CourseVersion.objects.none()
    return CourseVersion._base_manager.filter(
        course__in=courses_for_user(user=user)
    ).select_related("course__company", "published_by", "created_by")


def course_version_for_user(*, user, version_uuid):
    return get_object_or_404(
        course_versions_for_user(user=user),
        uuid=version_uuid,
    )


def rules_for_user(*, user):
    if not user.is_authenticated or not user.has_perm(
        "hydra_onboarding.view_courseassignmentrule"
    ):
        return CourseAssignmentRule.objects.none()
    return CourseAssignmentRule.objects.filter(
        course__in=courses_for_user(user=user)
    ).select_related(
        "company",
        "course",
        "location",
        "department",
        "team__section__location",
        "employee_type",
    )


def assignments_for_user(*, user):
    if not user.is_authenticated or not user.has_perm(
        "hydra_onboarding.view_courseassignment"
    ):
        return CourseAssignment.objects.none()
    visible_people = people_for_user(user=user)
    queryset = CourseAssignment._base_manager.filter(
        person__in=visible_people,
        company_id__in=company_ids_for_user(user=user),
    ).select_related(
        "person",
        "company",
        "course",
        "course_version",
        "rule",
        "assigned_by",
    )
    return queryset.distinct()


def assignment_for_user(*, user, assignment_uuid):
    return get_object_or_404(
        assignments_for_user(user=user),
        uuid=assignment_uuid,
    )


def assignment_events_for_user(*, user):
    if not user.is_authenticated or not user.has_perm(
        "hydra_onboarding.view_courseassignmentevent"
    ):
        return CourseAssignmentEvent.objects.none()
    return CourseAssignmentEvent.objects.filter(
        assignment__in=assignments_for_user(user=user)
    ).select_related(
        "actor",
        "quiz_attempt",
        "confirmation",
        "assignment__course",
        "assignment__person",
    )


def rule_scope_q(*, company_ids, location_ids, department_ids, team_ids):
    """Explicit hierarchy predicate used by admin and list filtering."""

    return (
        Q(company_id__in=company_ids)
        | Q(location_id__in=location_ids)
        | Q(department_id__in=department_ids)
        | Q(team_id__in=team_ids)
    )
