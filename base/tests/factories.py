"""
Factory Boy factories for base module models.
"""

import factory
from factory.django import DjangoModelFactory

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
    Tags,
    WorkType,
)


class CompanyFactory(DjangoModelFactory):
    class Meta:
        model = Company

    company = factory.Sequence(lambda n: f"Company {n}")
    address = factory.Faker("address")
    country = factory.Faker("country")
    state = factory.Faker("state")
    city = factory.Faker("city")
    zip = factory.Faker("zipcode")
    hq = False


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    department = factory.Sequence(lambda n: f"Department {n}")

    @factory.post_generation
    def company_id(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for company in extracted:
                self.company_id.add(company)


class JobPositionFactory(DjangoModelFactory):
    class Meta:
        model = JobPosition

    job_position = factory.Sequence(lambda n: f"Position {n}")
    department_id = factory.SubFactory(DepartmentFactory)


class JobRoleFactory(DjangoModelFactory):
    class Meta:
        model = JobRole

    job_role = factory.Sequence(lambda n: f"Role {n}")
    job_position_id = factory.SubFactory(JobPositionFactory)


class WorkTypeFactory(DjangoModelFactory):
    class Meta:
        model = WorkType

    work_type = factory.Sequence(lambda n: f"WorkType {n}")


class EmployeeTypeFactory(DjangoModelFactory):
    class Meta:
        model = EmployeeType

    employee_type = factory.Sequence(lambda n: f"EmpType {n}")


class EmployeeShiftDayFactory(DjangoModelFactory):
    class Meta:
        model = EmployeeShiftDay

    day = "monday"


class EmployeeShiftFactory(DjangoModelFactory):
    class Meta:
        model = EmployeeShift

    employee_shift = factory.Sequence(lambda n: f"Shift {n}")


class TagsFactory(DjangoModelFactory):
    class Meta:
        model = Tags

    title = factory.Sequence(lambda n: f"Tag {n}")
    color = "#3498db"


class HolidaysFactory(DjangoModelFactory):
    class Meta:
        model = Holidays

    name = factory.Sequence(lambda n: f"Holiday {n}")
    start_date = factory.Faker("date_this_year")
    end_date = factory.LazyAttribute(lambda o: o.start_date)


class CompanyLeavesFactory(DjangoModelFactory):
    class Meta:
        model = CompanyLeaves

    based_on_week = "0"
    based_on_week_day = "0"
