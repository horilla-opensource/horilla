from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from hydra_coordination.models import Location, ScopeGrant
from hydra_housing.models import (
    HousingAssignment,
    HousingBed,
    HousingBuilding,
    HousingFacility,
    HousingFloor,
    HousingRoom,
)
from hydra_housing.selectors import housing_assignments_for_user, housing_facilities_for_user
from hydra_housing.services import (
    assign_housing,
    end_housing_assignment,
    save_housing_bed,
    save_housing_building,
    save_housing_facility,
    save_housing_floor,
    save_housing_room,
)
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


class HydraHousingTestCase(HydraRecruitmentTestCase):
    def setUp(self):
        super().setUp()
        self.location_a = Location.objects.get(name="Location A")
        self.location_b = Location.objects.get(name="Location B")
        self.location_grant, _created = ScopeGrant.objects.get_or_create(
            user=self.user,
            location=self.location_a,
        )

    def grant_housing_read(self):
        self.grant_read()
        self.grant(
            ("hydra_coordination", "view_location"),
            ("hydra_housing", "view_housingfacility"),
            ("hydra_housing", "view_housingroom"),
            ("hydra_housing", "view_housingbed"),
            ("hydra_housing", "view_housingassignment"),
        )

    def grant_housing_write(self):
        self.grant_housing_read()
        self.grant(
            ("hydra_housing", "add_housingfacility"),
            ("hydra_housing", "add_housingroom"),
            ("hydra_housing", "add_housingbuilding"),
            ("hydra_housing", "add_housingfloor"),
            ("hydra_housing", "add_housingbed"),
            ("hydra_housing", "add_housingassignment"),
            ("hydra_housing", "change_housingassignment"),
            ("hydra_housing", "reserve_housingassignment"),
            ("hydra_housing", "renew_housingreservation"),
            ("hydra_housing", "confirm_housingreservation"),
            ("hydra_housing", "cancel_housingreservation"),
            ("hydra_housing", "move_housingassignment"),
            ("hydra_housing", "view_housingassignmentevent"),
        )

    def make_inventory(self, *, location=None, suffix="A", actor=None):
        actor = actor or self.admin
        location = location or self.location_a
        facility = save_housing_facility(
            facility=HousingFacility(
                location=location,
                name=f"House {suffix}",
                address=f"{suffix} Street 1",
            ),
            actor=actor,
        )
        building = save_housing_building(
            building=HousingBuilding(
                facility=facility,
                name=f"Building {suffix}",
            ),
            actor=actor,
        )
        floor = save_housing_floor(
            floor=HousingFloor(
                building=building,
                name="1",
                sort_order=1,
            ),
            actor=actor,
        )
        room = save_housing_room(
            room=HousingRoom(
                facility=facility,
                floor_unit=floor,
                name=f"Room {suffix}",
            ),
            actor=actor,
        )
        bed = save_housing_bed(
            bed=HousingBed(room=room, label=f"Bed {suffix}"),
            actor=actor,
        )
        return facility, room, bed

    def make_assignment(
        self,
        *,
        person=None,
        bed=None,
        actor=None,
        valid_from=None,
        valid_until=None,
        reservation_expires_at=None,
    ):
        actor = actor or self.user
        person = person or self.person_a
        if bed is None:
            _facility, _room, bed = self.make_inventory(actor=actor)
        return assign_housing(
            assignment=HousingAssignment(
                person=person,
                bed=bed,
                valid_from=valid_from or timezone.localdate(),
                valid_until=valid_until,
                reservation_expires_at=reservation_expires_at,
                notes="  Near   the gate  ",
            ),
            actor=actor,
        )


class HousingPermissionAndScopeTests(HydraHousingTestCase):
    def test_missing_housing_permission_returns_403(self):
        self.grant_read()
        self.grant(("hydra_coordination", "view_location"))
        self.login()

        response = self.client.get(reverse("hydra-housing-dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_and_direct_facility_url_are_location_scoped(self):
        facility_a, _room_a, _bed_a = self.make_inventory()
        facility_b, _room_b, _bed_b = self.make_inventory(
            location=self.location_b,
            suffix="B",
        )
        self.grant_housing_read()
        self.login()

        response = self.client.get(reverse("hydra-housing-dashboard"))
        denied = self.client.get(facility_b.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, facility_a.name)
        self.assertNotContains(response, facility_b.name)
        self.assertEqual(denied.status_code, 404)

    def test_team_grant_alone_does_not_expand_housing_location(self):
        self.make_inventory()
        self.location_grant.delete()
        self.grant_housing_read()

        self.assertFalse(housing_facilities_for_user(user=self.user).exists())

    def test_create_form_rejects_out_of_scope_location(self):
        self.grant_housing_write()
        self.login()

        response = self.client.post(
            reverse("hydra-housing-facility-create"),
            {
                "location": self.location_b.pk,
                "name": "Forged house",
                "address": "B Street",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(HousingFacility.objects.filter(name="Forged house").exists())

    def test_service_rejects_person_at_another_location(self):
        _facility, _room, bed_b = self.make_inventory(
            location=self.location_b,
            suffix="B",
        )

        with self.assertRaises(PermissionDenied):
            self.make_assignment(person=self.person_a, bed=bed_b, actor=self.admin)


class HousingAssignmentTests(HydraHousingTestCase):
    def setUp(self):
        super().setUp()
        self.grant_housing_write()
        self.facility, self.room, self.bed_a = self.make_inventory(actor=self.user)
        self.bed_b = save_housing_bed(
            bed=HousingBed(room=self.room, label="Bed B"),
            actor=self.user,
        )

    def test_assignment_is_normalized_stamped_and_visible(self):
        assignment = self.make_assignment(bed=self.bed_a)

        self.assertEqual(assignment.notes, "Near   the gate")
        self.assertEqual(assignment.created_by, self.user)
        self.assertEqual(assignment.modified_by, self.user)
        self.assertTrue(assignment.is_current())
        self.assertEqual(
            list(housing_assignments_for_user(user=self.user)),
            [assignment],
        )

    def test_bed_cannot_have_overlapping_assignments(self):
        today = timezone.localdate()
        self.make_assignment(
            person=self.person_a,
            bed=self.bed_a,
            valid_from=today,
            valid_until=today + timedelta(days=2),
        )

        with self.assertRaisesMessage(ValidationError, "bed is already assigned"):
            self.make_assignment(
                person=self.person_c,
                bed=self.bed_a,
                valid_from=today + timedelta(days=1),
                valid_until=today + timedelta(days=3),
            )

    def test_person_cannot_have_overlapping_assignments(self):
        today = timezone.localdate()
        self.make_assignment(
            person=self.person_a,
            bed=self.bed_a,
            valid_from=today,
            valid_until=today + timedelta(days=2),
        )

        with self.assertRaisesMessage(ValidationError, "already has housing"):
            self.make_assignment(
                person=self.person_a,
                bed=self.bed_b,
                valid_from=today + timedelta(days=1),
                valid_until=today + timedelta(days=3),
            )

    def test_adjacent_non_overlapping_periods_are_allowed(self):
        today = timezone.localdate()
        first = self.make_assignment(
            person=self.person_a,
            bed=self.bed_a,
            valid_from=today,
            valid_until=today,
        )
        second = self.make_assignment(
            person=self.person_c,
            bed=self.bed_a,
            valid_from=today + timedelta(days=1),
        )

        self.assertEqual(HousingAssignment.objects.count(), 2)
        self.assertEqual((first.valid_until, second.valid_from), (today, today + timedelta(days=1)))

    def test_end_is_idempotent_and_preserves_history(self):
        today = timezone.localdate()
        assignment = self.make_assignment(
            bed=self.bed_a,
            valid_from=today - timedelta(days=2),
        )

        ended = end_housing_assignment(
            assignment_uuid=assignment.uuid,
            valid_until=today,
            reason="Departure confirmed",
            actor=self.user,
        )
        repeated = end_housing_assignment(
            assignment_uuid=assignment.uuid,
            valid_until=today,
            reason="Departure confirmed",
            actor=self.user,
        )

        self.assertEqual(ended.pk, repeated.pk)
        self.assertEqual(repeated.valid_until, today)
        self.assertTrue(HousingAssignment.objects.filter(pk=assignment.pk).exists())

    def test_person_detail_exposes_scoped_housing_and_end_action(self):
        assignment = self.make_assignment(bed=self.bed_a)
        self.login()

        response = self.client.get(self.person_a.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.facility.name)
        self.assertContains(
            response,
            reverse("hydra-housing-assignment-end", args=(assignment.uuid,)),
        )

    def test_assignment_form_rejects_a_person_from_another_location(self):
        _facility_b, _room_b, bed_b = self.make_inventory(
            location=self.location_b,
            suffix="Remote",
            actor=self.admin,
        )
        ScopeGrant.objects.create(user=self.user, location=self.location_b)
        self.login()

        response = self.client.post(
            reverse("hydra-housing-assign", args=(self.person_a.uuid,)),
            {
                "bed": bed_b.pk,
                "valid_from": timezone.localdate().isoformat(),
                "valid_until": "",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "effective Team, confirmed-arrival")
        self.assertFalse(HousingAssignment.objects.exists())
