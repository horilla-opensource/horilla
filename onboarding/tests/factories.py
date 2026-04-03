"""
Factory Boy factories for onboarding module models.

Usage:
    stage = OnboardingStageFactory()
    task = OnboardingTaskFactory(stage_id=stage)
    cand_stage = CandidateStageFactory(onboarding_stage_id=stage)
    cand_task = CandidateTaskFactory(
        candidate_id=cand_stage.candidate_id,
        stage_id=stage,
        onboarding_task_id=task,
    )
    portal = OnboardingPortalFactory()
"""

import factory
from factory.django import DjangoModelFactory

from employee.tests.factories import EmployeeFactory
from onboarding.models import (
    CandidateStage,
    CandidateTask,
    OnboardingPortal,
    OnboardingStage,
    OnboardingTask,
)
from recruitment.tests.factories import CandidateFactory, RecruitmentFactory


class OnboardingStageFactory(DjangoModelFactory):
    """
    Creates an OnboardingStage linked to a Recruitment.

    NOTE: Recruitment.post_save signal auto-creates an "Initial" stage.
    This factory creates an ADDITIONAL stage for the recruitment.
    """

    class Meta:
        model = OnboardingStage

    stage_title = factory.Sequence(lambda n: f"Onboarding Stage {n}")
    recruitment_id = factory.SubFactory(RecruitmentFactory)
    sequence = factory.Sequence(lambda n: n + 1)
    is_final_stage = False

    @factory.post_generation
    def employee_id(self, create, extracted, **kwargs):
        """Add stage managers (M2M)."""
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.employee_id.add(emp)


class OnboardingTaskFactory(DjangoModelFactory):
    """
    Creates an OnboardingTask linked to an OnboardingStage.
    """

    class Meta:
        model = OnboardingTask

    task_title = factory.Sequence(lambda n: f"Onboarding Task {n}")
    stage_id = factory.SubFactory(OnboardingStageFactory)

    @factory.post_generation
    def employee_id(self, create, extracted, **kwargs):
        """Add task managers (M2M)."""
        if not create:
            return
        if extracted:
            for emp in extracted:
                self.employee_id.add(emp)

    @factory.post_generation
    def candidates(self, create, extracted, **kwargs):
        """Add candidates to task (M2M)."""
        if not create:
            return
        if extracted:
            for cand in extracted:
                self.candidates.add(cand)


class CandidateStageFactory(DjangoModelFactory):
    """
    Creates a CandidateStage linking a Candidate to an OnboardingStage.

    NOTE: candidate_id is OneToOneField, so each candidate can only have
    one CandidateStage. CandidateStage.save() sets onboarding_end_date
    automatically when the stage is_final_stage.
    """

    class Meta:
        model = CandidateStage

    candidate_id = factory.SubFactory(CandidateFactory)
    onboarding_stage_id = factory.SubFactory(OnboardingStageFactory)
    sequence = 0


class CandidateTaskFactory(DjangoModelFactory):
    """
    Creates a CandidateTask linking a Candidate to an OnboardingTask.

    Status choices: todo, scheduled, ongoing, stuck, done.
    """

    class Meta:
        model = CandidateTask

    candidate_id = factory.SubFactory(CandidateFactory)
    stage_id = factory.SubFactory(OnboardingStageFactory)
    status = "todo"
    onboarding_task_id = factory.SubFactory(OnboardingTaskFactory)


class OnboardingPortalFactory(DjangoModelFactory):
    """
    Creates an OnboardingPortal for a Candidate.

    NOTE: candidate_id is OneToOneField — each candidate gets one portal.
    """

    class Meta:
        model = OnboardingPortal

    candidate_id = factory.SubFactory(CandidateFactory)
    token = factory.Sequence(lambda n: f"token-{n:032x}")
    used = False
    count = 0
