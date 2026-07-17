from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_housing.forms import (
    HousingAssignmentForm,
    HousingBedForm,
    HousingBuildingForm,
    HousingEndForm,
    HousingFacilityForm,
    HousingFilterForm,
    HousingFloorForm,
    HousingRoomForm,
    HousingMoveForm,
    HousingReservationCancelForm,
    HousingReservationConfirmForm,
    HousingReservationRenewForm,
)
from hydra_housing.models import (
    HousingAssignment,
    HousingBed,
    HousingBuilding,
    HousingFacility,
    HousingFloor,
    HousingRoom,
)
from hydra_housing.selectors import (
    HOUSING_VIEW_PERMISSIONS,
    housing_assignment_for_user,
    housing_assignments_for_user,
    housing_building_for_user,
    housing_buildings_for_user,
    housing_facility_for_user,
    housing_facilities_for_user,
    housing_room_for_user,
)
from hydra_housing.services import (
    assign_housing,
    cancel_housing_reservation,
    confirm_housing_reservation,
    end_housing_assignment,
    move_housing_assignment,
    renew_housing_reservation,
    save_housing_bed,
    save_housing_building,
    save_housing_facility,
    save_housing_floor,
    save_housing_room,
)
from hydra_people.selectors import person_for_user


def _add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            for item in errors:
                form.add_error(field if field in form.fields else None, item)
    else:
        form.add_error(None, error)


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS, raise_exception=True)
def housing_dashboard(request):
    form = HousingFilterForm(request.GET or None, actor=request.user)
    query = ""
    location = None
    if form.is_valid():
        query = form.cleaned_data["q"].strip()
        location = form.cleaned_data["location"]

    facilities = housing_facilities_for_user(user=request.user, location=location).filter(
        is_active=True
    )
    if query:
        facilities = facilities.filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(buildings__name__icontains=query)
            | Q(rooms__name__icontains=query)
            | Q(rooms__floor_unit__name__icontains=query)
            | Q(rooms__floor_unit__building__name__icontains=query)
            | Q(rooms__beds__label__icontains=query)
        )
    facilities = facilities.prefetch_related(
        Prefetch("rooms", queryset=HousingRoom._base_manager.filter(is_active=True).prefetch_related(
            Prefetch("beds", queryset=HousingBed._base_manager.filter(is_active=True))
        ))
    ).distinct()
    assignments = housing_assignments_for_user(
        user=request.user,
        current_only=True,
    )
    if location:
        assignments = assignments.filter(bed__room__facility__location=location)
    if query:
        assignments = assignments.filter(
            Q(person__hydra_id__icontains=query)
            | Q(person__passport_name__icontains=query)
            | Q(bed__room__facility__name__icontains=query)
            | Q(bed__room__name__icontains=query)
            | Q(bed__label__icontains=query)
        )
    reservations = housing_assignments_for_user(user=request.user).filter(
        is_active=True,
        valid_from__gt=timezone.localdate(),
    )
    if location:
        reservations = reservations.filter(bed__room__facility__location=location)
    if query:
        reservations = reservations.filter(
            Q(person__hydra_id__icontains=query)
            | Q(person__passport_name__icontains=query)
            | Q(bed__room__facility__name__icontains=query)
            | Q(bed__room__name__icontains=query)
            | Q(bed__label__icontains=query)
        )
    occupied_count = assignments.count()
    reservation_count = reservations.count()
    return render(
        request,
        "hydra_housing/housing_dashboard.html",
        {
            "filter_form": form,
            "facilities": facilities,
            "current_assignments": assignments[:100],
            "reservations": reservations.order_by("valid_from", "pk")[:100],
            "facility_count": facilities.count(),
            "occupied_count": occupied_count,
            "reservation_count": reservation_count,
        },
    )


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS, raise_exception=True)
def housing_facility_detail(request, facility_uuid):
    facility = housing_facility_for_user(user=request.user, facility_uuid=facility_uuid)
    buildings = housing_buildings_for_user(user=request.user).filter(
        facility=facility,
        is_active=True,
    ).prefetch_related(
        Prefetch(
            "floors",
            queryset=HousingFloor._base_manager.filter(is_active=True),
        )
    )
    rooms = HousingRoom._base_manager.filter(facility=facility, is_active=True).select_related(
        "floor_unit__building"
    ).prefetch_related(
        Prefetch("beds", queryset=HousingBed._base_manager.filter(is_active=True))
    )
    assignments = housing_assignments_for_user(user=request.user, current_only=True).filter(
        bed__room__facility=facility
    )
    assignment_by_bed = {assignment.bed_id: assignment for assignment in assignments}
    reservations = housing_assignments_for_user(user=request.user).filter(
        bed__room__facility=facility,
        is_active=True,
        valid_from__gt=timezone.localdate(),
    ).order_by("valid_from", "pk")
    reservation_by_bed = {}
    for reservation in reservations:
        reservation_by_bed.setdefault(reservation.bed_id, reservation)
    room_rows = []
    for room in rooms:
        beds = list(room.beds.all())
        room_rows.append(
            {
                "room": room,
                "beds": [
                    {
                        "bed": bed,
                        "assignment": assignment_by_bed.get(bed.pk),
                        "reservation": reservation_by_bed.get(bed.pk),
                    }
                    for bed in beds
                ],
            }
        )
    return render(
        request,
        "hydra_housing/facility_detail.html",
        {"facility": facility, "buildings": buildings, "room_rows": room_rows},
    )


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.add_housingfacility",), raise_exception=True)
def housing_facility_create(request):
    form = HousingFacilityForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            facility = save_housing_facility(facility=form.save(commit=False), actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing facility created."))
            return redirect(facility)
    return render(request, "hydra_housing/model_form.html", {"form": form, "page_title": _("Create housing facility")})


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.add_housingroom",), raise_exception=True)
def housing_room_create(request, facility_uuid):
    facility = housing_facility_for_user(user=request.user, facility_uuid=facility_uuid)
    form = HousingRoomForm(
        request.POST or None,
        actor=request.user,
        facility=facility,
    )
    if request.method == "POST" and form.is_valid():
        room = form.save(commit=False)
        room.facility = facility
        try:
            save_housing_room(room=room, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing room created."))
            return redirect(facility)
    return render(request, "hydra_housing/model_form.html", {"form": form, "page_title": _("Create room"), "cancel_url": facility.get_absolute_url()})


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.add_housingbuilding",), raise_exception=True)
def housing_building_create(request, facility_uuid):
    facility = housing_facility_for_user(user=request.user, facility_uuid=facility_uuid)
    form = HousingBuildingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        building = form.save(commit=False)
        building.facility = facility
        try:
            save_housing_building(building=building, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing building created."))
            return redirect(facility)
    return render(
        request,
        "hydra_housing/model_form.html",
        {"form": form, "page_title": _("Create building"), "cancel_url": facility.get_absolute_url()},
    )


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.add_housingfloor",), raise_exception=True)
def housing_floor_create(request, building_uuid):
    building = housing_building_for_user(user=request.user, building_uuid=building_uuid)
    form = HousingFloorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        floor = form.save(commit=False)
        floor.building = building
        try:
            save_housing_floor(floor=floor, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing floor created."))
            return redirect(building.facility)
    return render(
        request,
        "hydra_housing/model_form.html",
        {"form": form, "page_title": _("Create floor"), "cancel_url": building.facility.get_absolute_url()},
    )


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.add_housingbed",), raise_exception=True)
def housing_bed_create(request, room_uuid):
    room = housing_room_for_user(user=request.user, room_uuid=room_uuid)
    form = HousingBedForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        bed = form.save(commit=False)
        bed.room = room
        try:
            save_housing_bed(bed=bed, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing bed created."))
            return redirect(room.facility)
    return render(request, "hydra_housing/model_form.html", {"form": form, "page_title": _("Create bed"), "cancel_url": room.facility.get_absolute_url()})


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.add_housingassignment",), raise_exception=True)
def housing_assign(request, person_uuid):
    person = person_for_user(user=request.user, person_uuid=person_uuid)
    form = HousingAssignmentForm(request.POST or None, actor=request.user, person=person)
    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.person = person
        try:
            assign_housing(assignment=assignment, actor=request.user)
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(
                request,
                _("Housing reserved.") if assignment.is_reservation else _("Housing assigned."),
            )
            return redirect(person)
    return render(request, "hydra_housing/assignment_form.html", {"form": form, "person": person})


@login_required
@permission_required(HOUSING_VIEW_PERMISSIONS + ("hydra_housing.change_housingassignment",), raise_exception=True)
def housing_assignment_end(request, assignment_uuid):
    assignment = housing_assignment_for_user(user=request.user, assignment_uuid=assignment_uuid)
    form = HousingEndForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            end_housing_assignment(
                assignment_uuid=assignment.uuid,
                valid_until=form.cleaned_data["valid_until"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing stay ended."))
            return redirect(assignment.person)
    return render(request, "hydra_housing/assignment_end_form.html", {"form": form, "assignment": assignment})


@login_required
@permission_required(
    HOUSING_VIEW_PERMISSIONS
    + (
        "hydra_housing.change_housingassignment",
        "hydra_housing.cancel_housingreservation",
    ),
    raise_exception=True,
)
def housing_reservation_cancel(request, assignment_uuid):
    assignment = housing_assignment_for_user(
        user=request.user,
        assignment_uuid=assignment_uuid,
    )
    form = HousingReservationCancelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            cancel_housing_reservation(
                assignment_uuid=assignment.uuid,
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing reservation cancelled."))
            return redirect(assignment.person)
    return render(
        request,
        "hydra_housing/reservation_cancel_form.html",
        {"form": form, "assignment": assignment},
    )


@login_required
@permission_required(
    HOUSING_VIEW_PERMISSIONS
    + (
        "hydra_housing.change_housingassignment",
        "hydra_housing.reserve_housingassignment",
        "hydra_housing.renew_housingreservation",
    ),
    raise_exception=True,
)
def housing_reservation_renew(request, assignment_uuid):
    assignment = housing_assignment_for_user(
        user=request.user,
        assignment_uuid=assignment_uuid,
    )
    form = HousingReservationRenewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            renew_housing_reservation(
                assignment_uuid=assignment.uuid,
                reservation_expires_at=form.cleaned_data["reservation_expires_at"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Temporary housing reservation renewed."))
            return redirect(assignment.person)
    return render(
        request,
        "hydra_housing/reservation_renew_form.html",
        {"form": form, "assignment": assignment},
    )


@login_required
@permission_required(
    HOUSING_VIEW_PERMISSIONS
    + (
        "hydra_housing.change_housingassignment",
        "hydra_housing.reserve_housingassignment",
        "hydra_housing.confirm_housingreservation",
    ),
    raise_exception=True,
)
def housing_reservation_confirm(request, assignment_uuid):
    assignment = housing_assignment_for_user(
        user=request.user,
        assignment_uuid=assignment_uuid,
    )
    form = HousingReservationConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            confirm_housing_reservation(
                assignment_uuid=assignment.uuid,
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Temporary housing reservation confirmed."))
            return redirect(assignment.person)
    return render(
        request,
        "hydra_housing/reservation_confirm_form.html",
        {"form": form, "assignment": assignment},
    )


@login_required
@permission_required(
    HOUSING_VIEW_PERMISSIONS
    + (
        "hydra_housing.add_housingassignment",
        "hydra_housing.change_housingassignment",
        "hydra_housing.move_housingassignment",
    ),
    raise_exception=True,
)
def housing_assignment_move(request, assignment_uuid):
    assignment = housing_assignment_for_user(
        user=request.user,
        assignment_uuid=assignment_uuid,
    )
    form = HousingMoveForm(
        request.POST or None,
        actor=request.user,
        assignment=assignment,
    )
    if request.method == "POST" and form.is_valid():
        try:
            destination = move_housing_assignment(
                assignment_uuid=assignment.uuid,
                destination_bed_id=form.cleaned_data["destination_bed"].pk,
                effective_on=form.cleaned_data["effective_on"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
            )
        except ValidationError as error:
            _add_validation_errors(form, error)
        else:
            messages.success(request, _("Housing move recorded."))
            return redirect(destination.person)
    return render(
        request,
        "hydra_housing/assignment_move_form.html",
        {"form": form, "assignment": assignment},
    )
