"""
Factory Boy factories for offboarding module models.

Usage:
    offboarding = OffboardingFactory()
    stage = OffboardingStageFactory(offboarding_id=offboarding)
    task = OffboardingTaskFactory(stage_id=stage)
    emp = OffboardingEmployeeFactory(stage_id=stage)
    resignation = ResignationLetterFactory()
"""

import factory
from factory.django import DjangoModelFactory

from base.tests.factories import CompanyFactory
from employee.tests.factories import EmployeeFactory
from offboarding.models import (
    EmployeeTask,
    ExitReason,
    Offboarding,
    OffboardingEmployee,
    OffboardingNote,
    OffboardingStage,
    OffboardingTask,
    ResignationLetter,
)


class OffboardingFactory(DjangoModelFactory):
    """
    Creates an Offboarding instance.

    NOTE: Offboarding.save() auto-creates 5 default stages on first save:
    Exit interview, Work Handover, FNF, Farewell, Archived.
    PLUS post_save signal creates a 6th "Notice Period" stage.
    """

    class Meta:
        model = Offboarding

    title = factory.Sequence(lambda n: f"Offboarding {n}")
    description = "Test offboarding description"
    status = "ongoing"
    company_id = factory.SubFactory(CompanyFactory)

    @factory.post_generation
    def managers(self, create, extracted, **kwargs):
        """Add managers (M2M)."""
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.managers.add(emp)


class OffboardingStageFactory(DjangoModelFactory):
    """
    Creates an OffboardingStage linked to an Offboarding.

    NOTE: OffboardingStage is also auto-created by Offboarding.save().
    Use this factory for creating ADDITIONAL custom stages.
    """

    class Meta:
        model = OffboardingStage

    title = factory.Sequence(lambda n: f"Custom Stage {n}")
    type = "other"
    offboarding_id = factory.SubFactory(OffboardingFactory)
    sequence = factory.Sequence(lambda n: n + 10)

    @factory.post_generation
    def managers(self, create, extracted, **kwargs):
        """Add stage managers (M2M)."""
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.managers.add(emp)


class OffboardingTaskFactory(DjangoModelFactory):
    """
    Creates an OffboardingTask linked to an OffboardingStage.

    NOTE: unique_together = ["title", "stage_id"]
    """

    class Meta:
        model = OffboardingTask

    title = factory.Sequence(lambda n: f"Task {n}")
    stage_id = factory.SubFactory(OffboardingStageFactory)

    @factory.post_generation
    def managers(self, create, extracted, **kwargs):
        """Add task managers (M2M)."""
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.managers.add(emp)


class OffboardingEmployeeFactory(DjangoModelFactory):
    """
    Creates an OffboardingEmployee linking an Employee to a stage.

    NOTE: employee_id is OneToOneField — each employee can appear once.
    """

    class Meta:
        model = OffboardingEmployee

    employee_id = factory.SubFactory(EmployeeFactory)
    stage_id = factory.SubFactory(OffboardingStageFactory)
    notice_period = 30
    unit = "day"
    notice_period_starts = factory.Faker("date_this_year")
    notice_period_ends = factory.Faker("future_date")


class ResignationLetterFactory(DjangoModelFactory):
    """
    Creates a ResignationLetter for an Employee.

    Status choices: requested, approved, rejected.
    """

    class Meta:
        model = ResignationLetter

    employee_id = factory.SubFactory(EmployeeFactory)
    title = factory.Sequence(lambda n: f"Resignation {n}")
    description = "I am resigning for personal reasons."
    planned_to_leave_on = factory.Faker("future_date")
    status = "requested"


class EmployeeTaskFactory(DjangoModelFactory):
    """
    Creates an EmployeeTask linking an OffboardingEmployee to an OffboardingTask.

    NOTE: unique_together = ["employee_id", "task_id"]
    NOTE: save() sends a notification via django-notifications, which
    requires _thread_locals.request to have a user with employee_get.
    """

    class Meta:
        model = EmployeeTask

    employee_id = factory.SubFactory(OffboardingEmployeeFactory)
    task_id = factory.SubFactory(OffboardingTaskFactory)
    status = "todo"


class ExitReasonFactory(DjangoModelFactory):
    """
    Creates an ExitReason for an OffboardingEmployee.
    """

    class Meta:
        model = ExitReason

    title = factory.Sequence(lambda n: f"Exit Reason {n}")
    description = "Leaving for a new opportunity"
    offboarding_employee_id = factory.SubFactory(OffboardingEmployeeFactory)
