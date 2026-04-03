"""
Factory Boy factories for attendance module models.

Usage:
    attendance = AttendanceFactory(employee_id=emp)
    activity = AttendanceActivityFactory(employee_id=emp)
    overtime = AttendanceOverTimeFactory(employee_id=emp)
    work_record = WorkRecordFactory(employee_id=emp)
    grace_time = GraceTimeFactory()
"""

from datetime import date, time, timedelta

import factory
from factory.django import DjangoModelFactory

from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceLateComeEarlyOut,
    AttendanceOverTime,
    AttendanceValidationCondition,
    GraceTime,
    WorkRecords,
)
from employee.tests.factories import EmployeeFactory


class AttendanceActivityFactory(DjangoModelFactory):
    class Meta:
        model = AttendanceActivity

    employee_id = factory.SubFactory(EmployeeFactory)
    attendance_date = factory.LazyFunction(date.today)
    clock_in_date = factory.LazyAttribute(lambda o: o.attendance_date)
    clock_in = factory.LazyFunction(lambda: time(9, 0))
    clock_out_date = factory.LazyAttribute(lambda o: o.attendance_date)
    clock_out = factory.LazyFunction(lambda: time(17, 0))


class AttendanceFactory(DjangoModelFactory):
    class Meta:
        model = Attendance

    employee_id = factory.SubFactory(EmployeeFactory)
    attendance_date = factory.LazyFunction(date.today)
    attendance_clock_in_date = factory.LazyAttribute(lambda o: o.attendance_date)
    attendance_clock_in = factory.LazyFunction(lambda: time(9, 0))
    attendance_clock_out_date = factory.LazyAttribute(lambda o: o.attendance_date)
    attendance_clock_out = factory.LazyFunction(lambda: time(17, 0))
    attendance_worked_hour = "08:00"
    minimum_hour = "08:00"


class AttendanceOverTimeFactory(DjangoModelFactory):
    class Meta:
        model = AttendanceOverTime

    employee_id = factory.SubFactory(EmployeeFactory)
    month = "january"
    year = factory.LazyFunction(lambda: str(date.today().year))
    hour_account_second = 28800  # 8 hours
    hour_pending_second = 0
    overtime_second = 3600  # 1 hour


class AttendanceLateComeEarlyOutFactory(DjangoModelFactory):
    class Meta:
        model = AttendanceLateComeEarlyOut

    attendance_id = factory.SubFactory(AttendanceFactory)
    type = "late_come"


class AttendanceValidationConditionFactory(DjangoModelFactory):
    class Meta:
        model = AttendanceValidationCondition

    validation_at_work = "08:00"
    minimum_overtime_to_approve = "00:30"


class GraceTimeFactory(DjangoModelFactory):
    class Meta:
        model = GraceTime

    allowed_time = "00:15:00"
    allowed_time_in_secs = 900
    allowed_clock_in = True
    allowed_clock_out = False
    is_default = False


class WorkRecordFactory(DjangoModelFactory):
    class Meta:
        model = WorkRecords

    employee_id = factory.SubFactory(EmployeeFactory)
    date = factory.LazyFunction(date.today)
    work_record_type = "CONF"
    at_work = "08:00"
    min_hour = "08:00"
    at_work_second = 28800
    min_hour_second = 28800
    note = "Auto-generated test work record"
    day_percentage = 1.0
