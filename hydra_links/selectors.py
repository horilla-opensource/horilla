from django.db.models import Q
from django.shortcuts import get_object_or_404

from hydra_coordination.models import Location
from hydra_coordination.selectors import active_grants_for_user
from hydra_links.models import PublicHydraLink


def public_link_location_ids_for_user(*, user):
    if not user.is_authenticated:
        return Location._base_manager.none().values_list("pk", flat=True)
    if user.is_superuser:
        return Location._base_manager.values_list("pk", flat=True)
    grants = active_grants_for_user(user=user)
    company_ids = grants.filter(company__isnull=False).values_list(
        "company_id", flat=True
    )
    department_ids = grants.filter(department__isnull=False).values_list(
        "department_id", flat=True
    )
    location_ids = grants.filter(location__isnull=False).values_list(
        "location_id", flat=True
    )
    section_ids = grants.filter(section__isnull=False).values_list(
        "section_id", flat=True
    )
    team_ids = grants.filter(team__isnull=False).values_list("team_id", flat=True)
    return (
        Location._base_manager.filter(
            Q(company_id__in=company_ids)
            | Q(pk__in=location_ids)
            | Q(sections__department_id__in=department_ids)
            | Q(sections__pk__in=section_ids)
            | Q(sections__teams__pk__in=team_ids)
        )
        .distinct()
        .values_list("pk", flat=True)
    )

def public_links_for_user(*, user, include_inactive=False):
    if not user.is_authenticated or not user.has_perm(
        "hydra_links.view_publichydralink"
    ):
        return PublicHydraLink.objects.none()
    queryset = PublicHydraLink.objects.select_related("location__company")
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    if user.is_superuser:
        return queryset
    return queryset.filter(
        Q(location__isnull=True)
        | Q(location_id__in=public_link_location_ids_for_user(user=user))
    )


def public_links_for_locations(*, user, location_ids, include_global=False):
    location_ids = set(location_ids)
    queryset = public_links_for_user(user=user)
    scope_q = Q(location_id__in=location_ids)
    if include_global:
        scope_q |= Q(location__isnull=True)
    return queryset.filter(scope_q)


def public_links_for_location(*, user, location, include_global=False):
    return public_links_for_locations(
        user=user,
        location_ids=(location.pk,),
        include_global=include_global,
    )


def manageable_public_links_for_user(*, user, permission="change_publichydralink"):
    if not user.is_authenticated or not user.has_perm(
        f"hydra_links.{permission}"
    ):
        return PublicHydraLink.objects.none()
    queryset = PublicHydraLink.objects.select_related("location__company")
    if user.is_superuser:
        return queryset
    scope_q = Q(location_id__in=public_link_location_ids_for_user(user=user))
    if user.has_perm("hydra_links.manage_global_publichydralink"):
        scope_q |= Q(location__isnull=True)
    return queryset.filter(scope_q)


def public_link_for_user(*, user, link_uuid, permission="change_publichydralink"):
    return get_object_or_404(
        manageable_public_links_for_user(user=user, permission=permission),
        uuid=link_uuid,
    )
