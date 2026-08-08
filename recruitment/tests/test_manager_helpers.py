"""Recruitment manager helper smoke + deepen tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from recruitment.methods import (
    in_all_managers,
    is_recruitmentmanager,
    is_stagemanager,
    recruitment_manages,
    stage_manages,
)


class RecruitmentManagerHelperTests(SimpleTestCase):
    def test_stagemanager_true_when_stage_set_exists(self):
        employee = SimpleNamespace(
            recruitment_set=MagicMock(exists=MagicMock(return_value=False)),
            stage_set=MagicMock(exists=MagicMock(return_value=True)),
        )
        request = SimpleNamespace(user=SimpleNamespace(employee_get=employee))
        self.assertTrue(is_stagemanager(request))

    def test_recruitmentmanager_false_without_sets(self):
        employee = SimpleNamespace(
            recruitment_set=MagicMock(exists=MagicMock(return_value=False)),
        )
        request = SimpleNamespace(user=SimpleNamespace(employee_get=employee))
        self.assertFalse(is_recruitmentmanager(request))

    def test_helpers_false_without_employee(self):
        request = SimpleNamespace(user=SimpleNamespace())
        self.assertFalse(is_stagemanager(request))
        self.assertFalse(is_recruitmentmanager(request))

    def test_stage_manages_true_via_stage_manager(self):
        employee = SimpleNamespace(id=7)
        stage = SimpleNamespace(
            stage_manager=MagicMock(
                filter=MagicMock(
                    return_value=MagicMock(exists=MagicMock(return_value=True))
                )
            ),
            recruitment_id=SimpleNamespace(
                recruitment_managers=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(exists=MagicMock(return_value=False))
                    )
                )
            ),
        )
        request = SimpleNamespace(user=SimpleNamespace(employee_get=employee))
        self.assertTrue(stage_manages(request, stage))

    def test_recruitment_manages_true(self):
        employee = SimpleNamespace(id=3)
        recruitment = SimpleNamespace(
            recruitment_managers=MagicMock(
                filter=MagicMock(
                    return_value=MagicMock(exists=MagicMock(return_value=True))
                )
            )
        )
        request = SimpleNamespace(user=SimpleNamespace(employee_get=employee))
        self.assertTrue(recruitment_manages(request, recruitment))

    def test_in_all_managers_false_when_all_empty(self):
        employee = SimpleNamespace(
            stage_set=MagicMock(exists=MagicMock(return_value=False)),
            recruitment_set=MagicMock(exists=MagicMock(return_value=False)),
            onboardingstage_set=MagicMock(exists=MagicMock(return_value=False)),
            onboarding_task=MagicMock(exists=MagicMock(return_value=False)),
        )
        request = SimpleNamespace(user=SimpleNamespace(employee_get=employee))
        self.assertFalse(in_all_managers(request))
