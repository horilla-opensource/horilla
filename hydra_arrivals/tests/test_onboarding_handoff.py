from datetime import date
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import (
    ArrivalPlan,
    OnboardingHandoff,
    OnboardingHandoffEvent,
    OnboardingPortalDelivery,
)
from hydra_arrivals.onboarding import (
    HANDOFF_RECONCILE_PERMISSIONS,
    HANDOFF_START_PERMISSIONS,
    HANDOFF_TASK_UPDATE_PERMISSIONS,
    reconcile_open_onboarding_handoffs,
    start_onboarding_handoff,
    update_onboarding_task_status,
)
from hydra_arrivals.services import transition_arrival_plan
from hydra_arrivals.portal_email import dispatch_portal_emails
from hydra_arrivals.tests.test_arrivals import HydraArrivalTestCase
from hydra_coordination.models import Location, ScopeGrant, Section, Team
from hydra_coordination.services import assign_employee_to_team
from hydra_people.models import Person
from hydra_people.recruitment_workflow import transition_candidate
from hydra_people.services import (
    CONVERSION_PERMISSIONS,
    convert_person_to_employee,
    link_candidate,
)
from onboarding.models import CandidateStage, CandidateTask, OnboardingStage, OnboardingTask
from recruitment.models import Candidate, Stage


class OnboardingHandoffTestCase(HydraArrivalTestCase):
    def setUp(self):
        super().setUp()
        self.candidate_a = Candidate._base_manager.get(pk=type(self).candidate_a.pk)
        self.candidate_b = Candidate._base_manager.get(pk=type(self).candidate_b.pk)
        self.person_a = Person.objects.get(pk=type(self).person_a.pk)
        self.person_b = Person.objects.get(pk=type(self).person_b.pk)
        self.hired_stage_a = Stage._base_manager.create(
            recruitment_id=self.recruitment_a,
            stage="Hired",
            stage_type="hired",
            sequence=100,
        )
        self.candidate_a, _transition = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.hired_stage_a,
            actor=self.admin,
            reason="Onboarding handoff test setup.",
            joining_date=date(2026, 8, 3),
        )
        self.onboarding_stage = OnboardingStage._base_manager.get(
            recruitment_id=self.recruitment_a
        )
        self.onboarding_task = OnboardingTask.objects.create(
            task_title="Verify first-day documents",
            stage_id=self.onboarding_stage,
        )
        self.onboarding_task.employee_id.add(self.employee)

    def grant_permissions(self, permissions):
        self.grant(*(tuple(permission.split(".", 1)) for permission in permissions))

    def grant_handoff_start(self):
        self.grant_permissions(HANDOFF_START_PERMISSIONS)
        self.grant(
            ("hydra_arrivals", "view_onboardinghandoffevent"),
            ("hydra_arrivals", "reconcile_onboardinghandoff"),
        )

    def confirmed_plan(self, *, location=None):
        plan = self.make_plan(
            actor=self.admin,
            coordinator=self.admin,
            location=location or self.location_a,
        )
        return transition_arrival_plan(
            plan_uuid=plan.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actual_arrived_at=timezone.now(),
            actor=self.admin,
        )


class OnboardingHandoffStartTests(OnboardingHandoffTestCase):
    def test_confirmed_hired_candidate_starts_reused_onboarding_once(self):
        plan = self.confirmed_plan()
        self.grant_handoff_start()

        first = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)
        second = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.status, OnboardingHandoff.Status.STARTED)
        self.assertEqual(OnboardingHandoff.objects.count(), 1)
        self.assertEqual(CandidateStage.objects.filter(candidate_id=self.candidate_a).count(), 1)
        task = CandidateTask.objects.get(candidate_id=self.candidate_a)
        self.assertEqual(task.stage_id, self.onboarding_stage)
        self.assertTrue(self.onboarding_task.candidates.filter(pk=self.candidate_a.pk).exists())
        self.assertEqual(first.started_snapshot["task_count"], 1)
        self.assertEqual(first.started_snapshot["tasks_created"], 1)
        self.candidate_a.refresh_from_db()
        self.person_a.refresh_from_db()
        self.assertTrue(self.candidate_a.start_onboard)
        self.assertEqual(self.person_a.lifecycle_state, self.person_a.LifecycleState.ONBOARDING)
        event = first.events.get()
        self.assertEqual(event.event_type, OnboardingHandoffEvent.EventType.STARTED)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.source, OnboardingHandoffEvent.Source.USER)
        notification = self.user.notifications.get(
            verb="A confirmed arrival is ready for onboarding."
        )
        self.assertNotIn(self.person_a.hydra_id, notification.verb)
        self.assertNotIn(self.candidate_a.email, notification.verb)

    def test_unconfirmed_or_not_hired_candidate_is_rejected_without_side_effects(self):
        self.grant_handoff_start()
        planned = self.make_plan(actor=self.admin, coordinator=self.admin)

        with self.assertRaisesMessage(ValidationError, "Confirm the arrival"):
            start_onboarding_handoff(plan_uuid=planned.uuid, actor=self.user)

        confirmed = transition_arrival_plan(
            plan_uuid=planned.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actor=self.admin,
        )
        self.candidate_a, _transition = transition_candidate(
            candidate=self.candidate_a,
            target_stage=self.stage_a,
            actor=self.admin,
            reason="Verify non-hired onboarding rejection.",
        )
        with self.assertRaisesMessage(ValidationError, "Mark the application as hired"):
            start_onboarding_handoff(plan_uuid=confirmed.uuid, actor=self.user)

        self.assertFalse(OnboardingHandoff.objects.exists())
        self.assertFalse(CandidateStage.objects.filter(candidate_id=self.candidate_a).exists())
        self.candidate_a.refresh_from_db()
        self.assertFalse(self.candidate_a.start_onboard)

    def test_missing_permission_and_out_of_scope_direct_url_are_denied(self):
        plan = self.confirmed_plan()

        with self.assertRaises(PermissionDenied):
            start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        outside = self.make_plan(
            actor=self.admin,
            person=self.person_b,
            candidate=self.candidate_b,
            location=self.location_b,
            coordinator=self.admin,
        )
        hired_stage_b = Stage._base_manager.create(
            recruitment_id=self.recruitment_b,
            stage="Hired",
            stage_type="hired",
            sequence=100,
        )
        self.candidate_b, _transition = transition_candidate(
            candidate=self.candidate_b,
            target_stage=hired_stage_b,
            actor=self.admin,
            reason="Out-of-scope onboarding test setup.",
            joining_date=date(2026, 8, 3),
        )
        outside = transition_arrival_plan(
            plan_uuid=outside.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actor=self.admin,
        )
        self.grant_handoff_start()
        self.login()

        response = self.client.post(
            reverse("hydra-onboarding-handoff-start", args=(outside.uuid,))
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(OnboardingHandoff.objects.filter(arrival=outside).exists())

    def test_duplicate_candidate_task_rows_block_handoff_for_integrity_review(self):
        plan = self.confirmed_plan()
        self.grant_handoff_start()
        CandidateStage.objects.create(
            candidate_id=self.candidate_a,
            onboarding_stage_id=self.onboarding_stage,
        )
        for _ in range(2):
            CandidateTask.objects.create(
                candidate_id=self.candidate_a,
                stage_id=self.onboarding_stage,
                onboarding_task_id=self.onboarding_task,
            )

        with self.assertRaisesMessage(ValidationError, "Duplicate onboarding task"):
            start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        self.assertFalse(OnboardingHandoff.objects.exists())
        self.candidate_a.refresh_from_db()
        self.assertFalse(self.candidate_a.start_onboard)

    def test_detail_shows_scoped_handoff_tasks_and_history(self):
        plan = self.confirmed_plan()
        self.grant_handoff_start()
        start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)
        self.login()

        response = self.client.get(plan.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Onboarding handoff")
        self.assertContains(response, self.onboarding_task.task_title)
        self.assertContains(response, "Handoff started")

    def test_handoff_events_are_append_only(self):
        plan = self.confirmed_plan()
        self.grant_handoff_start()
        handoff = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)
        event = handoff.events.get()

        event.snapshot = {"rewrite": True}
        with self.assertRaises(TypeError):
            event.save()
        with self.assertRaises(TypeError):
            OnboardingHandoffEvent.objects.filter(pk=event.pk).update(
                snapshot={"rewrite": True}
            )
        with self.assertRaises(TypeError):
            event.delete()

    def test_legacy_get_and_bulk_routes_cannot_bypass_scoped_task_service(self):
        plan = self.confirmed_plan()
        handoff = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.admin)
        task = CandidateTask.objects.get(candidate_id=self.candidate_a)
        self.client.force_login(self.admin)

        unsafe_get = self.client.get(
            reverse("change-task-status"),
            {"task_id": task.pk, "status": "done"},
        )
        unsafe_bulk = self.client.post(
            reverse("candidate-task-bulk-update"),
            {
                "ids": f"[{self.candidate_a.pk}]",
                "task": self.onboarding_task.pk,
                "status": "done",
            },
        )

        self.assertEqual(unsafe_get.status_code, 405)
        self.assertEqual(unsafe_bulk.status_code, 409)
        task.refresh_from_db()
        handoff.refresh_from_db()
        self.assertEqual(task.status, "todo")
        self.assertEqual(handoff.status, OnboardingHandoff.Status.STARTED)

    def test_one_person_can_have_separate_handoffs_for_multiple_applications(self):
        first_plan = self.confirmed_plan()
        first = start_onboarding_handoff(plan_uuid=first_plan.uuid, actor=self.admin)
        second_candidate = self.make_candidate(
            "Anna second application",
            "anna.second@example.test",
            self.recruitment_b,
            self.job_b,
            self.stage_b,
        )
        link_candidate(
            person=self.person_a,
            candidate=second_candidate,
            actor=self.admin,
        )
        hired_stage_b = Stage._base_manager.create(
            recruitment_id=self.recruitment_b,
            stage="Hired",
            stage_type="hired",
            sequence=100,
        )
        second_candidate, _transition = transition_candidate(
            candidate=second_candidate,
            target_stage=hired_stage_b,
            actor=self.admin,
            reason="Second-application onboarding test setup.",
            joining_date=date(2026, 8, 3),
        )
        second_plan = self.make_plan(
            actor=self.admin,
            person=self.person_a,
            candidate=second_candidate,
            location=self.location_b,
            coordinator=self.admin,
        )
        second_plan = transition_arrival_plan(
            plan_uuid=second_plan.uuid,
            target_status=ArrivalPlan.Status.CONFIRMED,
            actor=self.admin,
        )

        second = start_onboarding_handoff(
            plan_uuid=second_plan.uuid,
            actor=self.admin,
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(
            OnboardingHandoff.objects.filter(person=self.person_a).count(),
            2,
        )


class OnboardingHandoffMilestoneTests(OnboardingHandoffTestCase):
    def grant_conversion_and_assignment(self):
        self.grant_permissions(CONVERSION_PERMISSIONS)
        self.grant_permissions(HANDOFF_TASK_UPDATE_PERMISSIONS)
        self.grant(
            ("hydra_coordination", "add_personassignment"),
            ("hydra_coordination", "assign_person"),
            ("employee", "view_employee"),
            ("employee", "change_employeeworkinformation"),
        )

    def convert(self):
        return convert_person_to_employee(
            person=self.person_a,
            candidate=self.candidate_a,
            work_email="handoff.employee@example.test",
            phone="+48123456789",
            joining_date=date.today(),
            actor=self.user,
        )

    def test_conversion_and_existing_destination_assignment_complete_handoff(self):
        plan = self.confirmed_plan()
        self.grant_handoff_start()
        self.grant_conversion_and_assignment()
        handoff = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        employee, conversion, created = self.convert()

        handoff.refresh_from_db()
        self.assertTrue(created)
        self.assertEqual(handoff.employee_conversion, conversion)
        self.assertIsNotNone(handoff.person_assignment_id)
        self.assertEqual(handoff.status, OnboardingHandoff.Status.ASSIGNED)
        self.assertIsNone(handoff.completed_at)

        task = CandidateTask.objects.get(candidate_id=self.candidate_a)
        task, handoff = update_onboarding_task_status(
            handoff=handoff,
            candidate_task_id=task.pk,
            status="done",
            actor=self.user,
        )

        self.assertEqual(task.status, "done")
        self.assertEqual(handoff.status, OnboardingHandoff.Status.COMPLETED)
        self.assertIsNotNone(handoff.completed_at)
        self.assertEqual(
            list(handoff.events.values_list("event_type", flat=True)),
            ["started", "conversion", "assignment", "completed"],
        )
        completion_event = handoff.events.get(
            event_type=OnboardingHandoffEvent.EventType.COMPLETED
        )
        self.assertEqual(completion_event.snapshot["task_count"], 1)
        self.assertEqual(completion_event.snapshot["completed_task_count"], 1)

    def test_wrong_location_assignment_does_not_complete_until_destination_team_exists(self):
        destination = Location.objects.create(
            company=self.company_a,
            name="Location A2",
            code="LOC-A2",
        )
        section = Section.objects.create(
            location=destination,
            department=self.department_a,
            name="Destination section",
            code="DEST",
        )
        destination_team = Team.objects.create(
            section=section,
            name="Destination team",
            code="DEST",
        )
        ScopeGrant.objects.create(user=self.user, location=destination)
        plan = self.confirmed_plan(location=destination)
        self.grant_handoff_start()
        self.grant_conversion_and_assignment()
        handoff = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        self.convert()
        handoff.refresh_from_db()
        self.assertEqual(handoff.status, OnboardingHandoff.Status.CONVERTED)
        self.assertIsNone(handoff.person_assignment_id)

        assignment = assign_employee_to_team(
            person=self.person_a,
            team=destination_team,
            valid_from=timezone.localdate(),
            actor=self.user,
        )
        handoff.refresh_from_db()
        self.assertEqual(handoff.person_assignment, assignment)
        self.assertEqual(handoff.status, OnboardingHandoff.Status.ASSIGNED)
        task = CandidateTask.objects.get(candidate_id=self.candidate_a)
        _task, handoff = update_onboarding_task_status(
            handoff=handoff,
            candidate_task_id=task.pk,
            status="done",
            actor=self.user,
        )
        self.assertEqual(handoff.status, OnboardingHandoff.Status.COMPLETED)

        with self.assertRaisesMessage(ValidationError, "completed onboarding"):
            update_onboarding_task_status(
                handoff=handoff,
                candidate_task_id=task.pk,
                status="todo",
                actor=self.user,
            )

    def test_worker_reconciliation_is_bounded_and_idempotent(self):
        plan = self.confirmed_plan()
        self.grant_handoff_start()
        handoff = start_onboarding_handoff(plan_uuid=plan.uuid, actor=self.user)

        first = reconcile_open_onboarding_handoffs(batch_size=1)
        second = reconcile_open_onboarding_handoffs(batch_size=1)

        self.assertEqual(first.handoffs_selected, 1)
        self.assertEqual(first.handoffs_updated, 0)
        self.assertEqual(second.handoffs_selected, 1)
        self.assertEqual(handoff.events.count(), 1)
        with self.assertRaises(ValidationError):
            reconcile_open_onboarding_handoffs(batch_size=0)


class HydraOnboardingRegressionTests(OnboardingHandoffTestCase):
    def test_candidate_detail_get_does_not_create_onboarding_rows(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("candidate-single-view", args=(self.candidate_a.pk,)),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CandidateStage.objects.filter(candidate_id=self.candidate_a).exists())
        self.assertFalse(CandidateTask.objects.filter(candidate_id=self.candidate_a).exists())

    @patch(
        "hydra_arrivals.portal_email.EmailMessage.send",
        side_effect=RuntimeError("mail down"),
    )
    def test_failed_portal_email_does_not_mark_onboarding_started(self, send):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("email-send"),
            {"ids": [str(self.candidate_a.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        send.assert_not_called()
        delivery = OnboardingPortalDelivery.objects.get(candidate=self.candidate_a)
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.PENDING)
        result = dispatch_portal_emails(limit=1)
        send.assert_called_once_with()
        self.assertEqual(result.failed, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, OnboardingPortalDelivery.Status.RETRY)
        self.candidate_a.refresh_from_db()
        self.assertFalse(self.candidate_a.start_onboard)
        self.assertFalse(CandidateStage.objects.filter(candidate_id=self.candidate_a).exists())
        self.assertFalse(CandidateTask.objects.filter(candidate_id=self.candidate_a).exists())

    @patch("hydra_arrivals.portal_email.EmailMessage.send", return_value=1)
    def test_successful_portal_email_starts_stage_and_configured_tasks(self, send):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("email-send"),
            {"ids": [str(self.candidate_a.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        send.assert_not_called()
        result = dispatch_portal_emails(limit=1)
        send.assert_called_once_with()
        self.assertEqual(result.sent, 1)
        self.candidate_a.refresh_from_db()
        self.assertTrue(self.candidate_a.start_onboard)
        stage = CandidateStage.objects.get(candidate_id=self.candidate_a)
        self.assertEqual(stage.onboarding_stage_id, self.onboarding_stage)
        task = CandidateTask.objects.get(candidate_id=self.candidate_a)
        self.assertEqual(task.onboarding_task_id, self.onboarding_task)
        self.assertEqual(task.stage_id, self.onboarding_stage)
