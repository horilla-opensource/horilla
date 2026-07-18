from datetime import date, time, timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from attendance.models import Attendance, AttendanceLateComeEarlyOut
from base.models import (
    Company,
    Department,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeShiftSchedule,
)
from employee.models import Employee
from hydra_coordination.brigadier_selectors import (
    brigadier_roster_for_team,
    brigadier_teams_for_user,
)
from hydra_coordination.models import Location, PersonAssignment, ScopeGrant, Section, Team
from hydra_coordination.services import assign_person, save_scope_grant
from hydra_people.models import Person
from leave.models import LeaveRequest, LeaveType


class BrigadierPanelTestCase(TestCase):
    required_permissions = (
        ("hydra_coordination", "view_brigadier_panel"),
        ("hydra_people", "view_person"),
        ("employee", "view_employee"),
        ("attendance", "view_attendance"),
        ("leave", "view_leaverequest"),
    )

    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.shift_day = EmployeeShiftDay.objects.create(
            day=cls.today.strftime("%A").lower()
        )
        cls.admin = User.objects.create_superuser(
            username="brigadier-admin",
            email="brigadier-admin@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.brigadier = cls.make_user_with_employee("brigadier-a")
        cls.company_only = cls.make_user_with_employee("company-only-manager")
        cls.limited = cls.make_user_with_employee("limited-brigadier")

        cls.company_a = cls.make_company("Brigadier Company A")
        cls.company_b = cls.make_company("Brigadier Company B")
        EmployeeShift._base_manager.bulk_create(
            [EmployeeShift(employee_shift="Hydra day shift")]
        )
        cls.shift = EmployeeShift._base_manager.get(
            employee_shift="Hydra day shift"
        )
        cls.shift.company_id.add(cls.company_a, cls.company_b)
        EmployeeShiftSchedule.objects.create(
            day=cls.shift_day,
            shift_id=cls.shift,
            start_time=time(6, 0),
            end_time=time(14, 0),
            minimum_working_hour="08:00",
        )
        LeaveType._base_manager.bulk_create(
            [
                LeaveType(
                    name="Annual leave",
                    color="#336699",
                    company_id=cls.company_a,
                )
            ]
        )
        cls.leave_type = LeaveType._base_manager.get(name="Annual leave")
        cls.department_a = cls.make_department("Production A", cls.company_a)
        cls.department_b = cls.make_department("Production B", cls.company_b)
        cls.location_a = Location.objects.create(
            company=cls.company_a, name="Location A", code="BR-A"
        )
        cls.location_b = Location.objects.create(
            company=cls.company_b, name="Location B", code="BR-B"
        )
        cls.section_a = Section.objects.create(
            location=cls.location_a,
            department=cls.department_a,
            name="Section A",
            code="SEC-A",
        )
        cls.section_b = Section.objects.create(
            location=cls.location_b,
            department=cls.department_b,
            name="Section B",
            code="SEC-B",
        )
        cls.team_a = Team.objects.create(
            section=cls.section_a, name="Brigadier Team Alpha", code="TEAM-A"
        )
        cls.team_b = Team.objects.create(
            section=cls.section_b, name="Brigadier Team Beta", code="TEAM-B"
        )

        for employee in (
            cls.brigadier.employee_get,
            cls.company_only.employee_get,
            cls.limited.employee_get,
        ):
            work_info = employee.employee_work_info
            work_info.company_id = cls.company_a
            work_info.save()

        cls.no_record_person = cls.make_employee_person(
            "NO RECORD WORKER", "No", "Record", cls.company_a, cls.team_a, cls.department_a
        )
        cls.at_work_person = cls.make_employee_person(
            "LATE WORKER", "Late", "Worker", cls.company_a, cls.team_a, cls.department_a
        )
        cls.completed_person = cls.make_employee_person(
            "EARLY WORKER", "Early", "Worker", cls.company_a, cls.team_a, cls.department_a
        )
        cls.outside_person = cls.make_employee_person(
            "OUTSIDE WORKER", "Outside", "Worker", cls.company_b, cls.team_b, cls.department_b
        )

        at_work = Attendance.objects.create(
            employee_id=cls.at_work_person.employee,
            attendance_date=cls.today,
            attendance_clock_in_date=cls.today,
            attendance_clock_in=time(6, 15),
            attendance_worked_hour="02:00",
            minimum_hour="08:00",
        )
        late_report = AttendanceLateComeEarlyOut(
            attendance_id=at_work,
            type="late_come",
        )
        late_report.save()
        completed = Attendance.objects.create(
            employee_id=cls.completed_person.employee,
            attendance_date=cls.today,
            attendance_clock_in_date=cls.today,
            attendance_clock_in=time(6, 0),
            attendance_clock_out_date=cls.today,
            attendance_clock_out=time(13, 30),
            attendance_worked_hour="07:30",
            minimum_hour="08:00",
            attendance_validated=False,
        )
        early_report = AttendanceLateComeEarlyOut(
            attendance_id=completed,
            type="early_out",
        )
        early_report.save()
        Attendance.objects.create(
            employee_id=cls.outside_person.employee,
            attendance_date=cls.today,
            attendance_clock_in_date=cls.today,
            attendance_clock_in=time(6, 0),
            attendance_clock_out_date=cls.today,
            attendance_clock_out=time(14, 0),
            attendance_worked_hour="08:00",
            minimum_hour="08:00",
            attendance_validated=True,
        )

        cls.grant_permissions(cls.brigadier, *cls.required_permissions)
        cls.grant_permissions(cls.company_only, *cls.required_permissions)
        cls.grant_permissions(cls.limited, *cls.required_permissions[1:])
        save_scope_grant(
            grant=ScopeGrant(user=cls.brigadier, team=cls.team_a),
            actor=cls.admin,
        )
        save_scope_grant(
            grant=ScopeGrant(user=cls.company_only, company=cls.company_a),
            actor=cls.admin,
        )
        save_scope_grant(
            grant=ScopeGrant(user=cls.limited, team=cls.team_a),
            actor=cls.admin,
        )

    @classmethod
    def make_user_with_employee(cls, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password="test-password",
            is_new_employee=False,
        )
        Employee.objects.create(
            employee_user_id=user,
            employee_first_name=username,
            employee_last_name="Operator",
            email=f"{username}@example.test",
            phone="+48123456789",
        )
        return user

    @classmethod
    def make_company(cls, name):
        return Company.objects.create(
            company=name,
            address="Test Street",
            country="PL",
            state="Dolnoslaskie",
            city="Siechnice",
            zip="55-011",
            icon="images/ui/company.png",
        )

    @classmethod
    def make_department(cls, name, company):
        department = Department(department=name)
        department.save()
        department.company_id.add(company)
        return department

    @classmethod
    def make_employee_person(cls, passport_name, first_name, last_name, company, team, department):
        slug = passport_name.lower().replace(" ", "-")
        user = User.objects.create_user(
            username=slug,
            email=f"{slug}@example.test",
            password="test-password",
            is_active=False,
            is_new_employee=False,
        )
        employee = Employee.objects.create(
            employee_user_id=user,
            employee_first_name=first_name,
            employee_last_name=last_name,
            email=f"{slug}@example.test",
            phone="+48987654321",
        )
        work_info = employee.employee_work_info
        work_info.company_id = company
        work_info.department_id = department
        work_info.shift_id = cls.shift
        work_info.date_joining = cls.today - timedelta(days=30)
        work_info.save()
        person = Person.objects.create(
            passport_name=passport_name,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date(1990, 1, 2),
            citizenship="UA",
            preferred_language=Person.PreferredLanguage.UKRAINIAN,
            lifecycle_state=Person.LifecycleState.EMPLOYEE,
            employee=employee,
            created_by=cls.admin,
            modified_by=cls.admin,
        )
        assign_person(
            assignment=PersonAssignment(
                person=person,
                team=team,
                department=department,
                valid_from=cls.today - timedelta(days=10),
            ),
            actor=cls.admin,
        )
        return person

    @classmethod
    def grant_permissions(cls, user, *permissions):
        user.user_permissions.add(
            *[
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
                for app_label, codename in permissions
            ]
        )

    def setUp(self):
        self.brigadier = User.objects.get(pk=self.brigadier.pk)
        self.company_only = User.objects.get(pk=self.company_only.pk)
        self.limited = User.objects.get(pk=self.limited.pk)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

    def make_approved_leave(
        self,
        *,
        person,
        day=None,
        start_breakdown="full_day",
        end_breakdown="full_day",
    ):
        day = day or self.today
        request = LeaveRequest(
            employee_id=person.employee,
            leave_type_id=self.leave_type,
            start_date=day,
            end_date=day,
            start_date_breakdown=start_breakdown,
            end_date_breakdown=end_breakdown,
            requested_days=1,
            description="Approved test leave",
            status="approved",
        )
        LeaveRequest._base_manager.bulk_create([request])
        return request


class BrigadierSelectorTests(BrigadierPanelTestCase):
    def test_only_current_direct_team_grants_open_panel(self):
        self.assertQuerySetEqual(
            brigadier_teams_for_user(user=self.brigadier),
            [self.team_a],
            transform=lambda team: team,
        )
        self.assertFalse(brigadier_teams_for_user(user=self.company_only).exists())

    def test_roster_composes_team_assignment_and_attendance(self):
        rows = brigadier_roster_for_team(
            user=self.brigadier,
            team=self.team_a,
            day=self.today,
        )
        by_name = {row.person.passport_name: row for row in rows}

        self.assertEqual(len(rows), 3)
        self.assertNotIn(self.outside_person.passport_name, by_name)
        self.assertTrue(by_name[self.no_record_person.passport_name].no_attendance)
        self.assertTrue(by_name[self.at_work_person.passport_name].at_work)
        self.assertTrue(by_name[self.at_work_person.passport_name].late_come)
        self.assertTrue(by_name[self.completed_person.passport_name].pending_validation)
        self.assertTrue(by_name[self.completed_person.passport_name].early_out)

    def test_full_day_approved_leave_is_expected_absence(self):
        self.make_approved_leave(person=self.no_record_person)

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=self.today
        )
        row = next(row for row in rows if row.person == self.no_record_person)

        self.assertTrue(row.scheduled)
        self.assertTrue(row.approved_leave_full_day)
        self.assertFalse(row.expected_to_work)
        self.assertFalse(row.no_attendance)
        self.assertFalse(row.has_exception)

    def test_attendance_during_full_day_leave_is_a_conflict(self):
        self.make_approved_leave(person=self.at_work_person)

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=self.today
        )
        row = next(row for row in rows if row.person == self.at_work_person)

        self.assertTrue(row.attendance_on_approved_leave)
        self.assertTrue(row.has_exception)
        self.assertFalse(row.late_come)

    def test_first_half_leave_suppresses_expected_late_marker(self):
        self.make_approved_leave(
            person=self.at_work_person,
            start_breakdown="first_half",
            end_breakdown="first_half",
        )

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=self.today
        )
        row = next(row for row in rows if row.person == self.at_work_person)

        self.assertTrue(row.approved_leave_partial_day)
        self.assertTrue(row.expected_to_work)
        self.assertFalse(row.late_come)

    def test_second_half_leave_suppresses_expected_early_marker(self):
        self.make_approved_leave(
            person=self.completed_person,
            start_breakdown="second_half",
            end_breakdown="second_half",
        )

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=self.today
        )
        row = next(row for row in rows if row.person == self.completed_person)

        self.assertTrue(row.approved_leave_partial_day)
        self.assertTrue(row.expected_to_work)
        self.assertFalse(row.early_out)

    def test_partial_leave_without_attendance_remains_an_exception(self):
        self.make_approved_leave(
            person=self.no_record_person,
            start_breakdown="first_half",
            end_breakdown="first_half",
        )

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=self.today
        )
        row = next(row for row in rows if row.person == self.no_record_person)

        self.assertTrue(row.approved_leave_partial_day)
        self.assertTrue(row.no_attendance)
        self.assertTrue(row.has_exception)

    def test_unscheduled_day_without_attendance_is_not_an_absence(self):
        unscheduled_day = self.today - timedelta(days=1)

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=unscheduled_day
        )
        row = next(row for row in rows if row.person == self.no_record_person)

        self.assertFalse(row.scheduled)
        self.assertFalse(row.schedule_missing)
        self.assertFalse(row.no_attendance)
        self.assertFalse(row.has_exception)

    def test_attendance_on_unscheduled_day_is_a_conflict(self):
        unscheduled_day = self.today - timedelta(days=1)
        EmployeeShiftDay.objects.get_or_create(
            day=unscheduled_day.strftime("%A").lower()
        )
        Attendance.objects.create(
            employee_id=self.no_record_person.employee,
            attendance_date=unscheduled_day,
            attendance_clock_in_date=unscheduled_day,
            attendance_clock_in=time(6, 0),
            attendance_clock_out_date=unscheduled_day,
            attendance_clock_out=time(14, 0),
            attendance_worked_hour="08:00",
            minimum_hour="08:00",
            attendance_validated=True,
        )

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=unscheduled_day
        )
        row = next(row for row in rows if row.person == self.no_record_person)

        self.assertTrue(row.attendance_on_unscheduled_day)
        self.assertTrue(row.has_exception)

    def test_missing_shift_assignment_is_configuration_exception(self):
        work_info = self.no_record_person.employee.employee_work_info
        work_info.shift_id = None
        work_info.save()

        rows = brigadier_roster_for_team(
            user=self.brigadier, team=self.team_a, day=self.today
        )
        row = next(row for row in rows if row.person == self.no_record_person)

        self.assertTrue(row.schedule_missing)
        self.assertFalse(row.no_attendance)
        self.assertTrue(row.has_exception)


class BrigadierPanelViewTests(BrigadierPanelTestCase):
    def test_panel_shows_only_direct_team_roster_and_exceptions(self):
        self.login(self.brigadier)

        response = self.client.get(reverse("hydra-brigadier-panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team_a.name)
        self.assertNotContains(response, self.team_b.name)
        self.assertContains(response, self.no_record_person.passport_name)
        self.assertContains(response, self.at_work_person.passport_name)
        self.assertContains(response, self.completed_person.passport_name)
        self.assertNotContains(response, self.outside_person.passport_name)
        self.assertContains(response, "Missing expected attendance")
        self.assertContains(response, "Late arrival")
        self.assertContains(response, "Early departure")
        self.assertContains(response, "Pending validation")
        self.assertContains(response, 'aria-current="page"')

    def test_direct_url_team_tampering_returns_404(self):
        self.login(self.brigadier)

        response = self.client.get(
            reverse("hydra-brigadier-panel"),
            {"team": self.team_b.pk},
        )

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, self.outside_person.passport_name, status_code=404)

    def test_selected_company_all_does_not_widen_team_scope(self):
        self.login(self.brigadier)

        response = self.client.get(reverse("hydra-brigadier-panel"))

        self.assertNotContains(response, self.team_b.name)
        self.assertNotContains(response, self.outside_person.hydra_id)

    def test_company_grant_does_not_open_brigadier_team(self):
        self.login(self.company_only)

        response = self.client.get(reverse("hydra-brigadier-panel"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No direct team scope")
        self.assertNotContains(response, self.team_a.name)
        self.assertNotContains(response, self.no_record_person.passport_name)

    def test_missing_dedicated_permission_returns_403(self):
        self.login(self.limited)

        response = self.client.get(reverse("hydra-brigadier-panel"))

        self.assertEqual(response.status_code, 403)

    def test_leave_permission_is_required_for_reconciled_panel(self):
        permission = Permission.objects.get(
            content_type__app_label="leave",
            codename="view_leaverequest",
        )
        self.brigadier.user_permissions.remove(permission)
        for name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.brigadier.__dict__.pop(name, None)
        self.login(self.brigadier)

        response = self.client.get(reverse("hydra-brigadier-panel"))

        self.assertEqual(response.status_code, 403)

    def test_future_date_is_rejected(self):
        self.login(self.brigadier)

        response = self.client.get(
            reverse("hydra-brigadier-panel"),
            {"date": self.today + timedelta(days=1)},
        )

        self.assertEqual(response.status_code, 400)

    def test_search_remains_inside_team_scope(self):
        self.login(self.brigadier)

        response = self.client.get(
            reverse("hydra-brigadier-panel"),
            {"team": self.team_a.pk, "q": "NO RECORD"},
        )

        self.assertContains(response, self.no_record_person.passport_name)
        self.assertNotContains(response, self.at_work_person.passport_name)
        self.assertNotContains(response, self.outside_person.passport_name)
