"""
Factory Boy factories for leave module models.

Usage:
    leave_type = LeaveTypeFactory()
    available = AvailableLeaveFactory(employee_id=emp)
    request = LeaveRequestFactory(employee_id=emp, leave_type_id=leave_type)
    allocation = LeaveAllocationRequestFactory(employee_id=emp)
    restrict = RestrictLeaveFactory(department=dept)
"""

from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory

from base.tests.factories import CompanyFactory, DepartmentFactory
from employee.tests.factories import EmployeeFactory
from leave.models import (
    AvailableLeave,
    LeaveAllocationRequest,
    LeaveRequest,
    LeaveType,
    RestrictLeave,
)


class LeaveTypeFactory(DjangoModelFactory):
    class Meta:
        model = LeaveType

    name = factory.Sequence(lambda n: f"Leave Type {n}")
    payment = "paid"
    total_days = 10
    reset = False
    company_id = factory.SubFactory(CompanyFactory)


class AvailableLeaveFactory(DjangoModelFactory):
    class Meta:
        model = AvailableLeave

    employee_id = factory.SubFactory(EmployeeFactory)
    leave_type_id = factory.SubFactory(LeaveTypeFactory)
    available_days = 10


class LeaveRequestFactory(DjangoModelFactory):
    class Meta:
        model = LeaveRequest

    employee_id = factory.SubFactory(EmployeeFactory)
    leave_type_id = factory.SubFactory(LeaveTypeFactory)
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=2))
    start_date_breakdown = "full_day"
    end_date_breakdown = "full_day"
    description = factory.Faker("sentence")
    status = "requested"


class LeaveAllocationRequestFactory(DjangoModelFactory):
    class Meta:
        model = LeaveAllocationRequest

    employee_id = factory.SubFactory(EmployeeFactory)
    leave_type_id = factory.SubFactory(LeaveTypeFactory)
    requested_days = 5
    description = factory.Faker("sentence")
    status = "requested"


class RestrictLeaveFactory(DjangoModelFactory):
    class Meta:
        model = RestrictLeave

    title = factory.Sequence(lambda n: f"Restriction {n}")
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))
    department = factory.SubFactory(DepartmentFactory)
