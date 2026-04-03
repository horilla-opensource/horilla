"""
Unit tests for base module models.

Covers CRUD, validation, constraints, __str__, FK relationships,
state transitions, and edge cases for the core HR configuration models.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.utils import timezone

from base.models import (
    Company,
    CompanyLeaves,
    Department,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeType,
    Holidays,
    JobPosition,
    JobRole,
    ShiftRequest,
    Tags,
    WorkType,
    WorkTypeRequest,
    validate_time_format,
)
from base.tests.factories import (
    CompanyFactory,
    CompanyLeavesFactory,
    DepartmentFactory,
    EmployeeShiftFactory,
    HolidaysFactory,
    JobPositionFactory,
    JobRoleFactory,
    TagsFactory,
    WorkTypeFactory,
)
from horilla.horilla_middlewares import _thread_locals
from horilla.test_utils.base import HorillaTestCase


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class CompanyModelTests(HorillaTestCase):
    """Tests for the Company model."""

    def test_create_company(self):
        """Company can be created with all required fields."""
        company = CompanyFactory()
        self.assertIsNotNone(company.pk)
        self.assertFalse(company.hq)

    def test_str_returns_company_name(self):
        """__str__ returns the company name."""
        company = CompanyFactory(company="Acme Corp")
        self.assertEqual(str(company), "Acme Corp")

    def test_hq_flag(self):
        """Company can be marked as headquarters."""
        company = CompanyFactory(hq=True)
        self.assertTrue(company.hq)

    def test_update_company(self):
        """Company fields can be updated."""
        company = CompanyFactory(company="Old Name")
        company.company = "New Name"
        company.save()
        company.refresh_from_db()
        self.assertEqual(company.company, "New Name")

    def test_delete_company(self):
        """Company can be deleted."""
        company = CompanyFactory()
        pk = company.pk
        company.delete()
        self.assertFalse(Company.objects.filter(pk=pk).exists())

    def test_unique_together_company_address(self):
        """Same company name + address combination raises IntegrityError."""
        CompanyFactory(company="UniCorp", address="123 Main St")
        with self.assertRaises(IntegrityError):
            CompanyFactory(company="UniCorp", address="123 Main St")

    def test_unique_together_allows_different_address(self):
        """Same company name with different address is allowed."""
        CompanyFactory(company="UniCorp", address="123 Main St")
        c2 = CompanyFactory(company="UniCorp", address="456 Other St")
        self.assertIsNotNone(c2.pk)

    def test_date_format_nullable(self):
        """date_format and time_format can be null."""
        company = CompanyFactory()
        self.assertIsNone(company.date_format)
        self.assertIsNone(company.time_format)

    def test_company_max_length(self):
        """Company name is capped at 50 characters."""
        long_name = "A" * 51
        company = Company(
            company=long_name,
            address="addr",
            country="US",
            state="CA",
            city="SF",
            zip="00000",
        )
        # HorillaModel.clean_fields() only checks XSS and doesn't call
        # super().clean_fields(), so Django's max_length/blank validators
        # never run via full_clean(). Call the base clean_fields() directly
        # to verify the field constraint is properly declared.
        with self.assertRaises(ValidationError):
            models.Model.clean_fields(company)


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
class DepartmentModelTests(HorillaTestCase):
    """Tests for the Department model."""

    def test_create_department(self):
        """Department can be created."""
        dept = DepartmentFactory()
        self.assertIsNotNone(dept.pk)

    def test_str_returns_department_name(self):
        """__str__ returns department name."""
        dept = DepartmentFactory(department="Finance")
        self.assertEqual(str(dept), "Finance")

    def test_m2m_company_assignment(self):
        """Department can be assigned to multiple companies."""
        company_a = CompanyFactory()
        company_b = CompanyFactory()
        dept = DepartmentFactory(company_id=[company_a, company_b])
        self.assertEqual(dept.company_id.count(), 2)
        self.assertIn(company_a, dept.company_id.all())
        self.assertIn(company_b, dept.company_id.all())

    def test_department_blank_name_fails(self):
        """Department with blank name fails validation."""
        dept = Department(department="")
        # HorillaModel.clean_fields() only checks XSS and doesn't call
        # super().clean_fields(), so blank=False is never enforced via
        # full_clean(). Call the base clean_fields() to verify the
        # field constraint is properly declared on the model.
        with self.assertRaises(ValidationError):
            models.Model.clean_fields(dept)

    def test_update_department(self):
        """Department name can be updated."""
        dept = DepartmentFactory(department="Old Dept")
        dept.department = "New Dept"
        dept.save()
        dept.refresh_from_db()
        self.assertEqual(dept.department, "New Dept")

    def test_delete_department(self):
        """Department can be deleted when not referenced by FK."""
        dept = DepartmentFactory()
        pk = dept.pk
        dept.delete()
        self.assertFalse(Department.objects.filter(pk=pk).exists())


# ---------------------------------------------------------------------------
# JobPosition
# ---------------------------------------------------------------------------
class JobPositionModelTests(HorillaTestCase):
    """Tests for the JobPosition model."""

    def test_create_job_position(self):
        """JobPosition is created with a department FK."""
        jp = JobPositionFactory()
        self.assertIsNotNone(jp.pk)
        self.assertIsNotNone(jp.department_id)

    def test_str_includes_department(self):
        """__str__ includes the department name in parentheses."""
        dept = DepartmentFactory(department="Engineering")
        jp = JobPositionFactory(job_position="Backend Dev", department_id=dept)
        self.assertIn("Backend Dev", str(jp))
        self.assertIn("Engineering", str(jp))

    def test_fk_department_protect(self):
        """Deleting department with linked JobPosition raises ProtectedError."""
        dept = DepartmentFactory()
        JobPositionFactory(department_id=dept)
        with self.assertRaises(Exception):
            # PROTECT prevents deletion
            dept.delete()

    def test_update_job_position(self):
        """JobPosition name can be updated."""
        jp = JobPositionFactory(job_position="Old Position")
        jp.job_position = "New Position"
        jp.save()
        jp.refresh_from_db()
        self.assertEqual(jp.job_position, "New Position")


# ---------------------------------------------------------------------------
# JobRole
# ---------------------------------------------------------------------------
class JobRoleModelTests(HorillaTestCase):
    """Tests for the JobRole model."""

    def test_create_job_role(self):
        """JobRole is created with a job position FK."""
        jr = JobRoleFactory()
        self.assertIsNotNone(jr.pk)
        self.assertIsNotNone(jr.job_position_id)

    def test_str_format(self):
        """__str__ returns 'role - position' format."""
        dept = DepartmentFactory(department="Engineering")
        jp = JobPositionFactory(job_position="Developer", department_id=dept)
        jr = JobRoleFactory(job_role="Senior Dev", job_position_id=jp)
        self.assertEqual(str(jr), "Senior Dev - Developer")

    def test_unique_together_job_role(self):
        """Same job_role + job_position_id raises IntegrityError."""
        jp = JobPositionFactory()
        JobRoleFactory(job_role="Analyst", job_position_id=jp)
        with self.assertRaises(IntegrityError):
            JobRoleFactory(job_role="Analyst", job_position_id=jp)

    def test_unique_together_allows_different_position(self):
        """Same role name under different positions is allowed."""
        jp1 = JobPositionFactory()
        jp2 = JobPositionFactory()
        JobRoleFactory(job_role="Lead", job_position_id=jp1)
        jr2 = JobRoleFactory(job_role="Lead", job_position_id=jp2)
        self.assertIsNotNone(jr2.pk)

    def test_fk_chain_department_to_role(self):
        """Full FK chain from department to job role is accessible."""
        dept = DepartmentFactory(department="Sales")
        jp = JobPositionFactory(job_position="Account Exec", department_id=dept)
        jr = JobRoleFactory(job_role="Key Accounts", job_position_id=jp)
        self.assertEqual(jr.job_position_id.department_id.department, "Sales")


# ---------------------------------------------------------------------------
# WorkType
# ---------------------------------------------------------------------------
class WorkTypeModelTests(HorillaTestCase):
    """Tests for the WorkType model."""

    def test_create_work_type(self):
        """WorkType can be created."""
        wt = WorkTypeFactory()
        self.assertIsNotNone(wt.pk)

    def test_str_returns_work_type_name(self):
        """__str__ returns the work type name."""
        wt = WorkTypeFactory(work_type="Remote")
        self.assertEqual(str(wt), "Remote")

    def test_update_work_type(self):
        """WorkType can be updated."""
        wt = WorkTypeFactory(work_type="Office")
        wt.work_type = "Hybrid"
        wt.save()
        wt.refresh_from_db()
        self.assertEqual(wt.work_type, "Hybrid")

    def test_delete_work_type(self):
        """WorkType can be deleted when not referenced."""
        wt = WorkTypeFactory()
        pk = wt.pk
        wt.delete()
        self.assertFalse(WorkType.objects.filter(pk=pk).exists())


# ---------------------------------------------------------------------------
# EmployeeType
# ---------------------------------------------------------------------------
class EmployeeTypeModelTests(HorillaTestCase):
    """Tests for the EmployeeType model."""

    def test_create_employee_type(self):
        """EmployeeType can be created."""
        et = EmployeeType.objects.create(employee_type="Full-time")
        self.assertIsNotNone(et.pk)

    def test_str_returns_employee_type(self):
        """__str__ returns the employee type string."""
        et = EmployeeType.objects.create(employee_type="Contract")
        self.assertEqual(str(et), "Contract")


# ---------------------------------------------------------------------------
# EmployeeShift
# ---------------------------------------------------------------------------
class EmployeeShiftModelTests(HorillaTestCase):
    """Tests for the EmployeeShift model."""

    def test_create_shift(self):
        """EmployeeShift can be created with defaults."""
        shift = EmployeeShiftFactory()
        self.assertIsNotNone(shift.pk)
        self.assertEqual(shift.weekly_full_time, "40:00")
        self.assertEqual(shift.full_time, "200:00")

    def test_str_returns_shift_name(self):
        """__str__ returns the shift name."""
        shift = EmployeeShiftFactory(employee_shift="Morning Shift")
        self.assertEqual(str(shift), "Morning Shift")

    def test_update_shift(self):
        """EmployeeShift fields can be updated."""
        shift = EmployeeShiftFactory(employee_shift="Day")
        shift.employee_shift = "Night"
        shift.save()
        shift.refresh_from_db()
        self.assertEqual(shift.employee_shift, "Night")

    def test_weekly_full_time_validation(self):
        """Invalid weekly_full_time format raises ValidationError."""
        shift = EmployeeShift(
            employee_shift="Bad Shift",
            weekly_full_time="invalid",
            full_time="200:00",
        )
        # HorillaModel.clean_fields() only checks XSS and doesn't call
        # super().clean_fields(), so field validators never run via
        # full_clean(). Call the base clean_fields() to verify the
        # validate_time_format validator is properly declared.
        with self.assertRaises(ValidationError):
            models.Model.clean_fields(shift)

    def test_full_time_validation(self):
        """Invalid full_time format raises ValidationError."""
        shift = EmployeeShift(
            employee_shift="Bad Shift",
            weekly_full_time="40:00",
            full_time="nottime",
        )
        # HorillaModel.clean_fields() only checks XSS and doesn't call
        # super().clean_fields(), so field validators never run via
        # full_clean(). Call the base clean_fields() directly.
        with self.assertRaises(ValidationError):
            models.Model.clean_fields(shift)


# ---------------------------------------------------------------------------
# validate_time_format
# ---------------------------------------------------------------------------
class ValidateTimeFormatTests(HorillaTestCase):
    """Tests for the validate_time_format validator function."""

    def test_valid_format(self):
        """Valid HH:MM format does not raise."""
        validate_time_format("08:30")
        validate_time_format("40:00")
        validate_time_format("200:00")

    def test_invalid_minutes(self):
        """Minutes >= 60 raises ValidationError."""
        with self.assertRaises(ValidationError):
            validate_time_format("08:60")

    def test_missing_colon(self):
        """Missing colon raises ValidationError."""
        with self.assertRaises(ValidationError):
            validate_time_format("0830")

    def test_too_long_value(self):
        """Value exceeding 6 characters raises ValidationError."""
        with self.assertRaises(ValidationError):
            validate_time_format("1000:00")

    def test_non_numeric(self):
        """Non-numeric input raises ValidationError."""
        with self.assertRaises(ValidationError):
            validate_time_format("ab:cd")


# ---------------------------------------------------------------------------
# EmployeeShiftDay
# ---------------------------------------------------------------------------
class EmployeeShiftDayModelTests(HorillaTestCase):
    """Tests for the EmployeeShiftDay model."""

    def test_create_shift_day(self):
        """EmployeeShiftDay can be created."""
        day = EmployeeShiftDay.objects.create(day="monday")
        self.assertIsNotNone(day.pk)

    def test_str_returns_capitalized_day(self):
        """__str__ returns the day name capitalized."""
        day = EmployeeShiftDay.objects.create(day="monday")
        result = str(day)
        # The model does _(self.day).capitalize(), so it should be capitalized
        self.assertTrue(result[0].isupper())


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
class TagsModelTests(HorillaTestCase):
    """Tests for the Tags model."""

    def test_create_tag(self):
        """Tag can be created with title and color."""
        tag = TagsFactory()
        self.assertIsNotNone(tag.pk)
        self.assertEqual(tag.color, "#3498db")

    def test_str_returns_title(self):
        """__str__ returns the tag title."""
        tag = TagsFactory(title="Urgent")
        self.assertEqual(str(tag), "Urgent")

    def test_update_tag(self):
        """Tag fields can be updated."""
        tag = TagsFactory(title="Old", color="#000000")
        tag.title = "New"
        tag.color = "#ffffff"
        tag.save()
        tag.refresh_from_db()
        self.assertEqual(tag.title, "New")
        self.assertEqual(tag.color, "#ffffff")

    def test_delete_tag(self):
        """Tag can be deleted."""
        tag = TagsFactory()
        pk = tag.pk
        tag.delete()
        self.assertFalse(Tags.objects.filter(pk=pk).exists())

    def test_title_max_length(self):
        """Title exceeding 30 chars fails validation."""
        tag = Tags(title="A" * 31, color="#000")
        # HorillaModel.clean_fields() only checks XSS and doesn't call
        # super().clean_fields(), so max_length is never enforced via
        # full_clean(). Call the base clean_fields() directly.
        with self.assertRaises(ValidationError):
            models.Model.clean_fields(tag)


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------
class HolidaysModelTests(HorillaTestCase):
    """Tests for the Holidays model."""

    def test_create_holiday(self):
        """Holiday can be created with start and end dates."""
        today = date.today()
        holiday = Holidays.objects.create(
            name="New Year",
            start_date=today,
            end_date=today + timedelta(days=1),
        )
        self.assertIsNotNone(holiday.pk)

    def test_str_returns_name(self):
        """__str__ returns the holiday name."""
        holiday = HolidaysFactory(name="Christmas")
        self.assertEqual(str(holiday), "Christmas")

    def test_recurring_flag(self):
        """Holiday can be set as recurring."""
        holiday = HolidaysFactory(recurring=True)
        self.assertTrue(holiday.recurring)

    def test_end_date_nullable(self):
        """end_date can be null."""
        holiday = Holidays.objects.create(
            name="Single Day",
            start_date=date.today(),
            end_date=None,
        )
        self.assertIsNone(holiday.end_date)

    def test_today_holidays_returns_matching(self):
        """today_holidays() returns holidays that overlap the given date."""
        today = date.today()
        holiday = Holidays.objects.create(
            name="Today Holiday",
            start_date=today,
            end_date=today,
        )
        result = Holidays.today_holidays(today)
        self.assertIn(holiday, result)

    def test_today_holidays_excludes_non_matching(self):
        """today_holidays() excludes holidays outside the date range."""
        today = date.today()
        Holidays.objects.create(
            name="Past Holiday",
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=29),
        )
        result = Holidays.today_holidays(today)
        self.assertEqual(result.count(), 0)

    def test_get_recurring_status_yes(self):
        """get_recurring_status returns 'Yes' for recurring holidays."""
        holiday = HolidaysFactory(recurring=True)
        # Returns a lazy string; cast to str for comparison
        self.assertEqual(str(holiday.get_recurring_status()), "Yes")

    def test_get_recurring_status_no(self):
        """get_recurring_status returns 'No' for non-recurring holidays."""
        holiday = HolidaysFactory(recurring=False)
        self.assertEqual(str(holiday.get_recurring_status()), "No")

    def test_holiday_with_company_fk(self):
        """Holiday can be associated with a company."""
        company = CompanyFactory()
        holiday = Holidays.objects.create(
            name="Company Holiday",
            start_date=date.today(),
            end_date=date.today(),
            company_id=company,
        )
        self.assertEqual(holiday.company_id, company)


# ---------------------------------------------------------------------------
# CompanyLeaves
# ---------------------------------------------------------------------------
class CompanyLeavesModelTests(HorillaTestCase):
    """Tests for the CompanyLeaves model."""

    def test_create_company_leave(self):
        """CompanyLeaves can be created."""
        leave = CompanyLeavesFactory()
        self.assertIsNotNone(leave.pk)

    def test_str_format(self):
        """__str__ returns 'DayName | WeekName' format."""
        leave = CompanyLeaves.objects.create(
            based_on_week="0",
            based_on_week_day="0",
        )
        result = str(leave)
        self.assertIn("Monday", result)
        self.assertIn("First Week", result)

    def test_unique_together_week_and_day(self):
        """Same week + day combination raises IntegrityError."""
        CompanyLeaves.objects.create(based_on_week="0", based_on_week_day="0")
        with self.assertRaises(IntegrityError):
            CompanyLeaves.objects.create(based_on_week="0", based_on_week_day="0")

    def test_unique_together_allows_different_combo(self):
        """Different week + day combinations are allowed."""
        CompanyLeaves.objects.create(based_on_week="0", based_on_week_day="0")
        cl2 = CompanyLeaves.objects.create(based_on_week="1", based_on_week_day="0")
        self.assertIsNotNone(cl2.pk)


# ---------------------------------------------------------------------------
# WorkTypeRequest
# ---------------------------------------------------------------------------
class WorkTypeRequestModelTests(HorillaTestCase):
    """Tests for the WorkTypeRequest model."""

    def _make_request(self, **overrides):
        """Helper to create a WorkTypeRequest with sensible defaults."""
        wt = WorkTypeFactory()
        defaults = {
            "employee_id": self.admin_employee,
            "work_type_id": wt,
            "requested_date": date.today(),
            "requested_till": date.today() + timedelta(days=5),
            "description": "Need remote work",
            "is_permanent_work_type": False,
            "approved": False,
            "canceled": False,
        }
        defaults.update(overrides)
        return WorkTypeRequest.objects.create(**defaults)

    def test_create_work_type_request(self):
        """WorkTypeRequest can be created with default status."""
        req = self._make_request()
        self.assertIsNotNone(req.pk)
        self.assertFalse(req.approved)
        self.assertFalse(req.canceled)

    def test_request_status_requested(self):
        """request_status returns 'Requested' when neither approved nor canceled."""
        req = self._make_request()
        self.assertEqual(str(req.request_status()), "Requested")

    def test_request_status_approved(self):
        """request_status returns 'Approved' when approved=True."""
        req = self._make_request(approved=True)
        self.assertEqual(str(req.request_status()), "Approved")

    def test_request_status_rejected(self):
        """request_status returns 'Rejected' when canceled=True."""
        req = self._make_request(canceled=True)
        self.assertEqual(str(req.request_status()), "Rejected")

    def test_delete_unapproved_request(self):
        """Unapproved request can be deleted."""
        req = self._make_request(approved=False)
        pk = req.pk
        req.delete()
        self.assertFalse(WorkTypeRequest.objects.filter(pk=pk).exists())

    def test_delete_approved_request_blocked(self):
        """Approved request cannot be deleted (stays in DB)."""
        req = self._make_request(approved=True)
        pk = req.pk
        # The custom delete() tries messages.warning(request, ...) when
        # _thread_locals.request exists, but the test mock doesn't support
        # Django messages middleware. Clear the request so delete() takes
        # the silent no-op path (no request → no messages → no super).
        if hasattr(_thread_locals, "request"):
            saved_request = _thread_locals.request
            del _thread_locals.request
        else:
            saved_request = None
        try:
            req.delete()
        finally:
            if saved_request is not None:
                _thread_locals.request = saved_request
        # The custom delete() does not call super() for approved requests
        self.assertTrue(WorkTypeRequest.objects.filter(pk=pk).exists())

    def test_is_permanent_display(self):
        """is_permanent_work_type_display returns Yes/No string."""
        req = self._make_request(is_permanent_work_type=True)
        self.assertEqual(str(req.is_permanent_work_type_display()), "Yes")

        req2 = self._make_request(is_permanent_work_type=False)
        self.assertEqual(str(req2.is_permanent_work_type_display()), "No")


# ---------------------------------------------------------------------------
# ShiftRequest
# ---------------------------------------------------------------------------
class ShiftRequestModelTests(HorillaTestCase):
    """Tests for the ShiftRequest model."""

    def _make_request(self, **overrides):
        """Helper to create a ShiftRequest with sensible defaults."""
        shift = EmployeeShiftFactory()
        defaults = {
            "employee_id": self.admin_employee,
            "shift_id": shift,
            "requested_date": date.today(),
            "requested_till": date.today() + timedelta(days=5),
            "description": "Need shift change",
            "is_permanent_shift": False,
            "approved": False,
            "canceled": False,
        }
        defaults.update(overrides)
        return ShiftRequest.objects.create(**defaults)

    def test_create_shift_request(self):
        """ShiftRequest can be created."""
        req = self._make_request()
        self.assertIsNotNone(req.pk)
        self.assertFalse(req.approved)

    def test_request_status_requested(self):
        """request_status returns 'Requested' by default."""
        req = self._make_request()
        self.assertEqual(str(req.request_status()), "Requested")

    def test_request_status_approved(self):
        """request_status returns 'Approved' when approved."""
        req = self._make_request(approved=True)
        self.assertEqual(str(req.request_status()), "Approved")

    def test_request_status_rejected(self):
        """request_status returns 'Rejected' when canceled."""
        req = self._make_request(canceled=True)
        self.assertEqual(str(req.request_status()), "Rejected")

    def test_is_permanent_display(self):
        """is_permanent returns Yes/No lazy string."""
        req = self._make_request(is_permanent_shift=True)
        self.assertEqual(str(req.is_permanent()), "Yes")

    def test_delete_unapproved_request(self):
        """Unapproved shift request can be deleted."""
        req = self._make_request(approved=False)
        pk = req.pk
        req.delete()
        self.assertFalse(ShiftRequest.objects.filter(pk=pk).exists())

    def test_delete_approved_request_blocked(self):
        """Approved shift request cannot be deleted."""
        req = self._make_request(approved=True)
        pk = req.pk
        # The custom delete() tries messages.warning(request, ...) when
        # _thread_locals.request exists, but the test mock doesn't support
        # Django messages middleware. Clear the request so delete() takes
        # the silent no-op path (no request → no messages → no super).
        if hasattr(_thread_locals, "request"):
            saved_request = _thread_locals.request
            del _thread_locals.request
        else:
            saved_request = None
        try:
            req.delete()
        finally:
            if saved_request is not None:
                _thread_locals.request = saved_request
        self.assertTrue(ShiftRequest.objects.filter(pk=pk).exists())
