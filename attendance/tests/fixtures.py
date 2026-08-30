"""Shared fixtures for attendance holiday tests."""

from datetime import date, timedelta

from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeShiftDay,
    Holidays,
    WorkType,
)
from employee.models import Employee, EmployeeWorkInformation


def _months_before(anchor_date, months):
    """Return the 1st of the month `months` before `anchor_date` (day-safe)."""
    month_index = anchor_date.year * 12 + (anchor_date.month - 1) - months
    return date(month_index // 12, month_index % 12 + 1, 1)


class HolidayFixtureMixin:
    """
    Creates two employees, a global holiday, and an employee-specific holiday.
    All holiday dates are in the past so attendance records can be created on them.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company="Test Corp",
            hq=True,
            address="1 Test St",
            country="US",
            state="CA",
            city="LA",
            zip="90001",
        )

        cls.shift = EmployeeShift.objects.create(employee_shift="Day Shift")
        cls.shift.company_id.add(cls.company)

        cls.work_type = WorkType.objects.create(work_type="Office")
        cls.work_type.company_id.add(cls.company)

        cls.dept = Department.objects.create(department="Engineering")
        cls.dept.company_id.add(cls.company)

        cls.shift_day = EmployeeShiftDay.objects.filter(day="monday").first()

        cls.emp_a = cls._make_employee("emp_a@holiday.test", "Alice", "Holiday")
        cls.emp_b = cls._make_employee("emp_b@holiday.test", "Bob", "Holiday")

        # Dates well in the past to satisfy attendance_date_validate.
        #
        # The export query these fixtures exercise filters holidays by month and
        # year, not by exact date, so global_date and specific_date must land in
        # different months or a "global holiday must not appear" assertion sees
        # the specific one and fails. Plain day offsets do not guarantee that:
        # today - 60d and today - 30d share a month on roughly 2% of calendar
        # days (e.g. 2026-08-30 puts both in July), which made the suite fail
        # only on those dates. Anchor to the first of a month and step back in
        # whole months so the separation holds on every run.
        first_of_month = date.today().replace(day=1)
        cls.global_date = _months_before(first_of_month, 3)
        cls.specific_date = _months_before(first_of_month, 2)
        cls.normal_date = _months_before(first_of_month, 1)

        # Global holiday — is_specific=False, applies to all employees
        cls.global_holiday = Holidays.objects.create(
            name="Global Holiday",
            start_date=cls.global_date,
            end_date=cls.global_date,
            is_specific=False,
            company_id=cls.company,
        )

        # Specific holiday — is_specific=True, assigned only to emp_a
        cls.specific_holiday = Holidays.objects.create(
            name="Specific Holiday",
            start_date=cls.specific_date,
            end_date=cls.specific_date,
            is_specific=True,
            assigning_type="employee",
            company_id=cls.company,
        )
        cls.specific_holiday.employees.add(cls.emp_a)

    @classmethod
    def _make_employee(cls, email, first_name, last_name):
        emp = Employee.objects.create(
            employee_first_name=first_name,
            employee_last_name=last_name,
            email=email,
            phone="9999999999",
        )
        EmployeeWorkInformation.objects.filter(employee_id=emp).update(
            company_id_id=cls.company.pk,
            shift_id_id=cls.shift.pk,
            work_type_id_id=cls.work_type.pk,
        )
        return emp
