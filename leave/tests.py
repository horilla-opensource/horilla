"""
Tests for LeaveType payment type handling, conditions, assignment validation,
and employee-specific holiday filtering.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.test import TestCase

from base.models import Company, Department, EmployeeShift, Holidays, WorkType
from employee.models import Employee, EmployeeWorkInformation
from leave.methods import holiday_dates_list
from leave.models import PAYMENT_TYPE, LeaveType, LeaveTypeCondition
from leave.services import evaluate_leave_type_conditions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_leave_type(**kwargs):
    lt = LeaveType.__new__(LeaveType)
    lt.pk = 1
    lt.id = 1
    lt.name = kwargs.get("name", "Test Leave")
    lt.payment = kwargs.get("payment", "paid")
    lt.payment_type = kwargs.get("payment_type", "fully_paid")
    lt.payment_percentage = kwargs.get("payment_percentage", None)
    # Stub conditions as empty queryset by default
    lt.conditions = MagicMock()
    lt.conditions.all.return_value = []
    return lt


def _make_employee(**kwargs):
    emp = MagicMock()
    emp.id = kwargs.get("id", 1)
    emp.gender = kwargs.get("gender", "male")
    emp.marital_status = kwargs.get("marital_status", "single")
    emp.country = kwargs.get("country", "")
    emp.get_full_name.return_value = kwargs.get("name", "Test Employee")
    return emp


# ---------------------------------------------------------------------------
# Payment type / percentage tests
# ---------------------------------------------------------------------------


class PaymentTypeChoicesTest(TestCase):
    def test_payment_type_choices_exist(self):
        keys = [k for k, _ in PAYMENT_TYPE]
        self.assertIn("fully_paid", keys)
        self.assertIn("half_paid", keys)
        self.assertIn("unpaid", keys)
        self.assertIn("custom", keys)


class LeaveTypeGetPaymentPercentageTest(TestCase):
    def _lt(self, **kw):
        return _make_leave_type(**kw)

    def test_fully_paid_returns_100(self):
        lt = self._lt(payment_type="fully_paid")
        self.assertEqual(lt.get_payment_percentage(), 100.0)

    def test_half_paid_returns_50(self):
        lt = self._lt(payment_type="half_paid")
        self.assertEqual(lt.get_payment_percentage(), 50.0)

    def test_unpaid_returns_0(self):
        lt = self._lt(payment_type="unpaid")
        self.assertEqual(lt.get_payment_percentage(), 0.0)

    def test_custom_uses_payment_percentage(self):
        lt = self._lt(payment_type="custom", payment_percentage=Decimal("75.00"))
        self.assertEqual(lt.get_payment_percentage(), 75.0)

    def test_custom_with_none_percentage_returns_0(self):
        lt = self._lt(payment_type="custom", payment_percentage=None)
        self.assertEqual(lt.get_payment_percentage(), 0.0)

    def test_backward_compat_paid(self):
        lt = self._lt(payment_type=None, payment="paid")
        self.assertEqual(lt.get_payment_percentage(), 100.0)

    def test_backward_compat_unpaid(self):
        lt = self._lt(payment_type=None, payment="unpaid")
        self.assertEqual(lt.get_payment_percentage(), 0.0)


class LeaveTypePaymentTypeDisplayTest(TestCase):
    def test_fully_paid_display(self):
        lt = _make_leave_type(payment_type="fully_paid")
        self.assertIn("100", lt.payment_type_display())

    def test_half_paid_display(self):
        lt = _make_leave_type(payment_type="half_paid")
        self.assertIn("50", lt.payment_type_display())

    def test_custom_display(self):
        lt = _make_leave_type(payment_type="custom", payment_percentage=Decimal("33"))
        self.assertIn("33", lt.payment_type_display())


# ---------------------------------------------------------------------------
# LeaveTypeCondition model tests
# ---------------------------------------------------------------------------


class LeaveTypeConditionModelTest(TestCase):
    def test_str_with_value(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.condition_type = "gender"
        cond.value = "female"
        self.assertIn("female", str(cond))
        self.assertIn("Gender", str(cond))

    def test_str_without_value(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.condition_type = "once_per_employment"
        cond.value = None
        self.assertIn("Once Per Employment", str(cond))

    def test_clean_raises_when_value_missing_for_gender(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.pk = None
        cond.condition_type = "gender"
        cond.value = ""
        with self.assertRaises(ValidationError):
            cond.clean()

    def test_clean_passes_for_once_per_employment_without_value(self):
        cond = LeaveTypeCondition.__new__(LeaveTypeCondition)
        cond.pk = None
        cond.condition_type = "once_per_employment"
        cond.value = None
        # Should not raise
        cond.clean()


# ---------------------------------------------------------------------------
# evaluate_leave_type_conditions service tests
# ---------------------------------------------------------------------------


class GenderConditionTest(TestCase):
    def _gender_condition(self, value):
        cond = MagicMock()
        cond.condition_type = "gender"
        cond.value = value
        return cond

    def test_matching_gender_passes(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._gender_condition("female")]
        employee = _make_employee(gender="female")
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)
        self.assertIsNone(msg)

    def test_wrong_gender_fails(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._gender_condition("female")]
        employee = _make_employee(gender="male")
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)
        self.assertIn("female", str(msg))

    def test_case_insensitive_gender_match(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._gender_condition("Female")]
        employee = _make_employee(gender="female")
        is_eligible, _ = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    def test_maternity_female_only(self):
        lt = _make_leave_type(name="Maternity Leave")
        lt.conditions.all.return_value = [self._gender_condition("female")]
        male = _make_employee(gender="male")
        is_eligible, msg = evaluate_leave_type_conditions(lt, male)
        self.assertFalse(is_eligible)

    def test_paternity_male_only(self):
        lt = _make_leave_type(name="Paternity Leave")
        lt.conditions.all.return_value = [self._gender_condition("male")]
        female = _make_employee(gender="female")
        is_eligible, msg = evaluate_leave_type_conditions(lt, female)
        self.assertFalse(is_eligible)


class OncePerEmploymentConditionTest(TestCase):
    def _once_condition(self):
        cond = MagicMock()
        cond.condition_type = "once_per_employment"
        cond.value = None
        return cond

    @patch("leave.services.AvailableLeave")
    def test_not_yet_assigned_passes(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = False
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._once_condition()]
        employee = _make_employee()
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    @patch("leave.services.AvailableLeave")
    def test_already_assigned_blocks(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = True
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._once_condition()]
        employee = _make_employee()
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)
        self.assertIn("once", str(msg).lower())


class MaritalStatusConditionTest(TestCase):
    def _marital_condition(self, value):
        cond = MagicMock()
        cond.condition_type = "marital_status"
        cond.value = value
        return cond

    def test_matching_marital_passes(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._marital_condition("married")]
        employee = _make_employee(marital_status="married")
        is_eligible, _ = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    def test_wrong_marital_fails(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = [self._marital_condition("married")]
        employee = _make_employee(marital_status="single")
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)


class NoConditionsTest(TestCase):
    def test_no_conditions_always_eligible(self):
        lt = _make_leave_type()
        lt.conditions.all.return_value = []
        employee = _make_employee()
        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)
        self.assertIsNone(msg)


class MultipleConditionsTest(TestCase):
    """When multiple conditions are set, all must pass."""

    @patch("leave.services.AvailableLeave")
    def test_all_pass(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = False

        gender_cond = MagicMock()
        gender_cond.condition_type = "gender"
        gender_cond.value = "female"

        once_cond = MagicMock()
        once_cond.condition_type = "once_per_employment"
        once_cond.value = None

        lt = _make_leave_type()
        lt.conditions.all.return_value = [gender_cond, once_cond]
        employee = _make_employee(gender="female")

        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertTrue(is_eligible)

    @patch("leave.services.AvailableLeave")
    def test_first_fails_short_circuits(self, MockAL):
        MockAL.objects.filter.return_value.exists.return_value = False

        gender_cond = MagicMock()
        gender_cond.condition_type = "gender"
        gender_cond.value = "female"

        once_cond = MagicMock()
        once_cond.condition_type = "once_per_employment"
        once_cond.value = None

        lt = _make_leave_type()
        lt.conditions.all.return_value = [gender_cond, once_cond]
        employee = _make_employee(gender="male")  # fails gender check

        is_eligible, msg = evaluate_leave_type_conditions(lt, employee)
        self.assertFalse(is_eligible)
        # once_per_employment filter should NOT have been called
        MockAL.objects.filter.assert_not_called()


# ---------------------------------------------------------------------------
# Employee-specific holiday filtering tests
# ---------------------------------------------------------------------------


class LeaveHolidayFixtureMixin:
    """
    Creates two employees, a global holiday, and an employee-specific holiday
    for use in leave app holiday filter tests.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company="Leave Test Corp",
            hq=True,
            address="2 Test Ave",
            country="US",
            state="NY",
            city="NYC",
            zip="10001",
        )
        cls.shift = EmployeeShift.objects.create(employee_shift="Morning Shift")
        cls.shift.company_id.add(cls.company)

        cls.work_type = WorkType.objects.create(work_type="Remote")
        cls.work_type.company_id.add(cls.company)

        cls.emp_a = cls._make_employee("leave_a@holiday.test", "Carol", "Leave")
        cls.emp_b = cls._make_employee("leave_b@holiday.test", "Dan", "Leave")

        cls.today = date.today()
        cls.past_global = cls.today - timedelta(days=45)
        cls.past_specific = cls.today - timedelta(days=20)
        cls.future_date = cls.today + timedelta(days=15)

        cls.global_holiday = Holidays.objects.create(
            name="Leave Global Holiday",
            start_date=cls.past_global,
            end_date=cls.past_global,
            is_specific=False,
            company_id=cls.company,
        )
        cls.specific_holiday = Holidays.objects.create(
            name="Leave Specific Holiday",
            start_date=cls.past_specific,
            end_date=cls.past_specific,
            is_specific=True,
            assigning_type="employee",
            company_id=cls.company,
        )
        cls.specific_holiday.employees.add(cls.emp_a)

        cls.future_global = Holidays.objects.create(
            name="Future Global Holiday",
            start_date=cls.future_date,
            end_date=cls.future_date,
            is_specific=False,
            company_id=cls.company,
        )

    @classmethod
    def _make_employee(cls, email, first_name, last_name):
        emp = Employee.objects.create(
            employee_first_name=first_name,
            employee_last_name=last_name,
            email=email,
            phone="8888888888",
        )
        EmployeeWorkInformation.objects.filter(employee_id=emp).update(
            company_id_id=cls.company.pk,
            shift_id_id=cls.shift.pk,
            work_type_id_id=cls.work_type.pk,
        )
        return emp


class TestHolidayDatesList(LeaveHolidayFixtureMixin, TestCase):
    """
    holiday_dates_list() must correctly expand multi-day holiday ranges
    and return the right dates when fed employee-filtered querysets.
    """

    def test_global_holiday_date_included_for_all(self):
        """Global holiday date appears when filtered for any employee."""
        for emp in (self.emp_a, self.emp_b):
            with self.subTest(employee=emp):
                qs = Holidays.objects.filter(
                    Q(is_specific=False) | Q(employees=emp),
                    start_date=self.past_global,
                )
                self.assertIn(self.past_global, holiday_dates_list(qs))

    def test_specific_holiday_included_for_assigned_emp_a(self):
        """Specific holiday date appears for the assigned employee."""
        qs = Holidays.objects.filter(
            Q(is_specific=False) | Q(employees=self.emp_a),
            start_date=self.past_specific,
        )
        self.assertIn(self.past_specific, holiday_dates_list(qs))

    def test_specific_holiday_excluded_for_unassigned_emp_b(self):
        """Specific holiday date does NOT appear for an unassigned employee."""
        qs = Holidays.objects.filter(
            Q(is_specific=False) | Q(employees=self.emp_b),
            start_date=self.past_specific,
        )
        self.assertNotIn(self.past_specific, holiday_dates_list(qs))

    def test_admin_filter_excludes_specific_holiday(self):
        """is_specific=False filter (admin pattern) excludes specific holidays."""
        qs = Holidays.objects.filter(
            is_specific=False,
            start_date=self.past_specific,
        )
        self.assertNotIn(self.past_specific, holiday_dates_list(qs))

    def test_multi_day_range_expands_correctly(self):
        """A 3-day holiday expands to all 3 dates."""
        start = self.past_global - timedelta(days=5)
        end = start + timedelta(days=2)
        h = Holidays.objects.create(
            name="Multi Day",
            start_date=start,
            end_date=end,
            is_specific=False,
            company_id=self.company,
        )
        dates = holiday_dates_list(Holidays.objects.filter(pk=h.pk))
        self.assertEqual(len(dates), 3)
        self.assertIn(start, dates)
        self.assertIn(start + timedelta(days=1), dates)
        self.assertIn(end, dates)


class TestAdminHolidayFilter(LeaveHolidayFixtureMixin, TestCase):
    """
    Admin views (leave_upcoming_holidays, employee_leave) use is_specific=False.
    They must show global holidays and hide specific ones.
    """

    def _admin_qs(self, start=None, end=None):
        start = start or (self.today - timedelta(days=90))
        end = end or (self.today + timedelta(days=90))
        return Holidays.objects.filter(
            is_specific=False,
            start_date__gte=start,
            start_date__lte=end,
        )

    def test_global_holiday_appears_in_admin_view(self):
        qs = self._admin_qs()
        self.assertIn(self.global_holiday, qs)

    def test_specific_holiday_excluded_from_admin_view(self):
        qs = self._admin_qs()
        self.assertNotIn(self.specific_holiday, qs)

    def test_future_global_appears_in_admin_view(self):
        qs = self._admin_qs()
        self.assertIn(self.future_global, qs)

    def test_admin_view_date_range_respected(self):
        """Holidays outside the date range are excluded."""
        # Query only within the past_global month — future_global should not appear
        qs = self._admin_qs(
            start=self.past_global - timedelta(days=1),
            end=self.past_global + timedelta(days=1),
        )
        self.assertIn(self.global_holiday, qs)
        self.assertNotIn(self.future_global, qs)


class TestEmployeeHolidayFilter(LeaveHolidayFixtureMixin, TestCase):
    """
    Employee-facing views (form_valid, employee_dashboard) use
    Q(is_specific=False) | Q(employees=employee).
    """

    def _employee_qs(self, employee):
        return Holidays.objects.filter(Q(is_specific=False) | Q(employees=employee))

    def test_global_holiday_visible_to_emp_a(self):
        qs = self._employee_qs(self.emp_a)
        self.assertIn(self.global_holiday, qs)

    def test_global_holiday_visible_to_emp_b(self):
        qs = self._employee_qs(self.emp_b)
        self.assertIn(self.global_holiday, qs)

    def test_specific_holiday_visible_to_assigned_emp_a(self):
        qs = self._employee_qs(self.emp_a)
        self.assertIn(self.specific_holiday, qs)

    def test_specific_holiday_hidden_from_unassigned_emp_b(self):
        qs = self._employee_qs(self.emp_b)
        self.assertNotIn(self.specific_holiday, qs)

    def test_both_holidays_in_emp_a_dates(self):
        """emp_a sees dates for both global and specific holidays."""
        qs = self._employee_qs(self.emp_a)
        dates = holiday_dates_list(qs)
        self.assertIn(self.past_global, dates)
        self.assertIn(self.past_specific, dates)

    def test_only_global_in_emp_b_dates(self):
        """emp_b sees only the global holiday date, not the specific one."""
        qs = self._employee_qs(self.emp_b)
        dates = holiday_dates_list(qs)
        self.assertIn(self.past_global, dates)
        self.assertNotIn(self.past_specific, dates)


class TestTodayHolidaysMethod(LeaveHolidayFixtureMixin, TestCase):
    """
    Holidays.today_holidays() updated with employee=None parameter.
    Without employee: returns all holidays active today.
    With employee: applies Q(is_specific=False) | Q(employees=employee).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create a holiday active TODAY to test today_holidays
        cls.today_global = Holidays.objects.create(
            name="Today Global",
            start_date=cls.today,
            end_date=cls.today,
            is_specific=False,
            company_id=cls.company,
        )
        cls.today_specific = Holidays.objects.create(
            name="Today Specific",
            start_date=cls.today,
            end_date=cls.today,
            is_specific=True,
            assigning_type="employee",
            company_id=cls.company,
        )
        cls.today_specific.employees.add(cls.emp_a)

    def test_no_employee_returns_both_holiday_types(self):
        """today_holidays() without employee returns global and specific holidays."""
        qs = Holidays.today_holidays(today=self.today)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.today_global.pk, pks)
        self.assertIn(self.today_specific.pk, pks)

    def test_with_emp_a_returns_own_specific_holiday(self):
        """today_holidays(employee=emp_a) includes emp_a's specific holiday."""
        qs = Holidays.today_holidays(today=self.today, employee=self.emp_a)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.today_global.pk, pks)
        self.assertIn(self.today_specific.pk, pks)

    def test_with_emp_b_excludes_emp_a_specific_holiday(self):
        """today_holidays(employee=emp_b) hides emp_a's specific holiday."""
        qs = Holidays.today_holidays(today=self.today, employee=self.emp_b)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.today_global.pk, pks)
        self.assertNotIn(self.today_specific.pk, pks)

    def test_admin_pattern_filters_specific_from_today_holidays(self):
        """Admin call pattern: today_holidays().filter(is_specific=False) excludes specific."""
        qs = Holidays.today_holidays(today=self.today).filter(is_specific=False)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.today_global.pk, pks)
        self.assertNotIn(self.today_specific.pk, pks)

    def test_past_date_returns_nothing_for_today_holidays(self):
        """today_holidays() for a date with no active holidays returns empty qs."""
        far_past = self.today - timedelta(days=200)
        qs = Holidays.today_holidays(today=far_past)
        self.assertFalse(qs.exists())
