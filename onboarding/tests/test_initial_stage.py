"""Onboarding initial stage signal smoke tests."""

from django.test import TestCase

from horilla.testkit import make_company
from onboarding.models import OnboardingStage
from recruitment.models import Recruitment


class OnboardingInitialStageTests(TestCase):
    def test_recruitment_create_seeds_initial_stage(self):
        company = make_company("Onboard Co")
        recruitment = Recruitment.objects.create(
            title="Onboard Rec Unit",
            description="Smoke",
            company_id=company,
        )
        stage = OnboardingStage.objects.filter(recruitment_id=recruitment).first()
        self.assertIsNotNone(stage)
        self.assertEqual(stage.stage_title, "Initial")
        self.assertEqual(stage.sequence, 0)
