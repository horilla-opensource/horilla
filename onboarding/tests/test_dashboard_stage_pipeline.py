"""Onboarding dashboard "Onboarding Stage Pipeline" widget tests.

Regression coverage for a bug where the pipeline rendered one tile per
OnboardingStage *row* instead of one tile per distinct stage *name* --
since every Recruitment seeds its own OnboardingStage set, two
recruitments sharing a stage name (e.g. both auto-seeded "Initial") used
to render as two separate tiles instead of one aggregated tile.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from base.models import Department
from horilla.testkit import make_company, make_employee
from onboarding.models import CandidateStage, OnboardingStage
from recruitment.models import Candidate, JobPosition, Recruitment


class OnboardingStagePipelineWidgetTests(TestCase):
    def setUp(self):
        self.company = make_company("Stage Pipeline Co")
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="stage-pipeline-admin",
            email="stage-pipeline-admin@test.horilla",
            password="pass",
        )
        make_employee(
            company=self.company,
            email="stage-pipeline-admin-profile@test.horilla",
            user=self.admin,
        )
        self.client = Client()
        self.client.force_login(self.admin)

        department = Department.objects.create(department="Stage Pipeline Dept")
        job_position = JobPosition.objects.create(
            job_position="Stage Pipeline Role", department_id=department
        )

        # Two recruitments -- each auto-seeds its own "Initial" OnboardingStage
        # (see onboarding/tests/test_initial_stage.py), the exact setup that
        # used to double-render the "Initial" tile.
        self.recruitment_a = Recruitment.objects.create(
            title="Rec A",
            description="a",
            company_id=self.company,
            job_position_id=job_position,
        )
        self.recruitment_a.open_positions.add(job_position)
        self.recruitment_b = Recruitment.objects.create(
            title="Rec B",
            description="b",
            company_id=self.company,
            job_position_id=job_position,
            # Recruitment has a unique_together on
            # (job_position_id, start_date, company_id); recruitment_a
            # above already claimed today's date for this job/company.
            start_date=timezone.now().date() - timedelta(days=1),
        )
        self.recruitment_b.open_positions.add(job_position)
        stage_a = OnboardingStage.objects.get(
            recruitment_id=self.recruitment_a, stage_title="Initial"
        )
        stage_b = OnboardingStage.objects.get(
            recruitment_id=self.recruitment_b, stage_title="Initial"
        )

        self.candidates = [
            Candidate.objects.create(
                recruitment_id=self.recruitment_a,
                email=f"stage-cand-a{i}@test.horilla",
                name=f"Candidate A{i}",
                start_onboard=True,
            )
            for i in range(2)
        ] + [
            Candidate.objects.create(
                recruitment_id=self.recruitment_b,
                email="stage-cand-b0@test.horilla",
                name="Candidate B0",
                start_onboard=True,
            )
        ]
        CandidateStage.objects.create(
            candidate_id=self.candidates[0], onboarding_stage_id=stage_a
        )
        CandidateStage.objects.create(
            candidate_id=self.candidates[1], onboarding_stage_id=stage_a
        )
        CandidateStage.objects.create(
            candidate_id=self.candidates[2], onboarding_stage_id=stage_b
        )

    def _get_stages(self):
        response = self.client.get(reverse("onboarding-dashboard-stages"))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_same_named_stage_across_recruitments_is_one_tile(self):
        data = self._get_stages()
        titles = [s["stage"] for s in data["stages"]]
        self.assertEqual(
            titles.count("Initial"),
            1,
            "the 'Initial' stage rendered more than one tile",
        )

    def test_count_is_summed_across_recruitments(self):
        data = self._get_stages()
        initial = next(s for s in data["stages"] if s["stage"] == "Initial")
        self.assertEqual(initial["count"], 3)

    def test_stage_counts_sum_to_total_onboarding_candidates(self):
        data = self._get_stages()
        total_from_tiles = sum(s["count"] for s in data["stages"])
        self.assertEqual(total_from_tiles, len(self.candidates))
