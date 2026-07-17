from django.contrib import admin

from hydra_housing.models import (
    HousingAssignment,
    HousingAssignmentEvent,
    HousingBed,
    HousingBuilding,
    HousingFacility,
    HousingFloor,
    HousingRoom,
)
from hydra_housing.selectors import (
    HOUSING_VIEW_PERMISSIONS,
    housing_assignment_events_for_user,
    housing_assignments_for_user,
    housing_beds_for_user,
    housing_buildings_for_user,
    housing_facilities_for_user,
    housing_floors_for_user,
    housing_rooms_for_user,
)


class ServiceManagedAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or (
            request.user.has_perms(HOUSING_VIEW_PERMISSIONS)
            and super().has_view_permission(request, obj)
        )

    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        selectors = {
            HousingFacility: housing_facilities_for_user,
            HousingBuilding: housing_buildings_for_user,
            HousingFloor: housing_floors_for_user,
            HousingRoom: housing_rooms_for_user,
            HousingBed: housing_beds_for_user,
            HousingAssignment: housing_assignments_for_user,
            HousingAssignmentEvent: housing_assignment_events_for_user,
        }
        return selectors[self.model](user=request.user)


@admin.register(HousingFacility)
class HousingFacilityAdmin(ServiceManagedAdmin):
    list_display = ("name", "location", "address", "is_active")
    list_filter = ("location", "is_active")
    search_fields = ("name", "address")


@admin.register(HousingBuilding)
class HousingBuildingAdmin(ServiceManagedAdmin):
    list_display = ("name", "facility", "is_active")
    list_filter = ("facility", "is_active")
    search_fields = ("name", "facility__name")


@admin.register(HousingFloor)
class HousingFloorAdmin(ServiceManagedAdmin):
    list_display = ("name", "building", "sort_order", "is_active")
    list_filter = ("building__facility", "building", "is_active")
    search_fields = ("name", "building__name", "building__facility__name")


@admin.register(HousingRoom)
class HousingRoomAdmin(ServiceManagedAdmin):
    list_display = ("name", "facility", "floor_unit", "is_active")
    list_filter = ("facility", "is_active")


@admin.register(HousingBed)
class HousingBedAdmin(ServiceManagedAdmin):
    list_display = ("label", "room", "is_active")
    list_filter = ("room__facility", "is_active")


@admin.register(HousingAssignment)
class HousingAssignmentAdmin(ServiceManagedAdmin):
    list_display = (
        "person",
        "bed",
        "valid_from",
        "valid_until",
        "reservation_expires_at",
        "is_active",
    )
    list_filter = ("bed__room__facility", "valid_from", "valid_until", "is_active")
    search_fields = ("person__hydra_id", "person__passport_name")


@admin.register(HousingAssignmentEvent)
class HousingAssignmentEventAdmin(ServiceManagedAdmin):
    list_display = (
        "assignment",
        "action",
        "effective_on",
        "actor",
        "occurred_at",
    )
    list_filter = ("action", "effective_on", "occurred_at")
    search_fields = (
        "assignment__person__hydra_id",
        "assignment__person__passport_name",
        "reason",
    )
