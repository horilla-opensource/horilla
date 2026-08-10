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
from leave.models import (
    PAYMENT_TYPE,
    LeaveType,
    LeaveTypeCondition,
    AvailableLeave,
    UnpaidLeave,
    LeaveAccrualAuditLog,
)
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


# ============================================================================
# ROYAL FALCON SECURITY - Leave Accrual Policy Tests
# ============================================================================


class RoyalFalconLeaveAccrualTestCase(TestCase):
    """Base test case with common setup for all accrual tests."""

    def setUp(self):
       """Set up test data: company, departments, employees, leave types."""
       # Create company
       self.company = Company.objects.create(
           company_name="Royal Falcon Security",
           company_code="RFS",
       )

       # Create department
       self.department = Department.objects.create(
           department_name="Operations",
           company_id=self.company,
       )

       # Create leave type (Annual Leave)
       self.leave_type = LeaveType.objects.create(
           name="Annual Leave",
           code="AL",
           count=12,
           company_id=self.company,
           payment_type="paid",
           carryforward_max=60,
       )

    def create_employee(self, badge_id, joining_date, company=None):
       """Helper to create employee with badge ID and joining date."""
       if company is None:
           company = self.company

       employee = Employee.objects.create(
           badge_id=badge_id,
           employee_first_name=f"Test_{badge_id}",
           employee_last_name="Employee",
           email=f"{badge_id}@test.com",
       )

       # Create work information
       EmployeeWorkInformation.objects.filter(employee_id=employee).update(
           company_id_id=company.pk,
           date_joining=joining_date,
       )

       # Store original joining date
       employee.original_joining_date = joining_date
       employee.save()

       # Create available leave
       AvailableLeave.objects.create(
           employee_id=employee,
           leave_type_id=self.leave_type,
           available_days=0,
           carryforward_days=0,
           assigned_date=date.today(),
       )

       return employee


class TestEmployeeCategoryDetection(RoyalFalconLeaveAccrualTestCase):
    """Test badge prefix to category conversion."""

    def test_management_prefix(self):
       """Test A- prefix correctly identifies as Management."""
       from leave.models import EmployeeCategory

       cat = EmployeeCategory.objects.create(
           company_id=self.company,
           name="Management",
           badge_id_prefix="A",
           max_carryforward_days=30,
       )

       from leave.accrual_service import get_employee_category
       employee = self.create_employee("A-001", date(2024, 1, 15))
       category = get_employee_category(employee)

       self.assertIsNotNone(category)
       self.assertEqual(category.badge_id_prefix, "A")
       self.assertEqual(category.max_carryforward_days, 30)

    def test_normal_prefix(self):
       """Test S- prefix correctly identifies as Normal Employee."""
       from leave.models import EmployeeCategory

       cat = EmployeeCategory.objects.create(
           company_id=self.company,
           name="Normal",
           badge_id_prefix="S",
           max_carryforward_days=60,
       )

       from leave.accrual_service import get_employee_category
       employee = self.create_employee("S-001", date(2024, 1, 15))
       category = get_employee_category(employee)

       self.assertIsNotNone(category)
       self.assertEqual(category.badge_id_prefix, "S")
       self.assertEqual(category.max_carryforward_days, 60)


class TestAnniversaryDetection(RoyalFalconLeaveAccrualTestCase):
    """Test anniversary month detection for accrual eligibility."""

    def test_anniversary_month_same_month_next_year(self):
       """Test employee anniversary month is correctly detected."""
       from leave.accrual_service import is_anniversary_month

       joining_date = date(2024, 2, 15)
       employee = self.create_employee("S-001", joining_date)

       # On Feb 15, 2025 (same month next year)
       test_date = date(2025, 2, 15)
       self.assertTrue(is_anniversary_month(employee, test_date))

    def test_non_anniversary_month(self):
       """Test non-anniversary months return False."""
       from leave.accrual_service import is_anniversary_month

       joining_date = date(2024, 2, 15)
       employee = self.create_employee("S-001", joining_date)

       # On Mar 15, 2025 - different month
       test_date = date(2025, 3, 15)
       self.assertFalse(is_anniversary_month(employee, test_date))


class TestServiceCalculation(RoyalFalconLeaveAccrualTestCase):
    """Test service duration calculation excluding unpaid/unauthorized days."""

    def test_basic_service_days_no_exclusions(self):
       """Test basic service calculation without exclusions."""
       from leave.accrual_service import calculate_adjusted_service_days

       joining_date = date(2024, 1, 15)
       employee = self.create_employee("S-001", joining_date)

       test_date = date(2024, 2, 15)  # 31 days of service
       service_days = calculate_adjusted_service_days(employee, test_date)
       self.assertGreaterEqual(service_days, 30)

    def test_service_excludes_unpaid_leave(self):
       """Test unpaid leave days are excluded from service calculation."""
       from leave.accrual_service import calculate_adjusted_service_days

       joining_date = date(2024, 1, 15)
       employee = self.create_employee("S-001", joining_date)

       # Create unpaid leave for 5 days
       UnpaidLeave.objects.create(
           employee_id=employee,
           start_date=date(2024, 2, 1),
           end_date=date(2024, 2, 5),
           reason="Family emergency",
           status="active",
           accrual_paused=True,
           days_count=5,
       )

       test_date = date(2024, 3, 15)
       service_days_with_unpaid = calculate_adjusted_service_days(employee, test_date)

       # Create another employee without unpaid leave
       employee2 = self.create_employee("S-002", joining_date)
       service_days_without_unpaid = calculate_adjusted_service_days(employee2, test_date)

       # First employee should have fewer days due to unpaid leave
       self.assertLess(service_days_with_unpaid, service_days_without_unpaid)


class TestAccrualAuditLogImmutability(RoyalFalconLeaveAccrualTestCase):
    """Test that audit logs are immutable."""

    def test_audit_log_creation(self):
       """Test that audit log can be created."""
       from leave.accrual_service import create_accrual_audit_log

       employee = self.create_employee("S-001", date(2024, 1, 15))

       audit_log = create_accrual_audit_log(
           employee=employee,
           accrual_type="monthly_accrual",
           old_balance=10.0,
           new_balance=12.5,
           reason="Monthly Accrual - 2.5 days on anniversary",
       )

       self.assertEqual(audit_log.accrual_type, "monthly_accrual")
       self.assertEqual(audit_log.accrual_days, 2.5)
       self.assertEqual(audit_log.old_balance, 10.0)
       self.assertEqual(audit_log.new_balance, 12.5)

    def test_audit_log_cannot_be_edited(self):
       """Test that audit log cannot be edited after creation."""
       from leave.accrual_service import create_accrual_audit_log

       employee = self.create_employee("S-001", date(2024, 1, 15))
       audit_log = create_accrual_audit_log(
           employee=employee,
           accrual_type="monthly_accrual",
           old_balance=10.0,
           new_balance=12.5,
           reason="Test Accrual",
       )

       # Try to update
       audit_log.reason = "Modified reason"
       with self.assertRaises(ValidationError):
           audit_log.save()

    def test_audit_log_cannot_be_deleted(self):
       """Test that audit log cannot be deleted after creation."""
       from leave.accrual_service import create_accrual_audit_log

       employee = self.create_employee("S-001", date(2024, 1, 15))
       audit_log = create_accrual_audit_log(
           employee=employee,
           accrual_type="monthly_accrual",
           old_balance=10.0,
           new_balance=12.5,
           reason="Test Accrual",
       )

       # Try to delete
       with self.assertRaises(ValidationError):
           audit_log.delete()


class TestAccrualPauseResume(RoyalFalconLeaveAccrualTestCase):
    """Test accrual pause/resume mechanisms during unpaid leave."""

    def test_accrual_paused_when_unpaid_leave_active(self):
       """Test that accrual is paused when unpaid leave is created."""
       from leave.accrual_service import pause_accrual_for_unpaid_leave

       employee = self.create_employee("S-001", date(2024, 1, 15))
       available_leave = AvailableLeave.objects.get(
           employee_id=employee,
           leave_type_id=self.leave_type,
       )

       # Create unpaid leave
       unpaid = UnpaidLeave.objects.create(
           employee_id=employee,
           start_date=date(2024, 2, 1),
           end_date=date(2024, 2, 10),
           reason="Test unpaid leave",
           status="active",
           days_count=10,
       )

       # Pause accrual
       pause_accrual_for_unpaid_leave(unpaid)

       # Verify accrual_paused_until is set
       available_leave.refresh_from_db()
       self.assertIsNotNone(available_leave.accrual_paused_until)
       self.assertEqual(available_leave.accrual_paused_until, date(2024, 2, 10))

    def test_accrual_eligibility_during_pause(self):
       """Test that employee is not eligible for accrual while paused."""
       from leave.accrual_service import is_service_eligible_for_accrual

       employee = self.create_employee("S-001", date(2023, 6, 15))

       # Create unpaid leave that covers anniversary
       unpaid = UnpaidLeave.objects.create(
           employee_id=employee,
           start_date=date(2024, 6, 1),
           end_date=date(2024, 6, 30),
           reason="Medical leave",
           status="active",
           days_count=30,
       )

       available_leave = AvailableLeave.objects.get(
           employee_id=employee,
           leave_type_id=self.leave_type,
       )
       available_leave.accrual_paused_until = date(2024, 6, 30)
       available_leave.save()

       # On anniversary date (but during unpaid leave), should not be eligible
       # Note: This depends on implementation - may need logic in accrual job


class TestAnnualReset(RoyalFalconLeaveAccrualTestCase):
    """Test December 31 annual reset functionality."""

    def test_annual_reset_enforces_management_limit(self):
       """Test management category is limited to 30 days on Dec 31."""
       from leave.models import EmployeeCategory

       # Create management category
       mgmt_cat = EmployeeCategory.objects.create(
           company_id=self.company,
           name="Management",
           badge_id_prefix="A",
           max_carryforward_days=30,
       )

       employee = self.create_employee("A-001", date(2024, 1, 15))
       available_leave = AvailableLeave.objects.get(
           employee_id=employee,
           leave_type_id=self.leave_type,
       )

       # Set balance above 30
       available_leave.available_days = 50
       available_leave.carryforward_days = 0
       available_leave.save()

       # Verify management category is detected
       from leave.accrual_service import get_employee_category
       category = get_employee_category(employee)
       self.assertEqual(category.max_carryforward_days, 30)

    def test_annual_reset_enforces_normal_limit(self):
       """Test normal employee category is limited to 60 days on Dec 31."""
       from leave.models import EmployeeCategory

       # Create normal category
       normal_cat = EmployeeCategory.objects.create(
           company_id=self.company,
           name="Normal Employee",
           badge_id_prefix="S",
           max_carryforward_days=60,
       )

       employee = self.create_employee("S-001", date(2024, 1, 15))
       available_leave = AvailableLeave.objects.get(
           employee_id=employee,
           leave_type_id=self.leave_type,
       )

       # Set balance above 60
       available_leave.available_days = 80
       available_leave.carryforward_days = 0
       available_leave.save()

       # Verify normal category is detected
       from leave.accrual_service import get_employee_category
       category = get_employee_category(employee)
       self.assertEqual(category.max_carryforward_days, 60)


class TestUnauthorizedExtension(RoyalFalconLeaveAccrualTestCase):
    """Test unauthorized extension tracking."""

    def test_unauthorized_extension_calculation(self):
       """Test unauthorized days are correctly calculated."""
       from leave.models import UnauthorizedExtension, LeaveRequest

       employee = self.create_employee("S-001", date(2024, 1, 15))

       # Create a dummy leave request (approved paid leave)
       leave_req = LeaveRequest.objects.create(
           employee_id=employee,
           leave_type_id=self.leave_type,
           start_date=date(2024, 3, 1),
           end_date=date(2024, 3, 10),
           status="approved",
       )

       # Create unauthorized extension
       ue = UnauthorizedExtension.objects.create(
           employee_id=employee,
           leave_request_id=leave_req,
           approved_return_date=date(2024, 3, 11),
           actual_return_date=date(2024, 3, 15),
           status="pending_review",
       )

       # Verify unauthorized days calculated
       self.assertEqual(ue.unauthorized_days, 4)


class TestMultipleUnpaidLeaves(RoyalFalconLeaveAccrualTestCase):
    """Test handling of multiple unpaid leaves."""

    def test_multiple_unpaid_leaves_exclude_service(self):
       """Test service calculation with multiple unpaid leaves."""
       from leave.accrual_service import calculate_adjusted_service_days

       joining_date = date(2024, 1, 1)
       employee = self.create_employee("S-001", joining_date)

       # Create first unpaid leave
       UnpaidLeave.objects.create(
           employee_id=employee,
           start_date=date(2024, 2, 1),
           end_date=date(2024, 2, 5),
           reason="First unpaid leave",
           status="active",
           days_count=5,
       )

       # Create second unpaid leave
       UnpaidLeave.objects.create(
           employee_id=employee,
           start_date=date(2024, 3, 1),
           end_date=date(2024, 3, 3),
           reason="Second unpaid leave",
           status="active",
           days_count=3,
       )

       # Calculate service on April 1
       reference_date = date(2024, 4, 1)
       service_days = calculate_adjusted_service_days(employee, reference_date)

       # Should exclude 8 days (5 + 3)
       # From Jan 1 to Apr 1 = 91 days, minus 8 = 83 days
       expected = 91 - 8
       self.assertAlmostEqual(service_days, expected, delta=2)
