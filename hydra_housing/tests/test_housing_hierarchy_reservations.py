from datetime import datetime, time, timedelta

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from hydra_coordination.models import ScopeGrant
from hydra_housing.models import (
    HousingAssignmentEvent,
    HousingBuilding,
    HousingFloor,
    HousingRoom,
)
from hydra_housing.services import (
    confirm_housing_reservation,
    expire_due_housing_reservations,
    renew_housing_reservation,
    save_housing_room,
)
from hydra_housing.tests.test_housing import HydraHousingTestCase


class HousingHierarchyTests(HydraHousingTestCase):
    def setUp(self):
        super().setUp()
        self.grant_housing_write()
        self.facility, self.room, self.bed = self.make_inventory(actor=self.user)

    def test_structured_building_floor_room_hierarchy_is_scoped_and_rendered(self):
        self.login()

        response = self.client.get(self.facility.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.room.floor_unit.building.name)
        self.assertContains(response, self.room.floor_unit.name)
        self.assertEqual(
            self.room.floor_unit.building.facility,
            self.facility,
        )

    def test_room_rejects_a_floor_from_another_facility(self):
        remote_facility, remote_room, _remote_bed = self.make_inventory(
            location=self.location_b,
            suffix="Remote hierarchy",
            actor=self.admin,
        )
        room = HousingRoom(
            facility=self.facility,
            floor_unit=remote_room.floor_unit,
            name="Forged cross-facility room",
        )

        with self.assertRaisesMessage(ValidationError, "inside the room facility"):
            room.full_clean()
        with self.assertRaises(PermissionDenied):
            save_housing_room(room=room, actor=self.user)
        self.assertFalse(
            HousingRoom.objects.filter(name="Forged cross-facility room").exists()
        )
        self.assertNotEqual(remote_facility, self.facility)

    def test_building_and_floor_can_be_created_through_scoped_ui(self):
        self.login()

        building_response = self.client.post(
            reverse("hydra-housing-building-create", args=(self.facility.uuid,)),
            {"name": "Annex", "notes": "Verified hierarchy"},
        )
        building = HousingBuilding.objects.get(
            facility=self.facility,
            name="Annex",
        )
        floor_response = self.client.post(
            reverse("hydra-housing-floor-create", args=(building.uuid,)),
            {"name": "Ground", "sort_order": 0},
        )

        self.assertEqual(building_response.status_code, 302)
        self.assertEqual(floor_response.status_code, 302)
        self.assertTrue(
            HousingFloor.objects.filter(
                building=building,
                name="Ground",
                created_by=self.user,
            ).exists()
        )

    def test_cross_scope_building_and_floor_create_urls_are_hidden(self):
        remote_facility, remote_room, _remote_bed = self.make_inventory(
            location=self.location_b,
            suffix="Remote URL hierarchy",
            actor=self.admin,
        )
        self.login()

        building_response = self.client.get(
            reverse("hydra-housing-building-create", args=(remote_facility.uuid,))
        )
        floor_response = self.client.get(
            reverse(
                "hydra-housing-floor-create",
                args=(remote_room.floor_unit.building.uuid,),
            )
        )

        self.assertEqual(building_response.status_code, 404)
        self.assertEqual(floor_response.status_code, 404)

    def test_building_creation_requires_dedicated_permission(self):
        permission = Permission.objects.get(
            content_type__app_label="hydra_housing",
            codename="add_housingbuilding",
        )
        self.user.user_permissions.remove(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)
        self.login()

        response = self.client.get(
            reverse("hydra-housing-building-create", args=(self.facility.uuid,))
        )

        self.assertEqual(response.status_code, 403)


class TemporaryHousingReservationTests(HydraHousingTestCase):
    def setUp(self):
        super().setUp()
        self.grant_housing_write()
        self.facility, self.room, self.bed = self.make_inventory(actor=self.user)

    def _temporary_reservation(self, *, expiry=None):
        start = timezone.localdate() + timedelta(days=2)
        expiry = expiry or timezone.now() + timedelta(hours=2)
        return self.make_assignment(
            bed=self.bed,
            valid_from=start,
            reservation_expires_at=expiry,
        )

    def test_temporary_reservation_can_be_renewed_with_append_only_evidence(self):
        reservation = self._temporary_reservation()
        new_expiry = reservation.reservation_expires_at + timedelta(hours=2)

        renewed = renew_housing_reservation(
            assignment_uuid=reservation.uuid,
            reservation_expires_at=new_expiry,
            reason="Arrival confirmation is pending",
            actor=self.user,
        )
        repeated = renew_housing_reservation(
            assignment_uuid=reservation.uuid,
            reservation_expires_at=new_expiry,
            reason="Arrival confirmation is pending",
            actor=self.user,
        )

        self.assertEqual(renewed.pk, repeated.pk)
        self.assertEqual(renewed.reservation_expires_at, new_expiry)
        event = renewed.events.get(action=HousingAssignmentEvent.Action.RENEWED)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.reason, "Arrival confirmation is pending")

    def test_confirmation_removes_expiry_but_preserves_the_reserved_period(self):
        reservation = self._temporary_reservation()

        confirmed = confirm_housing_reservation(
            assignment_uuid=reservation.uuid,
            reason="Arrival and accommodation approved",
            actor=self.user,
        )
        repeated = confirm_housing_reservation(
            assignment_uuid=reservation.uuid,
            reason="Arrival and accommodation approved",
            actor=self.user,
        )

        self.assertEqual(confirmed.pk, repeated.pk)
        self.assertIsNone(confirmed.reservation_expires_at)
        self.assertTrue(confirmed.is_active)
        self.assertEqual(confirmed.valid_from, reservation.valid_from)
        self.assertEqual(
            confirmed.events.filter(
                action=HousingAssignmentEvent.Action.CONFIRMED
            ).count(),
            1,
        )

    def test_due_hold_expires_once_as_a_system_transition(self):
        reservation = self._temporary_reservation()
        expiry = reservation.reservation_expires_at

        result = expire_due_housing_reservations(
            now=expiry + timedelta(seconds=1),
            limit=10,
        )
        repeated = expire_due_housing_reservations(
            now=expiry + timedelta(seconds=1),
            limit=10,
        )

        reservation.refresh_from_db()
        self.assertEqual((result.selected, result.expired), (1, 1))
        self.assertEqual((repeated.selected, repeated.expired), (0, 0))
        self.assertFalse(reservation.is_active)
        event = reservation.events.get(action=HousingAssignmentEvent.Action.EXPIRED)
        self.assertEqual(event.source, HousingAssignmentEvent.Source.SYSTEM)
        self.assertIsNone(event.actor)

    def test_temporary_expiry_must_be_future_and_not_after_the_stay_start(self):
        start = timezone.localdate() + timedelta(days=2)
        start_at = timezone.make_aware(
            datetime.combine(start, time.min),
            timezone.get_current_timezone(),
        )

        with self.assertRaisesMessage(ValidationError, "no later than"):
            self.make_assignment(
                bed=self.bed,
                valid_from=start,
                reservation_expires_at=start_at + timedelta(minutes=1),
            )

    def test_renewal_requires_permission_and_scope(self):
        reservation = self._temporary_reservation()
        permission = Permission.objects.get(
            content_type__app_label="hydra_housing",
            codename="renew_housingreservation",
        )
        self.user.user_permissions.remove(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

        with self.assertRaises(PermissionDenied):
            renew_housing_reservation(
                assignment_uuid=reservation.uuid,
                reservation_expires_at=(
                    reservation.reservation_expires_at + timedelta(hours=1)
                ),
                reason="Unauthorized renewal",
                actor=self.user,
            )

        remote_facility, remote_room, remote_bed = self.make_inventory(
            location=self.location_b,
            suffix="Remote reservation",
            actor=self.admin,
        )
        remote = self.make_assignment(
            person=self.person_b,
            bed=remote_bed,
            actor=self.admin,
            valid_from=timezone.localdate() + timedelta(days=2),
            reservation_expires_at=timezone.now() + timedelta(hours=1),
        )
        self.grant(("hydra_housing", "renew_housingreservation"))
        ScopeGrant.objects.filter(user=self.user, location=self.location_b).delete()

        with self.assertRaises(PermissionDenied):
            renew_housing_reservation(
                assignment_uuid=remote.uuid,
                reservation_expires_at=(
                    remote.reservation_expires_at + timedelta(hours=1)
                ),
                reason="Cross-scope renewal",
                actor=self.user,
            )
        self.assertNotEqual(remote_facility, self.facility)

    def test_temporary_reservation_ui_exposes_confirm_and_renew_actions(self):
        reservation = self._temporary_reservation()
        self.login()

        response = self.client.get(self.person_a.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("hydra-housing-reservation-confirm", args=(reservation.uuid,)),
        )
        self.assertContains(
            response,
            reverse("hydra-housing-reservation-renew", args=(reservation.uuid,)),
        )

    def test_assignment_form_creates_a_temporary_hold(self):
        self.login()
        start = timezone.localdate() + timedelta(days=2)
        expiry = timezone.localtime(timezone.now() + timedelta(hours=1)).replace(
            second=0,
            microsecond=0,
        )

        response = self.client.post(
            reverse("hydra-housing-assign", args=(self.person_a.uuid,)),
            {
                "bed": self.bed.pk,
                "valid_from": start.isoformat(),
                "valid_until": "",
                "reservation_expires_at": expiry.strftime("%Y-%m-%dT%H:%M"),
                "notes": "Temporary UI hold",
            },
        )

        self.assertEqual(response.status_code, 302)
        reservation = self.person_a.housing_assignments.get()
        self.assertEqual(
            timezone.localtime(reservation.reservation_expires_at).replace(
                second=0,
                microsecond=0,
            ),
            expiry,
        )
