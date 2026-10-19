"""Top absentees count only the days each employee was expected to work."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from attendance.models import Attendance
from base.models import EmployeeShift, EmployeeShiftDay, EmployeeShiftSchedule, Holidays
from horilla.testkit.factories import (
    make_company,
    make_employee,
    make_leave_request,
    make_leave_type,
    make_user,
)

MON, TUE, WED, THU, FRI = (date(2026, 10, d) for d in range(5, 10))


class TestTopAbsentees(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Absentee Test Ltd")
        shift = EmployeeShift.objects.create(employee_shift="Day")
        shift.company_id.add(company)
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            EmployeeShiftSchedule.objects.create(
                shift_id=shift,
                day=EmployeeShiftDay.objects.get(day=day),
                start_time=time(8, 0),
                end_time=time(16, 0),
                minimum_working_hour="08:00",
            )
        cls.worker = make_employee(
            company=company,
            email="worker@absent.test",
            first_name="Worker",
            shift=shift,
        )
        cls.starter = make_employee(
            company=company,
            email="starter@absent.test",
            first_name="Starter",
            shift=shift,
        )
        cls.starter.employee_work_info.date_joining = THU
        cls.starter.employee_work_info.save()
        boss = make_user("boss", is_superuser=True)
        make_employee(company=company, email="boss@absent.test", user=boss)
        cls.boss = boss

    def absentees(self):
        self.client.force_login(self.boss)
        response = self.client.get(
            reverse("attendance-dashboard-absentees"),
            {"from_date": MON.isoformat(), "to_date": FRI.isoformat()},
        )
        return {row["name"]: row for row in response.json()["absentees"]}

    def test_leave_holidays_and_joining_date_are_not_absences(self):
        Attendance.objects.create(
            employee_id=self.worker,
            attendance_date=MON,
            attendance_clock_in_date=MON,
            attendance_clock_in=time(8, 0),
            attendance_worked_hour="08:00",
            minimum_hour="08:00",
        )
        holiday = make_leave_type("Annual")
        make_leave_request(
            employee=self.worker, leave_type=holiday, start_date=TUE, end_date=TUE
        )
        Holidays.objects.create(name="Bank holiday", start_date=WED, end_date=WED)

        rows = self.absentees()
        worker = rows[self.worker.get_full_name()]
        # Mon present, Tue on leave, Wed holiday: absent Thu and Fri only.
        self.assertEqual((worker["absent_days"], worker["total_days"]), (2, 3))
        # Joined on Thursday: expected Thu and Fri only.
        starter = rows[self.starter.get_full_name()]
        self.assertEqual((starter["absent_days"], starter["total_days"]), (2, 2))
