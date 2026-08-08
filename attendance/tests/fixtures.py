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

        # Dates well in the past to satisfy attendance_date_validate
        cls.global_date = date.today() - timedelta(days=60)
        cls.specific_date = date.today() - timedelta(days=30)
        cls.normal_date = date.today() - timedelta(days=10)

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
