"""Shared fixtures for leave holiday filter tests."""

from datetime import date, timedelta

from base.models import Company, EmployeeShift, Holidays, WorkType
from employee.models import Employee, EmployeeWorkInformation


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
