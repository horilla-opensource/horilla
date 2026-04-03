"""
Model tests for the recruitment module.

Tests cover: Recruitment, Stage, Candidate, SkillZone, RejectReason,
RejectedCandidate, and RecruitmentSurvey models.
"""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from base.tests.factories import CompanyFactory, JobPositionFactory
from employee.tests.factories import EmployeeFactory
from horilla.test_utils.base import HorillaTestCase
from recruitment.models import (
    Candidate,
    Recruitment,
    RecruitmentSurvey,
    RejectedCandidate,
    RejectReason,
    SkillZone,
    SkillZoneCandidate,
    Stage,
)
from recruitment.tests.factories import (
    CandidateFactory,
    RecruitmentFactory,
    RecruitmentSurveyFactory,
    RejectedCandidateFactory,
    RejectReasonFactory,
    SkillZoneCandidateFactory,
    SkillZoneFactory,
    StageFactory,
)


# ---------------------------------------------------------------------------
# Recruitment model tests
# ---------------------------------------------------------------------------
class RecruitmentModelTest(HorillaTestCase):
    """Tests for the Recruitment model."""

    def test_create_recruitment(self):
        """A recruitment can be created with minimal required fields."""
        rec = RecruitmentFactory()
        self.assertIsNotNone(rec.pk)
        self.assertFalse(rec.closed)

    def test_str_with_title(self):
        """__str__ returns the title when set."""
        rec = RecruitmentFactory(title="Backend Engineer Q3")
        self.assertEqual(str(rec), "Backend Engineer Q3")

    def test_str_without_title_falls_back_to_job_position(self):
        """__str__ returns job_position + start_date when title is None."""
        job_pos = JobPositionFactory(job_position="Data Analyst")
        rec = RecruitmentFactory(
            title=None,
            job_position_id=job_pos,
        )
        rec.open_positions.add(job_pos)
        # Should contain the job position name
        self.assertIn("Data Analyst", str(rec))

    def test_is_active_default(self):
        """Recruitment is_active defaults to True (from HorillaModel)."""
        rec = RecruitmentFactory()
        self.assertTrue(rec.is_active)

    def test_company_fk(self):
        """Recruitment stores company FK correctly."""
        company = CompanyFactory(company="Acme Corp")
        rec = RecruitmentFactory(company_id=company)
        self.assertEqual(rec.company_id, company)

    def test_recruitment_managers_m2m(self):
        """Managers can be added via M2M."""
        rec = RecruitmentFactory()
        mgr = self.manager_employee
        rec.recruitment_managers.add(mgr)
        self.assertIn(mgr, rec.recruitment_managers.all())

    def test_closed_field(self):
        """Recruitment can be closed."""
        rec = RecruitmentFactory(closed=True)
        self.assertTrue(rec.closed)

    def test_vacancy_count(self):
        """Vacancy stores the integer count."""
        rec = RecruitmentFactory(vacancy=10)
        self.assertEqual(rec.vacancy, 10)

    def test_clean_requires_title(self):
        """clean() raises ValidationError when title is None."""
        rec = RecruitmentFactory.build(title=None)
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_clean_published_requires_positive_vacancy(self):
        """clean() rejects is_published=True with vacancy <= 0."""
        rec = RecruitmentFactory.build(is_published=True, vacancy=0)
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_clean_end_date_before_start_date(self):
        """clean() raises error when end_date < start_date."""
        today = date.today()
        rec = RecruitmentFactory.build(
            title="Test",
            start_date=today,
            end_date=today - timedelta(days=5),
            is_published=False,
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_total_hires_zero(self):
        """total_hires returns 0 when no candidates are hired."""
        rec = RecruitmentFactory()
        self.assertEqual(rec.total_hires(), 0)


# ---------------------------------------------------------------------------
# Stage model tests
# ---------------------------------------------------------------------------
class StageModelTest(HorillaTestCase):
    """Tests for the Stage model."""

    def test_create_stage(self):
        """A stage can be created with minimal fields."""
        stage = StageFactory()
        self.assertIsNotNone(stage.pk)

    def test_str_contains_stage_name_and_recruitment(self):
        """__str__ shows 'stage - (recruitment title)'."""
        rec = RecruitmentFactory(title="DevOps Hire")
        stage = StageFactory(stage="Phone Screen", recruitment_id=rec)
        result = str(stage)
        self.assertIn("Phone Screen", result)
        self.assertIn("DevOps Hire", result)

    def test_ordering_by_sequence(self):
        """Stages order by sequence ascending (Meta.ordering)."""
        rec = RecruitmentFactory()
        # Recruitment.post_save signal auto-creates "Applied" (seq=0) and
        # "Initial" (seq=1). Create additional stages with higher sequences.
        s3 = StageFactory(recruitment_id=rec, stage="Third", sequence=30)
        s1 = StageFactory(recruitment_id=rec, stage="First", sequence=10)
        s2 = StageFactory(recruitment_id=rec, stage="Second", sequence=20)
        stages = list(Stage.objects.filter(recruitment_id=rec).order_by("sequence"))
        # Filter to only our manually created stages for the ordering assertion
        manual_stages = [s for s in stages if s in (s1, s2, s3)]
        self.assertEqual(manual_stages[0], s1)
        self.assertEqual(manual_stages[1], s2)
        self.assertEqual(manual_stages[2], s3)

    def test_stage_type_choices(self):
        """All valid stage_type choices are accepted."""
        rec = RecruitmentFactory()
        valid_types = ["initial", "applied", "test", "interview", "cancelled", "hired"]
        for i, st in enumerate(valid_types):
            stage = StageFactory(
                recruitment_id=rec,
                stage=f"Stage {st} {i}",
                stage_type=st,
            )
            self.assertEqual(stage.stage_type, st)

    def test_stage_type_default_is_interview(self):
        """Default stage_type is 'interview'."""
        rec = RecruitmentFactory()
        stage = Stage.objects.create(
            stage="Default Type Stage",
            recruitment_id=rec,
            sequence=0,
        )
        self.assertEqual(stage.stage_type, "interview")

    def test_recruitment_fk(self):
        """Stage references its recruitment correctly."""
        rec = RecruitmentFactory(title="QA Recruitment")
        stage = StageFactory(recruitment_id=rec)
        self.assertEqual(stage.recruitment_id, rec)

    def test_stage_managers_m2m(self):
        """Stage managers M2M works."""
        stage = StageFactory()
        mgr = self.admin_employee
        stage.stage_managers.add(mgr)
        self.assertIn(mgr, stage.stage_managers.all())

    def test_unique_together_recruitment_stage(self):
        """Same stage name in same recruitment raises IntegrityError."""
        rec = RecruitmentFactory()
        StageFactory(recruitment_id=rec, stage="Interview Round 1")
        with self.assertRaises(IntegrityError):
            StageFactory(recruitment_id=rec, stage="Interview Round 1")


# ---------------------------------------------------------------------------
# Candidate model tests
# ---------------------------------------------------------------------------
class CandidateModelTest(HorillaTestCase):
    """Tests for the Candidate model."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.job_pos = JobPositionFactory(job_position="Software Engineer")
        cls.recruitment = RecruitmentFactory(
            title="SE Recruitment",
            job_position_id=cls.job_pos,
            vacancy=5,
        )
        cls.recruitment.open_positions.add(cls.job_pos)
        # Recruitment.post_save signal auto-creates "Applied" (stage_type=applied,
        # sequence=0) and "Initial" (stage_type=initial, sequence=1) stages.
        # Reuse the auto-created "Initial" stage and create only the missing ones.
        cls.initial_stage = Stage.objects.get(
            recruitment_id=cls.recruitment, stage="Initial"
        )
        cls.interview_stage = StageFactory(
            recruitment_id=cls.recruitment,
            stage="Interview",
            stage_type="interview",
            sequence=10,
        )
        cls.hired_stage = StageFactory(
            recruitment_id=cls.recruitment,
            stage="Hired",
            stage_type="hired",
            sequence=20,
        )

    def _make_candidate(self, **kwargs):
        """Helper to create candidate with valid recruitment/stage."""
        defaults = {
            "name": "Jane Doe",
            "email": f"jane.{Candidate.objects.count()}@example.com",
            "recruitment_id": self.recruitment,
            "stage_id": self.initial_stage,
        }
        defaults.update(kwargs)
        return Candidate.objects.create(**defaults)

    def test_create_candidate(self):
        """A candidate can be created successfully."""
        cand = self._make_candidate()
        self.assertIsNotNone(cand.pk)

    def test_str_returns_name(self):
        """__str__ returns the candidate name."""
        cand = self._make_candidate(name="Alice Smith")
        self.assertEqual(str(cand), "Alice Smith")

    def test_is_active_default(self):
        """Candidate is_active defaults to True."""
        cand = self._make_candidate()
        self.assertTrue(cand.is_active)

    def test_email_unique_per_recruitment(self):
        """Same email in the same recruitment raises IntegrityError."""
        self._make_candidate(email="dup@example.com")
        with self.assertRaises(IntegrityError):
            self._make_candidate(email="dup@example.com")

    def test_email_same_across_different_recruitments(self):
        """Same email in different recruitments is allowed."""
        self._make_candidate(email="shared@example.com")
        job_pos2 = JobPositionFactory(job_position="Designer")
        rec2 = RecruitmentFactory(
            title="Design Recruitment",
            job_position_id=job_pos2,
        )
        rec2.open_positions.add(job_pos2)
        # Reuse the auto-created "Initial" stage (post_save signal)
        stage2 = Stage.objects.get(recruitment_id=rec2, stage="Initial")
        cand2 = Candidate.objects.create(
            name="Same Email",
            email="shared@example.com",
            recruitment_id=rec2,
            stage_id=stage2,
        )
        self.assertIsNotNone(cand2.pk)

    def test_hired_flag_set_when_stage_is_hired(self):
        """Candidate.hired is True when moved to hired stage."""
        cand = self._make_candidate(stage_id=self.hired_stage)
        self.assertTrue(cand.hired)

    def test_hired_flag_false_for_non_hired_stage(self):
        """Candidate.hired is False for non-hired stages."""
        cand = self._make_candidate(stage_id=self.initial_stage)
        self.assertFalse(cand.hired)

    def test_stage_transition_initial_to_interview(self):
        """Candidate can move from initial to interview stage."""
        cand = self._make_candidate(stage_id=self.initial_stage)
        cand.stage_id = self.interview_stage
        cand.save()
        cand.refresh_from_db()
        self.assertEqual(cand.stage_id, self.interview_stage)

    def test_stage_transition_to_hired(self):
        """Moving to hired stage sets hired=True."""
        cand = self._make_candidate(stage_id=self.initial_stage)
        cand.stage_id = self.hired_stage
        cand.save()
        cand.refresh_from_db()
        self.assertTrue(cand.hired)

    def test_canceled_flag_creates_cancelled_stage(self):
        """Setting canceled=True auto-creates/assigns a cancelled stage."""
        cand = self._make_candidate()
        cand.canceled = True
        cand.save()
        cand.refresh_from_db()
        self.assertTrue(cand.canceled)
        self.assertEqual(cand.stage_id.stage_type, "cancelled")

    def test_start_onboard_default_false(self):
        """start_onboard defaults to False."""
        cand = self._make_candidate()
        self.assertFalse(cand.start_onboard)

    def test_joining_date_nullable(self):
        """joining_date can be null."""
        cand = self._make_candidate()
        self.assertIsNone(cand.joining_date)

    def test_joining_date_can_be_set(self):
        """joining_date can be set to a date."""
        today = date.today()
        cand = self._make_candidate(joining_date=today)
        self.assertEqual(cand.joining_date, today)

    def test_hired_date_nullable(self):
        """hired_date can be null (editable=False, set programmatically)."""
        cand = self._make_candidate()
        self.assertIsNone(cand.hired_date)

    def test_job_position_auto_assigned_for_non_event_based(self):
        """For non-event-based recruitment, job_position_id is auto-set from recruitment."""
        cand = self._make_candidate(job_position_id=None)
        self.assertEqual(cand.job_position_id, self.job_pos)

    def test_invalid_job_position_raises_error(self):
        """Candidate with job_position not in recruitment.open_positions raises error."""
        other_pos = JobPositionFactory(job_position="Accountant")
        with self.assertRaises(ValidationError):
            self._make_candidate(job_position_id=other_pos)

    def test_get_full_name(self):
        """get_full_name returns the candidate name."""
        cand = self._make_candidate(name="Bob Builder")
        self.assertEqual(cand.get_full_name(), "Bob Builder")

    def test_get_email(self):
        """get_email returns the candidate email."""
        cand = self._make_candidate(email="bob@example.com")
        self.assertEqual(cand.get_email(), "bob@example.com")

    def test_converted_flag_clears_hired_and_canceled(self):
        """When converted=True, hired and canceled are set to False."""
        cand = self._make_candidate(stage_id=self.hired_stage)
        self.assertTrue(cand.hired)
        cand.converted = True
        cand.save()
        cand.refresh_from_db()
        self.assertFalse(cand.hired)
        self.assertFalse(cand.canceled)

    def test_offer_letter_status_default(self):
        """offer_letter_status defaults to 'not_sent'."""
        cand = self._make_candidate()
        self.assertEqual(cand.offer_letter_status, "not_sent")

    def test_gender_choices(self):
        """Valid gender values are accepted."""
        for gender in ["male", "female", "other"]:
            cand = self._make_candidate(
                email=f"gender.{gender}@example.com",
                gender=gender,
            )
            self.assertEqual(cand.gender, gender)


# ---------------------------------------------------------------------------
# SkillZone model tests
# ---------------------------------------------------------------------------
class SkillZoneModelTest(HorillaTestCase):
    """Tests for the SkillZone model."""

    def test_create_skill_zone(self):
        """A skill zone can be created."""
        sz = SkillZoneFactory()
        self.assertIsNotNone(sz.pk)

    def test_str_returns_title(self):
        """__str__ returns the title."""
        sz = SkillZoneFactory(title="Python Developers")
        self.assertEqual(str(sz), "Python Developers")

    def test_description_field(self):
        """Description is stored correctly."""
        sz = SkillZoneFactory(description="Pool of Python developers")
        self.assertEqual(sz.description, "Pool of Python developers")

    def test_company_fk(self):
        """SkillZone stores company FK correctly."""
        company = CompanyFactory(company="TechCorp")
        sz = SkillZoneFactory(company_id=company)
        self.assertEqual(sz.company_id, company)


# ---------------------------------------------------------------------------
# RejectReason + RejectedCandidate model tests
# ---------------------------------------------------------------------------
class RejectReasonModelTest(HorillaTestCase):
    """Tests for the RejectReason model."""

    def test_create_reject_reason(self):
        """A reject reason can be created."""
        reason = RejectReasonFactory()
        self.assertIsNotNone(reason.pk)

    def test_str_returns_title(self):
        """__str__ returns the title."""
        reason = RejectReasonFactory(title="Not enough experience")
        self.assertEqual(str(reason), "Not enough experience")

    def test_description_nullable(self):
        """Description can be blank/null."""
        reason = RejectReasonFactory(description=None)
        self.assertIsNone(reason.description)


class RejectedCandidateModelTest(HorillaTestCase):
    """Tests for the RejectedCandidate model."""

    def test_create_rejected_candidate(self):
        """A rejected candidate record can be created."""
        rejected = RejectedCandidateFactory()
        self.assertIsNotNone(rejected.pk)

    def test_str_contains_candidate_name(self):
        """__str__ contains the candidate name."""
        cand = CandidateFactory(name="Rejected Person")
        rejected = RejectedCandidateFactory(candidate_id=cand)
        self.assertIn("Rejected Person", str(rejected))

    def test_reject_reasons_m2m(self):
        """Reject reasons can be added via M2M."""
        reason1 = RejectReasonFactory(title="Failed test")
        reason2 = RejectReasonFactory(title="Culture fit")
        rejected = RejectedCandidateFactory()
        rejected.reject_reason_id.add(reason1, reason2)
        self.assertEqual(rejected.reject_reason_id.count(), 2)

    def test_one_to_one_with_candidate(self):
        """Only one RejectedCandidate per Candidate (OneToOne)."""
        cand = CandidateFactory()
        RejectedCandidateFactory(candidate_id=cand)
        with self.assertRaises(IntegrityError):
            RejectedCandidateFactory(candidate_id=cand)

    def test_description_stored(self):
        """Description field stores the rejection description."""
        rejected = RejectedCandidateFactory(description="Did not meet requirements")
        self.assertEqual(rejected.description, "Did not meet requirements")


# ---------------------------------------------------------------------------
# RecruitmentSurvey model tests
# ---------------------------------------------------------------------------
class RecruitmentSurveyModelTest(HorillaTestCase):
    """Tests for the RecruitmentSurvey model."""

    def test_create_survey_question(self):
        """A survey question can be created."""
        survey = RecruitmentSurveyFactory()
        self.assertIsNotNone(survey.pk)

    def test_str_returns_question(self):
        """__str__ returns the question text."""
        survey = RecruitmentSurveyFactory(question="What is your experience?")
        self.assertEqual(str(survey), "What is your experience?")

    def test_question_type_choices(self):
        """All valid question types are accepted."""
        valid_types = [
            "checkbox",
            "options",
            "multiple",
            "text",
            "number",
            "percentage",
            "date",
            "textarea",
            "file",
            "rating",
        ]
        for qt in valid_types:
            survey = RecruitmentSurveyFactory(type=qt)
            self.assertEqual(survey.type, qt)

    def test_choices_method_splits_options(self):
        """choices() splits comma-separated options."""
        survey = RecruitmentSurveyFactory(
            type="options",
            options="Yes, No, Maybe",
        )
        self.assertEqual(survey.choices(), ["Yes", "No", "Maybe"])

    def test_recruitment_ids_m2m(self):
        """Survey questions can be linked to recruitments via M2M."""
        rec = RecruitmentFactory()
        survey = RecruitmentSurveyFactory()
        survey.recruitment_ids.add(rec)
        self.assertIn(rec, survey.recruitment_ids.all())
