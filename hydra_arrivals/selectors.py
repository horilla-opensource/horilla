from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.models import Location
from hydra_coordination.selectors import active_grants_for_user


User = get_user_model()

ARRIVAL_VIEW_PERMISSIONS = (
    "hydra_arrivals.view_arrivalplan",
    "hydra_coordination.view_location",
    "hydra_people.view_person",
    "recruitment.view_candidate",
)


def arrival_locations_for_user(*, user) -> QuerySet[Location]:
    if not user.is_authenticated or not user.has_perms(ARRIVAL_VIEW_PERMISSIONS):
        return Location.objects.none()
    queryset = Location.objects.filter(is_active=True).select_related("company")
    if user.is_superuser:
        return queryset
    grants = active_grants_for_user(user=user)
    company_ids = grants.filter(company__isnull=False).values_list(
        "company_id", flat=True
    )
    location_ids = grants.filter(location__isnull=False).values_list(
        "location_id", flat=True
    )
    return queryset.filter(
        Q(company_id__in=company_ids) | Q(pk__in=location_ids)
    ).distinct()


def arrival_plans_for_user(
    *, user, query="", status="", day=None
) -> QuerySet[ArrivalPlan]:
    if not user.is_authenticated or not user.has_perms(ARRIVAL_VIEW_PERMISSIONS):
        return ArrivalPlan.objects.none()
    queryset = ArrivalPlan.objects.select_related(
        "person",
        "candidate__recruitment_id__company_id",
        "destination_location__company",
        "coordinator",
    )
    if not user.is_superuser:
        queryset = queryset.filter(
            destination_location__in=arrival_locations_for_user(user=user)
        )
    query = query.strip()
    if query:
        queryset = queryset.filter(
            Q(person__hydra_id__icontains=query)
            | Q(person__passport_name__icontains=query)
            | Q(candidate__email__icontains=query)
            | Q(transport_reference__icontains=query)
        )
    if status in ArrivalPlan.Status.values:
        queryset = queryset.filter(status=status)
    if day:
        queryset = queryset.filter(planned_at__date=day)
    return queryset.distinct()


def arrival_plan_for_user(*, user, plan_uuid) -> ArrivalPlan:
    return get_object_or_404(
        arrival_plans_for_user(user=user),
        uuid=plan_uuid,
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


def coordinators_for_locations(*, locations) -> QuerySet[User]:
    location_ids = list(locations.values_list("pk", flat=True))
    company_ids = list(locations.values_list("company_id", flat=True).distinct())
    if not location_ids:
        return User.objects.none()

    queryset = User.objects.filter(is_active=True)
    for app_label, codename in (
        ("hydra_arrivals", "view_arrivalplan"),
        ("hydra_arrivals", "transition_arrivalplan"),
        ("hydra_coordination", "view_location"),
        ("hydra_people", "view_person"),
        ("recruitment", "view_candidate"),
    ):
        queryset = _users_with_permission(queryset, app_label, codename)

    today = timezone.localdate()
    current_scope = (
        Q(hydra_scope_grants__is_active=True)
        & Q(hydra_scope_grants__valid_from__lte=today)
        & (
            Q(hydra_scope_grants__valid_until__isnull=True)
            | Q(hydra_scope_grants__valid_until__gte=today)
        )
        & (
            Q(hydra_scope_grants__location_id__in=location_ids)
            | Q(hydra_scope_grants__company_id__in=company_ids)
        )
    )
    return (
        queryset.filter(Q(is_superuser=True) | current_scope)
        .distinct()
        .order_by("username")
    )
