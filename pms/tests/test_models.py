"""
Tests for PMS (Performance Management System) module models.

Covers Period, Objective, KeyResult, EmployeeObjective, EmployeeKeyResult,
Feedback, Question, Answer, QuestionTemplate, Comment, and BonusPointSetting
with CRUD, validation, and business logic tests.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from horilla.test_utils.base import HorillaTestCase
from pms.models import (
    Answer,
    BonusPointSetting,
    Comment,
    EmployeeKeyResult,
    EmployeeObjective,
    Feedback,
    KeyResult,
    Objective,
    Period,
    Question,
    QuestionOptions,
    QuestionTemplate,
)
from pms.tests.factories import (
    AnswerFactory,
    BonusPointSettingFactory,
    CommentFactory,
    EmployeeKeyResultFactory,
    EmployeeObjectiveFactory,
    FeedbackFactory,
    KeyResultFactory,
    ObjectiveFactory,
    PeriodFactory,
    QuestionFactory,
    QuestionOptionsFactory,
    QuestionTemplateFactory,
)


# ---------------------------------------------------------------------------
# Period Tests (~5)
# ---------------------------------------------------------------------------
class PeriodTests(HorillaTestCase):
    """CRUD and validation tests for Period model."""

    def test_create_period(self):
        period = PeriodFactory()
        self.assertIsNotNone(period.pk)
        self.assertIsNotNone(period.period_name)

    def test_str_representation(self):
        period = PeriodFactory(period_name="Q1 2026")
        self.assertEqual(str(period), "Q1 2026")

    def test_period_name_unique(self):
        PeriodFactory(period_name="Annual Review 2026")
        with self.assertRaises(IntegrityError):
            PeriodFactory(period_name="Annual Review 2026")

    def test_date_range(self):
        start = date(2026, 1, 1)
        end = date(2026, 3, 31)
        period = PeriodFactory(start_date=start, end_date=end)
        self.assertEqual(period.start_date, start)
        self.assertEqual(period.end_date, end)

    def test_period_with_company(self):
        period = PeriodFactory(company_id=[self.company_a])
        self.assertIn(self.company_a, period.company_id.all())


# ---------------------------------------------------------------------------
# KeyResult Tests (~5)
# ---------------------------------------------------------------------------
class KeyResultTests(HorillaTestCase):
    """CRUD and validation tests for KeyResult model."""

    def test_create_key_result(self):
        kr = KeyResultFactory(company_id=self.company_a)
        self.assertIsNotNone(kr.pk)
        self.assertEqual(kr.company_id, self.company_a)

    def test_str_representation(self):
        kr = KeyResultFactory(title="Increase Revenue")
        self.assertEqual(str(kr), "Increase Revenue")

    def test_default_target_value(self):
        kr = KeyResultFactory()
        self.assertEqual(kr.target_value, 100)

    def test_progress_type_choices(self):
        kr_pct = KeyResultFactory(progress_type="%")
        self.assertEqual(kr_pct.progress_type, "%")

        kr_num = KeyResultFactory(progress_type="#")
        self.assertEqual(kr_num.progress_type, "#")

        kr_usd = KeyResultFactory(progress_type="$")
        self.assertEqual(kr_usd.progress_type, "$")

    def test_get_progress_type_display(self):
        kr = KeyResultFactory(progress_type="%")
        self.assertEqual(kr.get_progress_type(), "Percentage")

        kr_usd = KeyResultFactory(progress_type="$")
        self.assertEqual(kr_usd.get_progress_type(), "USD$")

    def test_archive_default_false(self):
        kr = KeyResultFactory()
        self.assertFalse(kr.archive)


# ---------------------------------------------------------------------------
# Objective Tests (~5)
# ---------------------------------------------------------------------------
class ObjectiveTests(HorillaTestCase):
    """CRUD and validation tests for Objective model."""

    def test_create_objective(self):
        obj = ObjectiveFactory(company_id=self.company_a)
        self.assertIsNotNone(obj.pk)

    def test_str_representation(self):
        obj = ObjectiveFactory(title="Boost Sales")
        self.assertEqual(str(obj), "Boost Sales")

    def test_duration_unit_choices(self):
        obj_days = ObjectiveFactory(duration_unit="days")
        self.assertEqual(obj_days.duration_unit, "days")

        obj_months = ObjectiveFactory(duration_unit="months")
        self.assertEqual(obj_months.duration_unit, "months")

        obj_years = ObjectiveFactory(duration_unit="years")
        self.assertEqual(obj_years.duration_unit, "years")

    def test_duration_col(self):
        obj = ObjectiveFactory(duration=30, duration_unit="days")
        result = obj.duration_col()
        self.assertIn("30", result)
        self.assertIn("Days", result)

    def test_objective_with_key_results(self):
        kr1 = KeyResultFactory()
        kr2 = KeyResultFactory()
        obj = ObjectiveFactory(key_result_id=[kr1, kr2])
        self.assertEqual(obj.key_result_id.count(), 2)
        self.assertIn(kr1, obj.key_result_id.all())

    def test_archive_default_false(self):
        obj = ObjectiveFactory()
        self.assertFalse(obj.archive)


# ---------------------------------------------------------------------------
# EmployeeObjective Tests (~6)
# ---------------------------------------------------------------------------
class EmployeeObjectiveTests(HorillaTestCase):
    """CRUD and validation tests for EmployeeObjective model."""

    def test_create_employee_objective(self):
        emp_obj = EmployeeObjectiveFactory(employee_id=self.regular_employee)
        self.assertIsNotNone(emp_obj.pk)
        self.assertEqual(emp_obj.employee_id, self.regular_employee)

    def test_str_representation(self):
        obj = ObjectiveFactory(title="Sales Target")
        emp_obj = EmployeeObjectiveFactory(
            employee_id=self.regular_employee,
            objective_id=obj,
        )
        result = str(emp_obj)
        self.assertIn("Sales Target", result)

    @patch("pms.signals.logger")
    def test_status_choices(self, mock_logger):
        # Patch logger because pms/signals.py line 137 calls logger() as a
        # function (bug: should be logger.debug()). When automations tests run
        # first and register global post_save signals, the bonus-point signal
        # handler fires on EmployeeObjective save and hits that bug.
        for status_val, _ in EmployeeObjective.STATUS_CHOICES:
            emp_obj = EmployeeObjectiveFactory(
                employee_id=EmployeeObjectiveFactory._meta.declarations["employee_id"],
                status=status_val,
            )
            self.assertEqual(emp_obj.status, status_val)

    def test_default_status_not_started(self):
        emp_obj = EmployeeObjectiveFactory()
        self.assertEqual(emp_obj.status, "Not Started")

    def test_progress_percentage_default_zero(self):
        emp_obj = EmployeeObjectiveFactory()
        self.assertEqual(emp_obj.progress_percentage, 0)

    def test_unique_together_employee_objective(self):
        """Same employee cannot be assigned the same objective twice."""
        obj = ObjectiveFactory()
        EmployeeObjectiveFactory(
            employee_id=self.regular_employee,
            objective_id=obj,
        )
        with self.assertRaises(IntegrityError):
            EmployeeObjectiveFactory(
                employee_id=self.regular_employee,
                objective_id=obj,
            )

    def test_update_objective_progress(self):
        """Progress percentage should be the average of key result percentages."""
        emp_obj = EmployeeObjectiveFactory(employee_id=self.regular_employee)
        kr1 = KeyResultFactory()
        kr2 = KeyResultFactory()
        ekr1 = EmployeeKeyResultFactory(
            employee_objective_id=emp_obj,
            key_result_id=kr1,
            current_value=50,
            target_value=100,
        )
        ekr2 = EmployeeKeyResultFactory(
            employee_objective_id=emp_obj,
            key_result_id=kr2,
            current_value=80,
            target_value=100,
        )
        emp_obj.refresh_from_db()
        # (50 + 80) / 2 = 65%
        self.assertEqual(emp_obj.progress_percentage, 65)


# ---------------------------------------------------------------------------
# EmployeeKeyResult Tests (~6)
# ---------------------------------------------------------------------------
class EmployeeKeyResultTests(HorillaTestCase):
    """CRUD and validation tests for EmployeeKeyResult model."""

    def test_create_employee_key_result(self):
        ekr = EmployeeKeyResultFactory()
        self.assertIsNotNone(ekr.pk)

    def test_str_representation(self):
        ekr = EmployeeKeyResultFactory()
        result = str(ekr)
        self.assertIn("|", result)

    def test_default_status_not_started(self):
        ekr = EmployeeKeyResultFactory()
        self.assertEqual(ekr.status, "Not Started")

    def test_progress_computation(self):
        """progress_percentage = (current_value / target_value) * 100."""
        ekr = EmployeeKeyResultFactory(
            current_value=75,
            target_value=100,
        )
        self.assertEqual(ekr.progress_percentage, 75)

    def test_progress_computation_zero_start(self):
        ekr = EmployeeKeyResultFactory(
            start_value=0,
            current_value=0,
            target_value=100,
        )
        self.assertEqual(ekr.progress_percentage, 0)

    def test_save_sets_key_result_title(self):
        """EmployeeKeyResult.save() should copy key_result_id.title to key_result field."""
        kr = KeyResultFactory(title="Revenue Growth")
        ekr = EmployeeKeyResultFactory(key_result_id=kr)
        self.assertEqual(ekr.key_result, "Revenue Growth")

    def test_save_auto_sets_end_date_from_duration(self):
        """If start_date is set but end_date is None, save() auto-calculates end_date."""
        kr = KeyResultFactory(duration=15)
        start = date.today()
        ekr = EmployeeKeyResultFactory(
            key_result_id=kr,
            start_date=start,
            end_date=None,
        )
        self.assertEqual(ekr.end_date, start + timedelta(days=15))

    def test_clean_target_value_zero_raises(self):
        """Target value of 0 should raise ValidationError."""
        ekr = EmployeeKeyResultFactory(target_value=100)
        ekr.target_value = 0
        with self.assertRaises(ValidationError):
            ekr.clean()

    def test_clean_percentage_target_over_100_raises(self):
        """For percentage key results, target > 100 should raise."""
        kr = KeyResultFactory(progress_type="%")
        ekr = EmployeeKeyResultFactory(
            key_result_id=kr,
            target_value=150,
        )
        with self.assertRaises(ValidationError):
            ekr.clean()


# ---------------------------------------------------------------------------
# QuestionTemplate & Question Tests (~3)
# ---------------------------------------------------------------------------
class QuestionTemplateTests(HorillaTestCase):
    """Tests for QuestionTemplate model."""

    def test_create_question_template(self):
        qt = QuestionTemplateFactory()
        self.assertIsNotNone(qt.pk)

    def test_str_representation(self):
        qt = QuestionTemplateFactory(question_template="Annual Review Questions")
        self.assertEqual(str(qt), "Annual Review Questions")

    def test_question_count(self):
        qt = QuestionTemplateFactory()
        QuestionFactory(template_id=qt)
        QuestionFactory(template_id=qt)
        self.assertEqual(qt.question_count(), 2)


class QuestionTests(HorillaTestCase):
    """Tests for Question model."""

    def test_create_question(self):
        q = QuestionFactory()
        self.assertIsNotNone(q.pk)

    def test_str_representation(self):
        q = QuestionFactory(question="How effective is the team?")
        self.assertEqual(str(q), "How effective is the team?")

    def test_question_type_choices(self):
        for type_val, _ in Question.QUESTION_TYPE_CHOICE:
            q = QuestionFactory(question_type=type_val)
            self.assertEqual(q.question_type, type_val)


# ---------------------------------------------------------------------------
# Feedback Tests (~5)
# ---------------------------------------------------------------------------
class FeedbackTests(HorillaTestCase):
    """CRUD and validation tests for Feedback model."""

    def test_create_feedback(self):
        fb = FeedbackFactory(
            employee_id=self.regular_employee,
            manager_id=self.manager_employee,
        )
        self.assertIsNotNone(fb.pk)

    def test_str_representation(self):
        fb = FeedbackFactory(
            employee_id=self.regular_employee,
            review_cycle="Mid-Year 2026",
        )
        expected = f"{self.regular_employee.employee_first_name} - Mid-Year 2026"
        self.assertEqual(str(fb), expected)

    def test_status_choices(self):
        for status_val, _ in Feedback.STATUS_CHOICES:
            fb = FeedbackFactory(status=status_val)
            self.assertEqual(fb.status, status_val)

    def test_default_status_not_started(self):
        fb = FeedbackFactory()
        self.assertEqual(fb.status, "Not Started")

    def test_due_days_diff(self):
        end = date.today() + timedelta(days=10)
        fb = FeedbackFactory(end_date=end)
        self.assertEqual(fb.due_days_diff(), 10)

    def test_cyclic_feedback_days(self):
        """Cyclic feedback should compute next_start_date and next_end_date."""
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        fb = FeedbackFactory(
            start_date=start,
            end_date=end,
            cyclic_feedback=True,
            cyclic_feedback_days_count=3,
            cyclic_feedback_period="months",
        )
        self.assertEqual(fb.cyclic_next_start_date, date(2026, 4, 1))
        self.assertEqual(fb.cyclic_next_end_date, date(2026, 4, 30))

    def test_requested_employees(self):
        fb = FeedbackFactory(
            employee_id=self.regular_employee,
            manager_id=self.manager_employee,
        )
        employees = fb.requested_employees()
        self.assertIn(self.regular_employee, employees)
        self.assertIn(self.manager_employee, employees)


# ---------------------------------------------------------------------------
# Answer Tests (~2)
# ---------------------------------------------------------------------------
class AnswerTests(HorillaTestCase):
    """Tests for Answer model."""

    def test_create_answer(self):
        answer = AnswerFactory(employee_id=self.regular_employee)
        self.assertIsNotNone(answer.pk)
        self.assertEqual(answer.employee_id, self.regular_employee)

    def test_str_representation(self):
        answer = AnswerFactory(
            employee_id=self.regular_employee,
            answer={"text": "Excellent work"},
        )
        expected = f"{self.regular_employee.employee_first_name} - {{'text': 'Excellent work'}}"
        self.assertEqual(str(answer), expected)


# ---------------------------------------------------------------------------
# Comment Tests (~2)
# ---------------------------------------------------------------------------
class CommentTests(HorillaTestCase):
    """Tests for Comment model."""

    def test_create_comment(self):
        comment = CommentFactory(employee_id=self.regular_employee)
        self.assertIsNotNone(comment.pk)

    def test_str_representation(self):
        comment = CommentFactory(
            employee_id=self.regular_employee,
            comment="Great progress on this objective",
        )
        expected = f"{self.regular_employee.employee_first_name} - Great progress on this objective "
        self.assertEqual(str(comment), expected)


# ---------------------------------------------------------------------------
# BonusPointSetting Tests (~4)
# ---------------------------------------------------------------------------
class BonusPointSettingTests(HorillaTestCase):
    """CRUD and validation tests for BonusPointSetting model."""

    def test_create_bonus_point_setting(self):
        bps = BonusPointSettingFactory()
        self.assertIsNotNone(bps.pk)

    def test_default_is_active(self):
        bps = BonusPointSettingFactory()
        self.assertTrue(bps.is_active)

    def test_model_choices(self):
        bps_obj = BonusPointSettingFactory(model="pms.models.EmployeeObjective")
        self.assertEqual(bps_obj.model, "pms.models.EmployeeObjective")

        bps_kr = BonusPointSettingFactory(model="pms.models.EmployeeKeyResult")
        self.assertEqual(bps_kr.model, "pms.models.EmployeeKeyResult")

    def test_get_model_display(self):
        bps = BonusPointSettingFactory(model="pms.models.EmployeeObjective")
        self.assertEqual(bps.get_model_display(), "Objective")

    def test_get_bonus_for_display(self):
        bps = BonusPointSettingFactory(bonus_for="Closed")
        self.assertEqual(bps.get_bonus_for_display(), "Closing")

    def test_points_default_zero(self):
        bps = BonusPointSetting.objects.create(
            model="pms.models.EmployeeObjective",
            bonus_for="Closed",
        )
        self.assertEqual(bps.points, 0)

    def test_conditions_and_fields(self):
        bps = BonusPointSettingFactory(
            field_1="complition_date",
            conditions="<=",
            field_2="end_date",
        )
        condition_str = bps.get_condition()
        self.assertIn("Completion Date", condition_str)
        self.assertIn("<=", condition_str)
        self.assertIn("End Date", condition_str)
