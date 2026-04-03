"""
Model tests for the offboarding module.

Tests cover CRUD operations, field behavior, ordering, __str__,
auto-stage creation, and business logic for Offboarding,
OffboardingStage, OffboardingTask, OffboardingEmployee,
EmployeeTask, and ResignationLetter.
"""

from datetime import date

from django.db import IntegrityError

from horilla.test_utils.base import HorillaTestCase
from offboarding.models import (
    EmployeeTask,
    Offboarding,
    OffboardingEmployee,
    OffboardingStage,
    OffboardingTask,
    ResignationLetter,
)
from offboarding.tests.factories import (
    EmployeeTaskFactory,
    OffboardingEmployeeFactory,
    OffboardingFactory,
    OffboardingStageFactory,
    OffboardingTaskFactory,
    ResignationLetterFactory,
)


class OffboardingTests(HorillaTestCase):
    """Tests for the Offboarding model."""

    def test_create_offboarding(self):
        """An Offboarding instance can be created."""
        ob = OffboardingFactory(title="Q1 Offboarding")
        self.assertEqual(ob.title, "Q1 Offboarding")
        self.assertIsNotNone(ob.pk)

    def test_str_representation(self):
        """__str__ returns the offboarding title."""
        ob = OffboardingFactory(title="Year End")
        self.assertEqual(str(ob), "Year End")

    def test_default_status_ongoing(self):
        """Default status is 'ongoing'."""
        ob = OffboardingFactory()
        self.assertEqual(ob.status, "ongoing")

    def test_auto_created_stages_on_save(self):
        """Creating an Offboarding auto-creates 6 stages (5 from save + 1 from signal)."""
        ob = OffboardingFactory()
        stages = OffboardingStage.objects.filter(offboarding_id=ob)
        # Offboarding.save() creates: Exit interview, Work Handover, FNF, Farewell, Archived
        # post_save signal creates: Notice Period
        self.assertEqual(stages.count(), 6)

    def test_auto_created_stage_types(self):
        """Auto-created stages include the expected types."""
        ob = OffboardingFactory()
        types = set(
            OffboardingStage.objects.filter(offboarding_id=ob).values_list(
                "type", flat=True
            )
        )
        expected = {
            "interview",
            "handover",
            "fnf",
            "other",
            "archived",
            "notice_period",
        }
        self.assertEqual(types, expected)

    def test_update_status(self):
        """Offboarding status can be updated."""
        ob = OffboardingFactory()
        ob.status = "completed"
        ob.save()
        ob.refresh_from_db()
        self.assertEqual(ob.status, "completed")

    def test_delete_offboarding(self):
        """Deleting an offboarding cascades to its stages."""
        ob = OffboardingFactory()
        pk = ob.pk
        stage_count_before = OffboardingStage.objects.filter(
            offboarding_id__pk=pk
        ).count()
        self.assertGreater(stage_count_before, 0)
        ob.delete()
        self.assertFalse(Offboarding.objects.filter(pk=pk).exists())
        self.assertEqual(
            OffboardingStage.objects.filter(offboarding_id__pk=pk).count(), 0
        )

    def test_managers_m2m(self):
        """Managers can be assigned to an offboarding."""
        ob = OffboardingFactory(managers=[self.admin_employee, self.manager_employee])
        self.assertEqual(ob.managers.count(), 2)


class OffboardingStageTests(HorillaTestCase):
    """Tests for the OffboardingStage model."""

    def test_create_stage(self):
        """An OffboardingStage can be created."""
        stage = OffboardingStageFactory(title="Review Stage")
        self.assertEqual(stage.title, "Review Stage")
        self.assertIsNotNone(stage.pk)

    def test_str_representation(self):
        """__str__ returns the stage title."""
        stage = OffboardingStageFactory(title="Handover")
        self.assertEqual(str(stage), "Handover")

    def test_is_archived_stage(self):
        """is_archived_stage() returns True for type='archived'."""
        stage = OffboardingStageFactory(type="archived")
        self.assertTrue(stage.is_archived_stage())

    def test_is_not_archived_stage(self):
        """is_archived_stage() returns False for non-archived types."""
        stage = OffboardingStageFactory(type="interview")
        self.assertFalse(stage.is_archived_stage())

    def test_stage_types_valid(self):
        """All defined type choices can be set."""
        valid_types = [t[0] for t in OffboardingStage.types]
        for type_val in valid_types:
            stage = OffboardingStageFactory(type=type_val)
            self.assertEqual(stage.type, type_val)

    def test_stage_managers_m2m(self):
        """Stage managers can be assigned."""
        stage = OffboardingStageFactory(managers=[self.manager_employee])
        self.assertEqual(stage.managers.count(), 1)
        self.assertIn(self.manager_employee, stage.managers.all())


class OffboardingTaskTests(HorillaTestCase):
    """Tests for the OffboardingTask model."""

    def test_create_task(self):
        """An OffboardingTask can be created."""
        task = OffboardingTaskFactory(title="Return Laptop")
        self.assertEqual(task.title, "Return Laptop")
        self.assertIsNotNone(task.pk)

    def test_str_representation(self):
        """__str__ returns the task title."""
        task = OffboardingTaskFactory(title="Clear Desk")
        self.assertEqual(str(task), "Clear Desk")

    def test_unique_together_title_stage(self):
        """Same title + stage combination raises IntegrityError."""
        stage = OffboardingStageFactory()
        OffboardingTaskFactory(title="Submit Report", stage_id=stage)
        with self.assertRaises(IntegrityError):
            OffboardingTaskFactory(title="Submit Report", stage_id=stage)

    def test_task_managers_m2m(self):
        """Managers can be assigned to a task."""
        task = OffboardingTaskFactory(managers=[self.admin_employee])
        self.assertEqual(task.managers.count(), 1)

    def test_delete_task(self):
        """Task can be deleted."""
        task = OffboardingTaskFactory()
        pk = task.pk
        task.delete()
        self.assertFalse(OffboardingTask.objects.filter(pk=pk).exists())


class OffboardingEmployeeTests(HorillaTestCase):
    """Tests for the OffboardingEmployee model."""

    def test_create_offboarding_employee(self):
        """An OffboardingEmployee can be created."""
        oe = OffboardingEmployeeFactory()
        self.assertIsNotNone(oe.pk)

    def test_str_representation(self):
        """__str__ returns the employee's full name."""
        oe = OffboardingEmployeeFactory()
        self.assertEqual(str(oe), oe.employee_id.get_full_name())

    def test_one_to_one_constraint(self):
        """Each employee can only have one offboarding record (OneToOne)."""
        from employee.tests.factories import EmployeeFactory

        emp = EmployeeFactory()
        OffboardingEmployeeFactory(employee_id=emp)
        with self.assertRaises(IntegrityError):
            OffboardingEmployeeFactory(employee_id=emp)

    def test_notice_period_fields(self):
        """Notice period fields store correctly."""
        start = date(2026, 4, 1)
        end = date(2026, 4, 30)
        oe = OffboardingEmployeeFactory(
            notice_period=30,
            unit="day",
            notice_period_starts=start,
            notice_period_ends=end,
        )
        oe.refresh_from_db()
        self.assertEqual(oe.notice_period, 30)
        self.assertEqual(oe.unit, "day")
        self.assertEqual(oe.notice_period_starts, start)
        self.assertEqual(oe.notice_period_ends, end)

    def test_unit_choices(self):
        """Unit field accepts valid choices."""
        oe = OffboardingEmployeeFactory(unit="month")
        self.assertEqual(oe.unit, "month")
        oe.unit = "day"
        oe.save()
        oe.refresh_from_db()
        self.assertEqual(oe.unit, "day")

    def test_stage_progression(self):
        """Employee can be moved to a different stage."""
        ob = OffboardingFactory()
        stages = list(OffboardingStage.objects.filter(offboarding_id=ob).order_by("pk"))
        oe = OffboardingEmployeeFactory(stage_id=stages[0])
        self.assertEqual(oe.stage_id, stages[0])
        oe.stage_id = stages[1]
        oe.save()
        oe.refresh_from_db()
        self.assertEqual(oe.stage_id, stages[1])

    def test_get_notice_period_col_ended(self):
        """get_notice_period_col returns ended message for past dates."""
        past_date = date(2020, 1, 1)
        oe = OffboardingEmployeeFactory(notice_period_ends=past_date)
        col = oe.get_notice_period_col()
        # The method returns "Notice period ended" for past dates
        self.assertIn("ended", str(col).lower())

    def test_get_notice_period_col_none(self):
        """get_notice_period_col returns empty string when no end date."""
        oe = OffboardingEmployeeFactory(notice_period_ends=None)
        col = oe.get_notice_period_col()
        self.assertEqual(col, "")


class EmployeeTaskTests(HorillaTestCase):
    """Tests for the EmployeeTask model."""

    def test_create_employee_task(self):
        """An EmployeeTask can be created with default status."""
        et = EmployeeTaskFactory()
        self.assertIsNotNone(et.pk)
        self.assertEqual(et.status, "todo")

    def test_status_choices(self):
        """All status choices are valid."""
        et = EmployeeTaskFactory()
        for status_val, _ in EmployeeTask.statuses:
            et.status = status_val
            et.save()
            et.refresh_from_db()
            self.assertEqual(et.status, status_val)

    def test_unique_together_employee_task(self):
        """Same employee + task combination raises IntegrityError."""
        oe = OffboardingEmployeeFactory()
        task = OffboardingTaskFactory()
        EmployeeTaskFactory(employee_id=oe, task_id=task)
        with self.assertRaises(IntegrityError):
            EmployeeTaskFactory(employee_id=oe, task_id=task)


class ResignationLetterTests(HorillaTestCase):
    """Tests for the ResignationLetter model."""

    def test_create_resignation(self):
        """A ResignationLetter can be created."""
        rl = ResignationLetterFactory()
        self.assertIsNotNone(rl.pk)
        self.assertEqual(rl.status, "requested")

    def test_status_choices(self):
        """All defined status choices can be set."""
        rl = ResignationLetterFactory()
        for status_val, _ in ResignationLetter.statuses:
            rl.status = status_val
            rl.save()
            rl.refresh_from_db()
            self.assertEqual(rl.status, status_val)

    def test_get_status_display(self):
        """get_status() returns the human-readable status label."""
        rl = ResignationLetterFactory(status="approved")
        # get_status() uses dict lookup on statuses
        self.assertEqual(str(rl.get_status()), "Approved")

    def test_planned_leave_date(self):
        """planned_to_leave_on stores the date correctly."""
        leave_date = date(2026, 6, 15)
        rl = ResignationLetterFactory(planned_to_leave_on=leave_date)
        rl.refresh_from_db()
        self.assertEqual(rl.planned_to_leave_on, leave_date)

    def test_update_to_rejected(self):
        """Resignation can be updated to rejected."""
        rl = ResignationLetterFactory(status="requested")
        rl.status = "rejected"
        rl.save()
        rl.refresh_from_db()
        self.assertEqual(rl.status, "rejected")

    def test_delete_resignation(self):
        """ResignationLetter can be deleted."""
        rl = ResignationLetterFactory()
        pk = rl.pk
        rl.delete()
        self.assertFalse(ResignationLetter.objects.entire().filter(pk=pk).exists())
