"""
Model tests for the onboarding module.

Tests cover CRUD operations, field behavior, ordering, __str__,
and business logic for OnboardingStage, OnboardingTask,
CandidateStage, CandidateTask, and OnboardingPortal.
"""

from datetime import datetime

from django.db import IntegrityError

from horilla.test_utils.base import HorillaTestCase
from onboarding.models import (
    CandidateStage,
    CandidateTask,
    OnboardingPortal,
    OnboardingStage,
    OnboardingTask,
)
from onboarding.tests.factories import (
    CandidateStageFactory,
    CandidateTaskFactory,
    OnboardingPortalFactory,
    OnboardingStageFactory,
    OnboardingTaskFactory,
)
from recruitment.tests.factories import CandidateFactory, RecruitmentFactory


class OnboardingStageTests(HorillaTestCase):
    """Tests for OnboardingStage model."""

    def test_create_stage(self):
        """An onboarding stage can be created with valid data."""
        stage = OnboardingStageFactory(stage_title="Document Collection")
        self.assertEqual(stage.stage_title, "Document Collection")
        self.assertIsNotNone(stage.pk)

    def test_str_representation(self):
        """__str__ returns the stage title."""
        stage = OnboardingStageFactory(stage_title="IT Setup")
        self.assertEqual(str(stage), "IT Setup")

    def test_sequence_ordering(self):
        """Stages are ordered by sequence (Meta.ordering)."""
        rec = RecruitmentFactory()
        # The post_save signal creates an "Initial" stage with sequence=0.
        stage_b = OnboardingStageFactory(
            recruitment_id=rec, stage_title="Second", sequence=2
        )
        stage_a = OnboardingStageFactory(
            recruitment_id=rec, stage_title="First", sequence=1
        )
        stages = list(
            OnboardingStage.objects.entire()
            .filter(recruitment_id=rec)
            .exclude(stage_title="Initial")
            .values_list("stage_title", flat=True)
        )
        self.assertEqual(stages, ["First", "Second"])

    def test_is_final_stage_default_false(self):
        """is_final_stage defaults to False."""
        stage = OnboardingStageFactory()
        self.assertFalse(stage.is_final_stage)

    def test_update_stage_title(self):
        """Stage title can be updated."""
        stage = OnboardingStageFactory(stage_title="Old Title")
        stage.stage_title = "New Title"
        stage.save()
        stage.refresh_from_db()
        self.assertEqual(stage.stage_title, "New Title")

    def test_delete_stage(self):
        """Stage can be deleted."""
        stage = OnboardingStageFactory()
        pk = stage.pk
        stage.delete()
        self.assertFalse(OnboardingStage.objects.entire().filter(pk=pk).exists())

    def test_initial_stage_auto_created_on_recruitment(self):
        """Creating a Recruitment auto-creates an 'Initial' OnboardingStage."""
        rec = RecruitmentFactory()
        initial = OnboardingStage.objects.entire().filter(
            recruitment_id=rec, stage_title="Initial"
        )
        self.assertTrue(initial.exists())
        self.assertEqual(initial.first().sequence, 0)

    def test_stage_managers_m2m(self):
        """Stage managers (M2M to Employee) can be added."""
        stage = OnboardingStageFactory(
            employee_id=[self.admin_employee, self.manager_employee]
        )
        self.assertEqual(stage.employee_id.count(), 2)
        self.assertIn(self.admin_employee, stage.employee_id.all())


class OnboardingTaskTests(HorillaTestCase):
    """Tests for OnboardingTask model."""

    def test_create_task(self):
        """An onboarding task can be created with valid data."""
        task = OnboardingTaskFactory(task_title="Sign NDA")
        self.assertEqual(task.task_title, "Sign NDA")
        self.assertIsNotNone(task.pk)

    def test_str_representation(self):
        """__str__ returns the task title."""
        task = OnboardingTaskFactory(task_title="Background Check")
        self.assertEqual(str(task), "Background Check")

    def test_task_linked_to_stage(self):
        """Task has a FK to its parent stage."""
        stage = OnboardingStageFactory(stage_title="Orientation")
        task = OnboardingTaskFactory(stage_id=stage)
        self.assertEqual(task.stage_id, stage)

    def test_task_managers_m2m(self):
        """Task managers (M2M to Employee) can be added."""
        task = OnboardingTaskFactory(employee_id=[self.manager_employee])
        self.assertEqual(task.employee_id.count(), 1)
        self.assertIn(self.manager_employee, task.employee_id.all())

    def test_task_candidates_m2m(self):
        """Candidates can be assigned to a task."""
        cand = CandidateFactory()
        task = OnboardingTaskFactory(candidates=[cand])
        self.assertEqual(task.candidates.count(), 1)
        self.assertIn(cand, task.candidates.all())

    def test_delete_task(self):
        """Task can be deleted."""
        task = OnboardingTaskFactory()
        pk = task.pk
        task.delete()
        self.assertFalse(OnboardingTask.objects.entire().filter(pk=pk).exists())

    def test_cascade_delete_with_stage(self):
        """Deleting a stage cascades to its tasks."""
        stage = OnboardingStageFactory()
        task = OnboardingTaskFactory(stage_id=stage)
        stage.delete()
        self.assertFalse(OnboardingTask.objects.entire().filter(pk=task.pk).exists())


class CandidateStageTests(HorillaTestCase):
    """Tests for CandidateStage model."""

    def test_create_candidate_stage(self):
        """A CandidateStage can be created."""
        cs = CandidateStageFactory()
        self.assertIsNotNone(cs.pk)

    def test_str_representation(self):
        """__str__ returns 'candidate | stage' format."""
        cs = CandidateStageFactory()
        expected = f"{cs.candidate_id}  |  {cs.onboarding_stage_id}"
        self.assertEqual(str(cs), expected)

    def test_one_to_one_constraint(self):
        """Each candidate can only be in one onboarding stage (OneToOne)."""
        cand = CandidateFactory()
        CandidateStageFactory(candidate_id=cand)
        with self.assertRaises(IntegrityError):
            CandidateStageFactory(candidate_id=cand)

    def test_final_stage_sets_end_date(self):
        """Saving to a final stage auto-sets onboarding_end_date to today."""
        stage = OnboardingStageFactory(is_final_stage=True)
        cs = CandidateStageFactory(onboarding_stage_id=stage)
        # Model sets onboarding_end_date = datetime.today() (a datetime, not date).
        # Refresh from DB to get the DateField-coerced date value.
        cs.refresh_from_db()
        self.assertEqual(cs.onboarding_end_date, datetime.today().date())

    def test_non_final_stage_no_end_date(self):
        """Non-final stage does not set onboarding_end_date."""
        stage = OnboardingStageFactory(is_final_stage=False)
        cs = CandidateStageFactory(onboarding_stage_id=stage)
        self.assertIsNone(cs.onboarding_end_date)

    def test_sequence_ordering(self):
        """CandidateStage records are ordered by sequence."""
        rec = RecruitmentFactory()
        stage = OnboardingStageFactory(recruitment_id=rec)
        cand1 = CandidateFactory(recruitment_id=rec)
        cand2 = CandidateFactory(recruitment_id=rec)
        cs_b = CandidateStageFactory(
            candidate_id=cand1, onboarding_stage_id=stage, sequence=2
        )
        cs_a = CandidateStageFactory(
            candidate_id=cand2, onboarding_stage_id=stage, sequence=1
        )
        pks = list(
            CandidateStage.objects.entire()
            .filter(onboarding_stage_id=stage)
            .values_list("pk", flat=True)
        )
        self.assertEqual(pks, [cs_a.pk, cs_b.pk])


class CandidateTaskTests(HorillaTestCase):
    """Tests for CandidateTask model."""

    def test_create_candidate_task(self):
        """A CandidateTask can be created with default status."""
        ct = CandidateTaskFactory()
        self.assertIsNotNone(ct.pk)
        self.assertEqual(ct.status, "todo")

    def test_str_representation(self):
        """__str__ returns 'candidate|task' format."""
        ct = CandidateTaskFactory()
        expected = f"{ct.candidate_id}|{ct.onboarding_task_id}"
        self.assertEqual(str(ct), expected)

    def test_status_choices(self):
        """All defined status choices can be set."""
        ct = CandidateTaskFactory()
        for status_value, _ in CandidateTask.choice:
            ct.status = status_value
            ct.save()
            ct.refresh_from_db()
            self.assertEqual(ct.status, status_value)

    def test_mark_task_done(self):
        """Task status can be updated to 'done'."""
        ct = CandidateTaskFactory(status="todo")
        ct.status = "done"
        ct.save()
        ct.refresh_from_db()
        self.assertEqual(ct.status, "done")

    def test_task_linked_to_stage_and_candidate(self):
        """CandidateTask is linked to both a candidate and a stage."""
        stage = OnboardingStageFactory()
        cand = CandidateFactory()
        task = OnboardingTaskFactory(stage_id=stage)
        ct = CandidateTaskFactory(
            candidate_id=cand,
            stage_id=stage,
            onboarding_task_id=task,
        )
        self.assertEqual(ct.candidate_id, cand)
        self.assertEqual(ct.stage_id, stage)
        self.assertEqual(ct.onboarding_task_id, task)

    def test_protect_on_candidate_delete(self):
        """Deleting a candidate with tasks raises ProtectedError."""
        from django.db.models import ProtectedError

        ct = CandidateTaskFactory()
        with self.assertRaises(ProtectedError):
            ct.candidate_id.delete()


class OnboardingPortalTests(HorillaTestCase):
    """Tests for OnboardingPortal model."""

    def test_create_portal(self):
        """An OnboardingPortal can be created."""
        portal = OnboardingPortalFactory()
        self.assertIsNotNone(portal.pk)
        self.assertFalse(portal.used)
        self.assertEqual(portal.count, 0)

    def test_str_representation(self):
        """__str__ returns 'candidate | token' format."""
        portal = OnboardingPortalFactory()
        expected = f"{portal.candidate_id} | {portal.token}"
        self.assertEqual(str(portal), expected)

    def test_one_to_one_constraint(self):
        """Each candidate can only have one portal (OneToOne)."""
        cand = CandidateFactory()
        OnboardingPortalFactory(candidate_id=cand)
        with self.assertRaises(IntegrityError):
            OnboardingPortalFactory(candidate_id=cand)

    def test_mark_portal_used(self):
        """Portal can be marked as used."""
        portal = OnboardingPortalFactory()
        portal.used = True
        portal.count = 1
        portal.save()
        portal.refresh_from_db()
        self.assertTrue(portal.used)
        self.assertEqual(portal.count, 1)
