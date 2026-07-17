from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_housing.admin import (
    HousingAssignmentAdmin,
    HousingAssignmentEventAdmin,
    HousingFacilityAdmin,
)
from hydra_housing.models import (
    HousingAssignment,
    HousingAssignmentEvent,
    HousingBed,
    HousingFacility,
)
from hydra_housing.services import (
    cancel_housing_reservation,
    move_housing_assignment,
    save_housing_bed,
)
from hydra_housing.tests.test_housing import HydraHousingTestCase
from hydra_ops.readiness import domain_integrity_results
from hydra_people.models import Person
from hydra_people.services import link_candidate, save_person


class HousingReservationAndMoveTests(HydraHousingTestCase):
    def setUp(self):
        super().setUp()
        self.grant_housing_write()
        self.facility, self.room, self.bed_a = self.make_inventory(actor=self.user)
        self.bed_b = save_housing_bed(
            bed=HousingBed(room=self.room, label="Bed B"),
            actor=self.user,
        )

    def revoke(self, codename):
        self.user.user_permissions.remove(
            Permission.objects.get(
                content_type__app_label="hydra_housing",
                codename=codename,
            )
        )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def test_future_assignment_is_a_conflict_protected_reservation(self):
        start = timezone.localdate() + timedelta(days=7)

        reservation = self.make_assignment(
            bed=self.bed_a,
            valid_from=start,
            valid_until=start + timedelta(days=30),
        )

        self.assertTrue(reservation.is_reservation)
        event = reservation.events.get()
        self.assertEqual(event.action, HousingAssignmentEvent.Action.RESERVED)
        self.assertEqual(event.effective_on, start)
        self.assertEqual(event.actor, self.user)
        with self.assertRaisesMessage(ValidationError, "bed is already assigned"):
            self.make_assignment(
                person=self.person_c,
                bed=self.bed_a,
                valid_from=start + timedelta(days=1),
                valid_until=start + timedelta(days=2),
            )

    def test_future_reservation_requires_dedicated_permission(self):
        self.revoke("reserve_housingassignment")

        with self.assertRaises(PermissionDenied):
            self.make_assignment(
                bed=self.bed_a,
                valid_from=timezone.localdate() + timedelta(days=1),
            )

        self.assertFalse(HousingAssignment.objects.exists())

    def test_planned_arrival_can_receive_destination_reservation(self):
        self.grant(("hydra_people", "add_person"))
        person = save_person(
            person=Person(
                passport_name="DARIA DELTA",
                first_name="Daria",
                last_name="Delta",
                date_of_birth=date(1994, 3, 2),
                gender=Person.Gender.FEMALE,
                citizenship="UA",
                preferred_language=Person.PreferredLanguage.UKRAINIAN,
            ),
            actor=self.user,
        )
        candidate = self.make_candidate(
            "Daria application",
            "daria.application@example.test",
            self.recruitment_a,
            self.job_a,
            self.stage_a,
        )
        link_candidate(person=person, candidate=candidate, actor=self.admin)
        planned_at = timezone.now() + timedelta(days=5)
        ArrivalPlan.objects.create(
            person=person,
            candidate=candidate,
            destination_location=self.location_a,
            coordinator=self.user,
            planned_at=planned_at,
        )

        reservation = self.make_assignment(
            person=person,
            bed=self.bed_a,
            valid_from=timezone.localtime(planned_at).date(),
        )

        self.assertTrue(reservation.is_reservation)

    def test_reservation_cancellation_is_reasoned_append_only_and_idempotent(self):
        reservation = self.make_assignment(
            bed=self.bed_a,
            valid_from=timezone.localdate() + timedelta(days=5),
        )

        cancelled = cancel_housing_reservation(
            assignment_uuid=reservation.uuid,
            reason="Arrival plan changed",
            actor=self.user,
        )
        repeated = cancel_housing_reservation(
            assignment_uuid=reservation.uuid,
            reason="Arrival plan changed",
            actor=self.user,
        )

        self.assertEqual(cancelled.pk, repeated.pk)
        self.assertFalse(repeated.is_active)
        self.assertTrue(HousingAssignment.objects.filter(pk=reservation.pk).exists())
        self.assertEqual(
            reservation.events.filter(
                action=HousingAssignmentEvent.Action.CANCELLED
            ).count(),
            1,
        )
        with self.assertRaisesMessage(ValidationError, "terminal event"):
            cancel_housing_reservation(
                assignment_uuid=reservation.uuid,
                reason="Different reason",
                actor=self.user,
            )

    def test_move_atomically_closes_source_creates_destination_and_is_idempotent(self):
        today = timezone.localdate()
        source = self.make_assignment(
            bed=self.bed_a,
            valid_from=today - timedelta(days=3),
        )

        destination = move_housing_assignment(
            assignment_uuid=source.uuid,
            destination_bed_id=self.bed_b.pk,
            effective_on=today,
            reason="Operational room change",
            actor=self.user,
        )
        repeated = move_housing_assignment(
            assignment_uuid=source.uuid,
            destination_bed_id=self.bed_b.pk,
            effective_on=today,
            reason="Operational room change",
            actor=self.user,
        )

        source.refresh_from_db()
        self.assertEqual(destination.pk, repeated.pk)
        self.assertEqual(source.valid_until, today - timedelta(days=1))
        self.assertEqual(destination.valid_from, today)
        self.assertEqual(destination.bed, self.bed_b)
        self.assertEqual(
            source.events.get(action=HousingAssignmentEvent.Action.MOVED_OUT).related_assignment,
            destination,
        )
        self.assertEqual(
            destination.events.get(action=HousingAssignmentEvent.Action.MOVED_IN).related_assignment,
            source,
        )
        results = {result.name: result for result in domain_integrity_results()}
        self.assertTrue(results["housing_bed_periods"].ok)
        self.assertTrue(results["housing_person_periods"].ok)
        self.assertTrue(results["housing_assignment_baseline"].ok)
        self.assertTrue(results["housing_assignment_lifecycle"].ok)

    def test_scheduled_reservation_can_move_without_leaving_a_false_occupancy(self):
        start = timezone.localdate() + timedelta(days=5)
        source = self.make_assignment(bed=self.bed_a, valid_from=start)

        destination = move_housing_assignment(
            assignment_uuid=source.uuid,
            destination_bed_id=self.bed_b.pk,
            effective_on=start,
            reason="Reservation bed changed",
            actor=self.user,
        )

        source.refresh_from_db()
        self.assertFalse(source.is_active)
        self.assertTrue(destination.is_active)
        self.assertEqual(destination.valid_from, start)

    def test_destination_conflict_rolls_back_the_complete_move(self):
        today = timezone.localdate()
        source = self.make_assignment(
            person=self.person_a,
            bed=self.bed_a,
            valid_from=today - timedelta(days=2),
        )
        blocker = self.make_assignment(
            person=self.person_c,
            bed=self.bed_b,
            valid_from=today - timedelta(days=1),
        )

        with self.assertRaisesMessage(ValidationError, "bed is already assigned"):
            move_housing_assignment(
                assignment_uuid=source.uuid,
                destination_bed_id=self.bed_b.pk,
                effective_on=today,
                reason="Conflicting move",
                actor=self.user,
            )

        source.refresh_from_db()
        self.assertIsNone(source.valid_until)
        self.assertEqual(HousingAssignment.objects.count(), 2)
        self.assertEqual(blocker.events.count(), 1)
        self.assertFalse(
            HousingAssignmentEvent.objects.filter(
                action__in=(
                    HousingAssignmentEvent.Action.MOVED_OUT,
                    HousingAssignmentEvent.Action.MOVED_IN,
                )
            ).exists()
        )

    def test_move_requires_dedicated_permission_and_destination_scope(self):
        source = self.make_assignment(
            bed=self.bed_a,
            valid_from=timezone.localdate() - timedelta(days=2),
        )
        self.revoke("move_housingassignment")

        with self.assertRaises(PermissionDenied):
            move_housing_assignment(
                assignment_uuid=source.uuid,
                destination_bed_id=self.bed_b.pk,
                effective_on=timezone.localdate(),
                reason="Unauthorized move",
                actor=self.user,
            )

        self.grant(("hydra_housing", "move_housingassignment"))
        _facility, _room, remote_bed = self.make_inventory(
            location=self.location_b,
            suffix="Remote lifecycle",
            actor=self.admin,
        )
        with self.assertRaises(PermissionDenied):
            move_housing_assignment(
                assignment_uuid=source.uuid,
                destination_bed_id=remote_bed.pk,
                effective_on=timezone.localdate(),
                reason="Out of scope move",
                actor=self.user,
            )

    def test_assignment_and_event_facts_cannot_be_rewritten_or_deleted(self):
        assignment = self.make_assignment(bed=self.bed_a)
        event = assignment.events.get()

        assignment.person = self.person_c
        with self.assertRaises(TypeError):
            assignment.save()
        with self.assertRaises(TypeError):
            HousingAssignment.objects.filter(pk=assignment.pk).update(notes="rewrite")
        event.reason = "Rewritten"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            HousingAssignmentEvent.objects.filter(pk=event.pk).delete()

    def test_person_screen_exposes_scoped_actions_and_append_only_audit(self):
        assignment = self.make_assignment(
            bed=self.bed_a,
            valid_from=timezone.localdate() - timedelta(days=2),
        )
        self.login()

        response = self.client.get(self.person_a.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("hydra-housing-assignment-move", args=(assignment.uuid,)),
        )
        self.assertContains(response, "Housing audit")
        self.assertContains(response, "Housing assignment created")

    def test_move_view_records_the_atomic_transition(self):
        source = self.make_assignment(
            bed=self.bed_a,
            valid_from=timezone.localdate() - timedelta(days=2),
        )
        self.login()

        response = self.client.post(
            reverse("hydra-housing-assignment-move", args=(source.uuid,)),
            {
                "destination_bed": self.bed_b.pk,
                "effective_on": timezone.localdate().isoformat(),
                "reason": "View move acceptance",
            },
        )

        self.assertEqual(response.status_code, 302)
        source.refresh_from_db()
        self.assertEqual(source.valid_until, timezone.localdate() - timedelta(days=1))
        self.assertTrue(
            HousingAssignment.objects.filter(
                person=self.person_a,
                bed=self.bed_b,
                valid_from=timezone.localdate(),
            ).exists()
        )

    def test_cancel_view_preserves_the_reservation_and_event(self):
        reservation = self.make_assignment(
            bed=self.bed_a,
            valid_from=timezone.localdate() + timedelta(days=3),
        )
        self.login()

        response = self.client.post(
            reverse("hydra-housing-reservation-cancel", args=(reservation.uuid,)),
            {"reason": "View cancellation acceptance"},
        )

        self.assertEqual(response.status_code, 302)
        reservation.refresh_from_db()
        self.assertFalse(reservation.is_active)
        self.assertTrue(
            reservation.events.filter(
                action=HousingAssignmentEvent.Action.CANCELLED
            ).exists()
        )

    def test_direct_move_and_cancel_urls_hide_another_location(self):
        _facility, _room, remote_bed = self.make_inventory(
            location=self.location_b,
            suffix="Remote direct URL",
            actor=self.admin,
        )
        remote = self.make_assignment(
            person=self.person_b,
            bed=remote_bed,
            actor=self.admin,
        )
        self.login()

        move_response = self.client.get(
            reverse("hydra-housing-assignment-move", args=(remote.uuid,))
        )
        cancel_response = self.client.get(
            reverse("hydra-housing-reservation-cancel", args=(remote.uuid,))
        )

        self.assertEqual(move_response.status_code, 404)
        self.assertEqual(cancel_response.status_code, 404)

    def test_read_only_admin_querysets_keep_location_scope(self):
        local = self.make_assignment(bed=self.bed_a)
        remote_facility, _remote_room, remote_bed = self.make_inventory(
            location=self.location_b,
            suffix="Remote admin",
            actor=self.admin,
        )
        remote = self.make_assignment(
            person=self.person_b,
            bed=remote_bed,
            actor=self.admin,
        )
        request = RequestFactory().get("/admin/hydra_housing/")
        request.user = self.user

        facilities = HousingFacilityAdmin(HousingFacility, admin.site).get_queryset(request)
        assignments = HousingAssignmentAdmin(HousingAssignment, admin.site).get_queryset(request)
        events = HousingAssignmentEventAdmin(
            HousingAssignmentEvent,
            admin.site,
        ).get_queryset(request)

        self.assertTrue(facilities.filter(pk=self.facility.pk).exists())
        self.assertFalse(facilities.filter(pk=remote_facility.pk).exists())
        self.assertTrue(assignments.filter(pk=local.pk).exists())
        self.assertFalse(assignments.filter(pk=remote.pk).exists())
        self.assertTrue(events.filter(assignment=local).exists())
        self.assertFalse(events.filter(assignment=remote).exists())

    def test_readiness_detects_overlap_and_missing_origin_event(self):
        today = timezone.localdate()
        HousingAssignment.objects.bulk_create(
            [
                HousingAssignment(
                    person=self.person_a,
                    bed=self.bed_a,
                    valid_from=today,
                    valid_until=today + timedelta(days=2),
                ),
                HousingAssignment(
                    person=self.person_c,
                    bed=self.bed_a,
                    valid_from=today + timedelta(days=1),
                    valid_until=today + timedelta(days=3),
                ),
            ]
        )

        results = {result.name: result for result in domain_integrity_results()}

        self.assertFalse(results["housing_bed_periods"].ok)
        self.assertFalse(results["housing_assignment_baseline"].ok)
