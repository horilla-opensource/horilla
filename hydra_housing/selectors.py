from django.db import models
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.models import Location, PersonAssignment
from hydra_coordination.selectors import active_grants_for_user
from hydra_housing.models import (
    HousingAssignment,
    HousingAssignmentEvent,
    HousingBed,
    HousingBuilding,
    HousingFacility,
    HousingFloor,
    HousingRoom,
)
from hydra_people.models import Person
from hydra_people.selectors import people_for_user


HOUSING_VIEW_PERMISSIONS = (
    "hydra_housing.view_housingfacility",
    "hydra_housing.view_housingroom",
    "hydra_housing.view_housingbed",
    "hydra_housing.view_housingassignment",
    "hydra_coordination.view_location",
    "hydra_people.view_person",
)


def housing_locations_for_user(*, user) -> QuerySet[Location]:
    if not user.is_authenticated or not user.has_perms(HOUSING_VIEW_PERMISSIONS):
        return Location._base_manager.none()
    queryset = Location._base_manager.filter(is_active=True).select_related("company")
    if user.is_superuser:
        return queryset.order_by("company__company", "name")
    grants = active_grants_for_user(user=user)
    company_ids = grants.filter(company__isnull=False).values_list("company_id", flat=True)
    location_ids = grants.filter(location__isnull=False).values_list("location_id", flat=True)
    return queryset.filter(
        Q(company_id__in=company_ids) | Q(pk__in=location_ids)
    ).distinct().order_by("company__company", "name")


def housing_facilities_for_user(*, user, location=None) -> QuerySet[HousingFacility]:
    if not user.is_authenticated or not user.has_perms(HOUSING_VIEW_PERMISSIONS):
        return HousingFacility._base_manager.none()
    queryset = HousingFacility._base_manager.select_related("location__company")
    if not user.is_superuser:
        queryset = queryset.filter(location__in=housing_locations_for_user(user=user))
    if location is not None:
        queryset = queryset.filter(location=location)
    return queryset.distinct()


def housing_facility_for_user(*, user, facility_uuid) -> HousingFacility:
    return get_object_or_404(housing_facilities_for_user(user=user), uuid=facility_uuid)


def housing_buildings_for_user(*, user) -> QuerySet[HousingBuilding]:
    return HousingBuilding._base_manager.filter(
        facility__in=housing_facilities_for_user(user=user)
    ).select_related("facility__location__company")


def housing_building_for_user(*, user, building_uuid) -> HousingBuilding:
    return get_object_or_404(
        housing_buildings_for_user(user=user),
        uuid=building_uuid,
    )


def housing_floors_for_user(*, user) -> QuerySet[HousingFloor]:
    return HousingFloor._base_manager.filter(
        building__facility__in=housing_facilities_for_user(user=user)
    ).select_related("building__facility__location__company")


def housing_floor_for_user(*, user, floor_uuid) -> HousingFloor:
    return get_object_or_404(housing_floors_for_user(user=user), uuid=floor_uuid)


def housing_rooms_for_user(*, user) -> QuerySet[HousingRoom]:
    return HousingRoom._base_manager.filter(
        facility__in=housing_facilities_for_user(user=user)
    ).select_related(
        "facility__location__company",
        "floor_unit__building__facility",
    )


def housing_room_for_user(*, user, room_uuid) -> HousingRoom:
    return get_object_or_404(housing_rooms_for_user(user=user), uuid=room_uuid)


def housing_beds_for_user(*, user) -> QuerySet[HousingBed]:
    return HousingBed._base_manager.filter(
        room__facility__in=housing_facilities_for_user(user=user)
    ).select_related(
        "room__facility__location__company",
        "room__floor_unit__building",
    )


def housing_bed_for_user(*, user, bed_uuid) -> HousingBed:
    return get_object_or_404(housing_beds_for_user(user=user), uuid=bed_uuid)


def housing_assignments_for_user(*, user, day=None, current_only=False):
    if not user.is_authenticated or not user.has_perms(HOUSING_VIEW_PERMISSIONS):
        return HousingAssignment._base_manager.none()
    queryset = HousingAssignment._base_manager.filter(
        bed__room__facility__in=housing_facilities_for_user(user=user)
    ).select_related(
        "person",
        "bed__room__facility__location__company",
        "bed__room__floor_unit__building",
    )
    if current_only:
        day = day or timezone.localdate()
        queryset = queryset.filter(
            is_active=True,
            reservation_expires_at__isnull=True,
            valid_from__lte=day,
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=day)
        )
    return queryset.distinct()


def housing_assignment_for_user(*, user, assignment_uuid) -> HousingAssignment:
    return get_object_or_404(
        housing_assignments_for_user(user=user),
        uuid=assignment_uuid,
    )


def housing_assignment_events_for_user(*, user):
    if not user.is_authenticated or not user.has_perm(
        "hydra_housing.view_housingassignmentevent"
    ):
        return HousingAssignmentEvent.objects.none()
    return HousingAssignmentEvent.objects.filter(
        assignment__in=housing_assignments_for_user(user=user)
    ).select_related(
        "assignment__person",
        "assignment__bed__room__facility__location",
        "related_assignment__bed__room__facility__location",
        "actor",
    )


def eligible_people_for_housing_period(
    *,
    user,
    location,
    valid_from,
    allow_planned_arrival=False,
) -> QuerySet[Person]:
    if not housing_locations_for_user(user=user).filter(pk=location.pk).exists():
        return Person._base_manager.none()
    today = timezone.localdate()
    eligibility_day = valid_from if valid_from > today else today
    current_at_location = PersonAssignment._base_manager.filter(
        person_id=models.OuterRef("pk"),
        is_active=True,
        valid_from__lte=eligibility_day,
        team__section__location=location,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=eligibility_day))
    arrived_at_location = ArrivalPlan._base_manager.filter(
        person_id=models.OuterRef("pk"),
        destination_location=location,
        status=ArrivalPlan.Status.CONFIRMED,
        actual_arrived_at__date__lte=eligibility_day,
    )
    visible = people_for_user(user=user).annotate(
        housing_current_location=models.Exists(current_at_location),
        housing_arrived_location=models.Exists(arrived_at_location),
    )
    eligibility = Q(housing_current_location=True) | Q(housing_arrived_location=True)
    if allow_planned_arrival and valid_from >= today:
        planned_at_location = ArrivalPlan._base_manager.filter(
            person_id=models.OuterRef("pk"),
            destination_location=location,
            status=ArrivalPlan.Status.PLANNED,
            planned_at__date__lte=valid_from,
        )
        visible = visible.annotate(
            housing_planned_location=models.Exists(planned_at_location)
        )
        eligibility |= Q(housing_planned_location=True)
    return visible.filter(eligibility).distinct()


def eligible_people_for_location(*, user, location) -> QuerySet[Person]:
    return eligible_people_for_housing_period(
        user=user,
        location=location,
        valid_from=timezone.localdate(),
        allow_planned_arrival=False,
    )
