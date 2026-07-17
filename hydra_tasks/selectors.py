from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from base.models import Company
from hydra_coordination.selectors import company_ids_for_user
from hydra_people.selectors import company_ids_for_person, people_for_user
from hydra_tasks.models import HydraTask, HydraTaskEvent


User = get_user_model()

ASSIGNEE_PERMISSIONS = (
    ("hydra_tasks", "view_hydratask"),
    ("hydra_tasks", "transition_hydratask"),
    ("hydra_people", "view_person"),
)


def companies_for_task_person(*, user, person) -> QuerySet[Company]:
    allowed = company_ids_for_user(user=user)
    linked = company_ids_for_person(person=person)
    return Company._base_manager.filter(pk__in=allowed.intersection(linked)).order_by(
        "company"
    )


def tasks_for_user(
    *,
    user,
    query="",
    status="",
    priority="",
    ownership="",
    due="",
) -> QuerySet[HydraTask]:
    if not user.is_authenticated or not user.has_perm("hydra_tasks.view_hydratask"):
        return HydraTask._base_manager.none()
    queryset = HydraTask._base_manager.select_related(
        "company",
        "person",
        "assignee",
        "created_by",
    )
    if not user.is_superuser:
        queryset = queryset.filter(
            person__in=people_for_user(user=user),
            company_id__in=company_ids_for_user(user=user),
        )
        if not user.has_perm("hydra_tasks.view_all_hydratask"):
            queryset = queryset.filter(Q(assignee=user) | Q(created_by=user))

    query = query.strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(person__hydra_id__icontains=query)
            | Q(target_label__icontains=query)
        )
    if status in HydraTask.Status.values:
        queryset = queryset.filter(status=status)
    if priority in HydraTask.Priority.values:
        queryset = queryset.filter(priority=priority)
    if ownership == "assigned_to_me":
        queryset = queryset.filter(assignee=user)
    elif ownership == "created_by_me":
        queryset = queryset.filter(created_by=user)

    now = timezone.now()
    if due == "overdue":
        queryset = queryset.filter(
            status__in=(HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS),
            due_at__lt=now,
        )
    elif due == "next_7_days":
        queryset = queryset.filter(
            status__in=(HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS),
            due_at__gte=now,
            due_at__lte=now + timedelta(days=7),
        )
    elif due == "no_due_date":
        queryset = queryset.filter(
            status__in=(HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS),
            due_at__isnull=True,
        )
    return queryset.distinct()


def task_for_user(*, user, task_uuid) -> HydraTask:
    return get_object_or_404(tasks_for_user(user=user), uuid=task_uuid)


def task_events_for_user(*, user, task) -> QuerySet[HydraTaskEvent]:
    if not user.is_authenticated or not user.has_perm(
        "hydra_tasks.view_hydrataskevent"
    ):
        return HydraTaskEvent.objects.none()
    if not tasks_for_user(user=user).filter(pk=task.pk).exists():
        return HydraTaskEvent.objects.none()
    return HydraTaskEvent.objects.filter(task=task).select_related(
        "actor",
        "from_assignee",
        "to_assignee",
    )


def _users_with_permission(queryset, app_label, codename):
    return queryset.filter(
        Q(is_superuser=True)
        | Q(
            user_permissions__content_type__app_label=app_label,
            user_permissions__codename=codename,
        )
        | Q(
            groups__permissions__content_type__app_label=app_label,
            groups__permissions__codename=codename,
        )
    )


def eligible_task_assignees(*, person, company) -> QuerySet[User]:
    """Return active principals with task permissions and intersecting scope."""

    queryset = User.objects.filter(is_active=True)
    for app_label, codename in ASSIGNEE_PERMISSIONS:
        queryset = _users_with_permission(queryset, app_label, codename)

    today = timezone.localdate()
    active_grant = (
        Q(hydra_scope_grants__is_active=True)
        & Q(hydra_scope_grants__valid_from__lte=today)
        & (
            Q(hydra_scope_grants__valid_until__isnull=True)
            | Q(hydra_scope_grants__valid_until__gte=today)
        )
    )
    company_scope = active_grant & (
        Q(hydra_scope_grants__company=company)
        | Q(hydra_scope_grants__department__company_id=company)
        | Q(hydra_scope_grants__location__company=company)
        | Q(hydra_scope_grants__section__location__company=company)
        | Q(hydra_scope_grants__team__section__location__company=company)
    )

    assignments = person.coordination_assignments.filter(
        is_active=True,
        valid_from__lte=today,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    company_ids = set(
        assignments.values_list("team__section__location__company_id", flat=True)
    )
    department_ids = set(assignments.values_list("department_id", flat=True))
    location_ids = set(
        assignments.values_list("team__section__location_id", flat=True)
    )
    section_ids = set(assignments.values_list("team__section_id", flat=True))
    team_ids = set(assignments.values_list("team_id", flat=True))
    for identifiers in (
        company_ids,
        department_ids,
        location_ids,
        section_ids,
        team_ids,
    ):
        identifiers.discard(None)

    person_scope = active_grant & (
        Q(hydra_scope_grants__company_id__in=company_ids)
        | Q(hydra_scope_grants__department_id__in=department_ids)
        | Q(hydra_scope_grants__location_id__in=location_ids)
        | Q(hydra_scope_grants__section_id__in=section_ids)
        | Q(hydra_scope_grants__team_id__in=team_ids)
    )
    if assignments.exists():
        queryset = queryset.filter(Q(is_superuser=True) | person_scope)
    else:
        queryset = queryset.filter(
            Q(is_superuser=True) | Q(pk=person.created_by_id)
        )
    queryset = queryset.filter(Q(is_superuser=True) | company_scope)
    return queryset.distinct().order_by("username")


def user_is_eligible_task_assignee(*, user, person, company) -> bool:
    if not user.is_active or not user.has_perms(
        tuple(f"{app}.{code}" for app, code in ASSIGNEE_PERMISSIONS)
    ):
        return False
    if user.is_superuser:
        return True
    return (
        company.pk in company_ids_for_user(user=user)
        and people_for_user(user=user).filter(pk=person.pk).exists()
    )
