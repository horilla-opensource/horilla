from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan, ArrivalStatusHistory
from hydra_arrivals.selectors import arrival_plans_for_user
from hydra_arrivals.services import (
    create_arrival_plan,
    transition_arrival_plan,
    update_arrival_plan,
)
from hydra_coordination.models import Location, ScopeGrant
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase


class HydraArrivalTestCase(HydraRecruitmentTestCase):
    def setUp(self):
        super().setUp()
        self.location_a = Location.objects.get(name="Location A")
        self.location_b = Location.objects.get(name="Location B")
        self.location_grant, _created = ScopeGrant.objects.get_or_create(
            user=self.user,
            location=self.location_a,
        )

    def grant_arrival_read(self):
        self.grant_read()
        self.grant(
            ("hydra_coordination", "view_location"),
            ("hydra_arrivals", "view_arrivalplan"),
            ("hydra_arrivals", "view_arrivalstatushistory"),
        )

    def grant_arrival_write(self, *, include_assign=True):
        self.grant_arrival_read()
        permissions = [
            ("hydra_arrivals", "add_arrivalplan"),
            ("hydra_arrivals", "change_arrivalplan"),
            ("hydra_arrivals", "transition_arrivalplan"),
        ]
        if include_assign:
            permissions.append(("hydra_arrivals", "assign_arrivalplan"))
        self.grant(*permissions)

    def make_plan(
        self,
        *,
        actor=None,
        person=None,
        candidate=None,
        location=None,
        coordinator=None,
        planned_at=None,
        **overrides,
    ):
        actor = actor or self.user
        values = {
            "person": person or self.person_a,
            "candidate": candidate or self.candidate_a,
            "destination_location": location or self.location_a,
            "coordinator": coordinator or actor,
            "planned_at": planned_at or timezone.now() + timedelta(days=1),
            "transport_type": ArrivalPlan.TransportType.BUS,
            "transport_reference": "BUS  401",
            "pickup_point": "  Main   gate ",
            "notes": " Bring interpreter ",
        }
        values.update(overrides)
        return create_arrival_plan(plan=ArrivalPlan(**values), actor=actor)


class ArrivalPermissionAndScopeTests(HydraArrivalTestCase):
    def test_missing_model_permission_returns_403(self):
        self.grant_read()
        self.grant(("hydra_coordination", "view_location"))
        self.login()

        response = self.client.get(reverse("hydra-arrival-list"))

        self.assertEqual(response.status_code, 403)

    def test_list_and_direct_uuid_are_location_scoped(self):
        plan_a = self.make_plan(actor=self.admin, coordinator=self.admin)
        plan_b = self.make_plan(
            actor=self.admin,
            person=self.person_b,
            candidate=self.candidate_b,
            location=self.location_b,
            coordinator=self.admin,
        )
        self.grant_arrival_read()
        self.login()

        response = self.client.get(reverse("hydra-arrival-list"))
        denied = self.client.get(plan_b.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, plan_a.person.hydra_id)
        self.assertNotContains(response, plan_b.person.hydra_id)
        self.assertEqual(denied.status_code, 404)

    def test_team_grant_alone_does_not_expand_to_location_arrivals(self):
        self.make_plan(actor=self.admin, coordinator=self.admin)
        self.location_grant.delete()
        self.grant_arrival_read()

        self.assertFalse(arrival_plans_for_user(user=self.user).exists())

    def test_create_form_rejects_out_of_scope_location(self):
        self.grant_arrival_write()
        self.login()

        response = self.client.post(
            reverse("hydra-arrival-create", args=(self.person_a.uuid,)),
            {
                "candidate": self.candidate_a.pk,
                "destination_location": self.location_b.pk,
                "coordinator": self.user.pk,
                "planned_at": (timezone.now() + timedelta(days=1)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "transport_type": ArrivalPlan.TransportType.TRAIN,
                "transport_reference": "IC 100",
                "pickup_point": "Station",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(ArrivalPlan.objects.exists())

    def test_assigning_another_coordinator_requires_permission(self):
        self.grant_arrival_write(include_assign=False)

        with self.assertRaises(PermissionDenied):
            self.make_plan(coordinator=self.admin)


class ArrivalPlanningTests(HydraArrivalTestCase):
    def setUp(self):
        super().setUp()
        self.grant_arrival_write()

    def test_create_normalizes_plan_and_records_initial_history(self):
        self.login()

        response = self.client.post(
            reverse("hydra-arrival-create", args=(self.person_a.uuid,)),
            {
                "candidate": self.candidate_a.pk,
                "destination_location": self.location_a.pk,
                "coordinator": self.user.pk,
                "planned_at": (timezone.now() + timedelta(days=1)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "transport_type": ArrivalPlan.TransportType.BUS,
                "transport_reference": "  BUS   401 ",
                "pickup_point": "  Main   gate ",
                "notes": " Bring interpreter ",
            },
        )

        self.assertEqual(response.status_code, 302)
        plan = ArrivalPlan.objects.get()
        self.assertEqual(plan.status, ArrivalPlan.Status.PLANNED)
        self.assertEqual(plan.transport_reference, "BUS 401")
        self.assertEqual(plan.pickup_point, "Main gate")
        self.assertEqual(plan.notes, "Bring interpreter")
        self.assertEqual(plan.created_by, self.user)
        event = plan.status_history.get()
        self.assertEqual((event.from_status, event.to_status), ("", "planned"))
        self.assertEqual(event.actor, self.user)

    def test_candidate_company_and_person_link_are_enforced(self):
        wrong_company = ArrivalPlan(
            person=self.person_a,
            candidate=self.candidate_a,
            destination_location=self.location_b,
            coordinator=self.admin,
            planned_at=timezone.now() + timedelta(days=1),
        )
        wrong_person = ArrivalPlan(
            person=self.person_b,
            candidate=self.candidate_a,
            destination_location=self.location_a,
            coordinator=self.admin,
            planned_at=timezone.now() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            wrong_company.full_clean()
        with self.assertRaises(ValidationError):
            wrong_person.full_clean()

    def test_only_one_planned_arrival_is_allowed_per_application(self):
        self.make_plan()

        with self.assertRaisesMessage(ValidationError, "already has a planned arrival"):
            self.make_plan(planned_at=timezone.now() + timedelta(days=2))

        self.assertEqual(ArrivalPlan.objects.count(), 1)

    def test_terminal_plan_cannot_be_edited(self):
        plan = self.make_plan()
        transition_arrival_plan(
            plan_uuid=plan.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=timezone.now(),
            actor=self.user,
        )
        plan.refresh_from_db()
        plan.notes = "changed"

        with self.assertRaisesMessage(ValidationError, "cannot be edited"):
            update_arrival_plan(plan=plan, actor=self.user)


class ArrivalTransitionTests(HydraArrivalTestCase):
    def setUp(self):
        super().setUp()
        self.grant_arrival_write()

    def test_confirm_is_audited_and_idempotent(self):
        plan = self.make_plan()
        actual = timezone.now()

        first = transition_arrival_plan(
            plan_uuid=plan.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=actual,
            actor=self.user,
        )
        second = transition_arrival_plan(
            plan_uuid=plan.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=actual,
            actor=self.user,
        )

        self.assertEqual(first.status, ArrivalPlan.Status.CONFIRMED)
        self.assertEqual(second.status, ArrivalPlan.Status.CONFIRMED)
        self.assertEqual(second.actual_arrived_at, actual)
        self.assertEqual(second.status_history.count(), 2)

    def test_no_show_requires_due_time_and_reason_then_records_reason(self):
        plan = self.make_plan()

        with self.assertRaisesMessage(ValidationError, "before the planned time"):
            transition_arrival_plan(
                plan_uuid=plan.uuid,
                target_status=ArrivalPlan.Status.NO_SHOW,
                reason="Missing",
                actor=self.user,
            )
        ArrivalPlan.objects.filter(pk=plan.pk).update(
            planned_at=timezone.now() - timedelta(hours=1)
        )
        with self.assertRaisesMessage(ValidationError, "requires a reason"):
            transition_arrival_plan(
                plan_uuid=plan.uuid,
                target_status=ArrivalPlan.Status.NO_SHOW,
                reason="",
                actor=self.user,
            )

        result = transition_arrival_plan(
            plan_uuid=plan.uuid,
            target_status=ArrivalPlan.Status.NO_SHOW,
            reason="  Driver   reported absence ",
            actor=self.user,
        )

        self.assertEqual(result.status, ArrivalPlan.Status.NO_SHOW)
        self.assertEqual(result.no_show_reason, "Driver reported absence")
        self.assertEqual(result.status_history.first().reason, result.no_show_reason)

    def test_opposite_terminal_outcome_is_rejected_without_new_history(self):
        plan = self.make_plan()
        transition_arrival_plan(
            plan_uuid=plan.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actor=self.user,
        )

        with self.assertRaisesMessage(ValidationError, "different outcome"):
            transition_arrival_plan(
                plan_uuid=plan.uuid,
                target_status=ArrivalPlan.Status.NO_SHOW,
                reason="Not present",
                actor=self.user,
            )

        self.assertEqual(plan.status_history.count(), 2)

    def test_history_is_append_only(self):
        plan = self.make_plan()
        event = plan.status_history.get()

        event.reason = "rewrite"
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            ArrivalStatusHistory.objects.filter(pk=event.pk).update(reason="rewrite")
        with self.assertRaises(TypeError):
            event.delete()


class ArrivalCompatibilityTests(HydraArrivalTestCase):
    def test_original_onboarding_candidate_view_remains_operational(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("candidates-view"))

        self.assertEqual(response.status_code, 200)
