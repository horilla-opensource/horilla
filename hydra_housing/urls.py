from django.urls import path

from hydra_housing import views


urlpatterns = [
    path("", views.housing_dashboard, name="hydra-housing-dashboard"),
    path("facilities/create/", views.housing_facility_create, name="hydra-housing-facility-create"),
    path("facilities/<uuid:facility_uuid>/", views.housing_facility_detail, name="hydra-housing-facility-detail"),
    path("facilities/<uuid:facility_uuid>/buildings/create/", views.housing_building_create, name="hydra-housing-building-create"),
    path("facilities/<uuid:facility_uuid>/rooms/create/", views.housing_room_create, name="hydra-housing-room-create"),
    path("buildings/<uuid:building_uuid>/floors/create/", views.housing_floor_create, name="hydra-housing-floor-create"),
    path("rooms/<uuid:room_uuid>/beds/create/", views.housing_bed_create, name="hydra-housing-bed-create"),
    path("people/<uuid:person_uuid>/assign/", views.housing_assign, name="hydra-housing-assign"),
    path("assignments/<uuid:assignment_uuid>/end/", views.housing_assignment_end, name="hydra-housing-assignment-end"),
    path("assignments/<uuid:assignment_uuid>/move/", views.housing_assignment_move, name="hydra-housing-assignment-move"),
    path("reservations/<uuid:assignment_uuid>/cancel/", views.housing_reservation_cancel, name="hydra-housing-reservation-cancel"),
    path("reservations/<uuid:assignment_uuid>/renew/", views.housing_reservation_renew, name="hydra-housing-reservation-renew"),
    path("reservations/<uuid:assignment_uuid>/confirm/", views.housing_reservation_confirm, name="hydra-housing-reservation-confirm"),
]
