"""
Factory Boy factories for recruitment module models.

Usage:
    rec = RecruitmentFactory()                          # basic recruitment
    stage = StageFactory(recruitment_id=rec)             # stage linked to recruitment
    cand = CandidateFactory(recruitment_id=rec, stage_id=stage)
    sz = SkillZoneFactory()
"""

import factory
from factory.django import DjangoModelFactory

from base.tests.factories import CompanyFactory, JobPositionFactory
from recruitment.models import (
    Candidate,
    Recruitment,
    RecruitmentSurvey,
    RejectedCandidate,
    RejectReason,
    SkillZone,
    SkillZoneCandidate,
    Stage,
    SurveyTemplate,
)


class SurveyTemplateFactory(DjangoModelFactory):
    class Meta:
        model = SurveyTemplate

    title = factory.Sequence(lambda n: f"Survey Template {n}")
    description = "Default survey template description"
    company_id = factory.SubFactory(CompanyFactory)


class RecruitmentFactory(DjangoModelFactory):
    class Meta:
        model = Recruitment

    title = factory.Sequence(lambda n: f"Recruitment {n}")
    description = "Test recruitment description"
    is_published = False  # avoids vacancy > 0 validation
    vacancy = 5
    closed = False
    company_id = factory.SubFactory(CompanyFactory)
    start_date = factory.Faker("date_this_year")

    @factory.post_generation
    def recruitment_managers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for manager in extracted:
                self.recruitment_managers.add(manager)

    @factory.post_generation
    def open_positions(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for pos in extracted:
                self.open_positions.add(pos)


class StageFactory(DjangoModelFactory):
    class Meta:
        model = Stage

    stage = factory.Sequence(lambda n: f"Stage {n}")
    recruitment_id = factory.SubFactory(RecruitmentFactory)
    stage_type = "initial"
    sequence = factory.Sequence(lambda n: n)


class CandidateFactory(DjangoModelFactory):
    """
    Creates a Candidate linked to a Recruitment and Stage.

    NOTE: Candidate.save() has complex logic:
    - Sets hired=True when stage_type == "hired"
    - Auto-assigns job_position_id from recruitment if not event-based
    - Validates job_position_id is in recruitment.open_positions
    - Creates cancelled stage if canceled=True

    The factory sets up the required Recruitment -> JobPosition -> open_positions
    chain so save() validation passes.
    """

    class Meta:
        model = Candidate

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"candidate.{n}@test.com")
    gender = "male"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Override _create to wire up recruitment -> job_position -> open_positions
        before calling save(), since Candidate.save() validates that
        job_position_id is in recruitment_id.open_positions.
        """
        recruitment_id = kwargs.get("recruitment_id")
        stage_id = kwargs.get("stage_id")

        # Create recruitment if not provided
        if recruitment_id is None:
            job_pos = JobPositionFactory()
            recruitment_id = RecruitmentFactory(
                job_position_id=job_pos,
            )
            recruitment_id.open_positions.add(job_pos)
            kwargs["recruitment_id"] = recruitment_id

        # Ensure the recruitment has a job_position and open_positions wired up.
        # Candidate.save() validates job_position_id is in open_positions.
        if not recruitment_id.is_event_based:
            if recruitment_id.job_position_id is None:
                job_pos = JobPositionFactory()
                recruitment_id.job_position_id = job_pos
                recruitment_id.save()
                recruitment_id.open_positions.add(job_pos)
            else:
                recruitment_id.open_positions.add(recruitment_id.job_position_id)

        # Create stage if not provided -- reuse an existing stage from the
        # recruitment (post_save signal auto-creates "Applied" and "Initial").
        if stage_id is None:
            from recruitment.models import Stage

            existing = Stage.objects.filter(recruitment_id=recruitment_id).first()
            if existing:
                stage_id = existing
            else:
                stage_id = StageFactory(recruitment_id=recruitment_id)
            kwargs["stage_id"] = stage_id

        return super()._create(model_class, *args, **kwargs)


class RejectReasonFactory(DjangoModelFactory):
    class Meta:
        model = RejectReason

    title = factory.Sequence(lambda n: f"Reject Reason {n}")
    description = "Default rejection reason"
    company_id = factory.SubFactory(CompanyFactory)


class RejectedCandidateFactory(DjangoModelFactory):
    """
    Creates a RejectedCandidate linked to a Candidate.

    NOTE: reject_reason_id is a M2M field — use post_generation
    to add reasons after creation.
    """

    class Meta:
        model = RejectedCandidate

    candidate_id = factory.SubFactory(CandidateFactory)
    description = "Candidate rejected for testing purposes"

    @factory.post_generation
    def reject_reason_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for reason in extracted:
                self.reject_reason_id.add(reason)


class SkillZoneFactory(DjangoModelFactory):
    class Meta:
        model = SkillZone

    title = factory.Sequence(lambda n: f"Skill Zone {n}")
    description = "Test skill zone description"
    company_id = factory.SubFactory(CompanyFactory)


class SkillZoneCandidateFactory(DjangoModelFactory):
    class Meta:
        model = SkillZoneCandidate

    skill_zone_id = factory.SubFactory(SkillZoneFactory)
    candidate_id = factory.SubFactory(CandidateFactory)
    reason = "Promising candidate for future openings"


class RecruitmentSurveyFactory(DjangoModelFactory):
    """
    Creates a RecruitmentSurvey question.

    NOTE: recruitment_ids is M2M — use post_generation to link recruitments.
    """

    class Meta:
        model = RecruitmentSurvey

    question = factory.Sequence(lambda n: f"Survey question {n}?")
    type = "text"
    sequence = factory.Sequence(lambda n: n)
    options = ""

    @factory.post_generation
    def recruitment_ids(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for rec in extracted:
                self.recruitment_ids.add(rec)
