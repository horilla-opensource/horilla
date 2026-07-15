from datetime import date, timedelta

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from base.models import Company, Department, JobPosition
from employee.models import Employee
from hydra_coordination.models import (
    Location,
    PersonAssignment,
    ScopeGrant,
    Section,
    Team,
)
from hydra_coordination.services import (
    assign_employee_to_team,
    assign_person,
    save_scope_grant,
)
from hydra_people.models import Person


class EmployeeTeamAssignmentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="team-assignment-admin",
            email="team-assignment-admin@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.operator = User.objects.create_user(
            username="team-assignment-operator",
            email="team-assignment-operator@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.operator_employee = Employee.objects.create(
            employee_user_id=cls.operator,
            employee_first_name="Team",
            employee_last_name="Coordinator",
            email="team-assignment-operator@example.test",
            phone="+48222222222",
        )
        employee_user = User.objects.create_user(
            username="assigned-employee",
            email="assigned-employee@example.test",
            password="test-password",
            is_active=False,
            is_new_employee=False,
        )
        cls.employee = Employee.objects.create(
            employee_user_id=employee_user,
            employee_first_name="Iryna",
            employee_last_name="Worker",
            email="assigned-employee@example.test",
            phone="+48111111111",
        )

        cls.company_a = cls.make_company("Hydra Team A", "A Street")
        cls.company_b = cls.make_company("Hydra Team B", "B Street")
        cls.department_a = cls.make_department("Production A", cls.company_a)
        cls.department_a2 = cls.make_department("Packing A", cls.company_a)
        cls.department_b = cls.make_department("Production B", cls.company_b)
        cls.job_a = JobPosition.objects.create(
            job_position="Greenhouse worker", department_id=cls.department_a
        )
        cls.job_a.company_id.add(cls.company_a)

        cls.location_a = Location.objects.create(
            company=cls.company_a, name="Siechnice", code="SIE"
        )
        cls.location_b = Location.objects.create(
            company=cls.company_b, name="Other location", code="OTH"
        )
        cls.section_a = Section.objects.create(
            location=cls.location_a,
            department=cls.department_a,
            name="Greenhouse",
            code="GH",
        )
        cls.section_a2 = Section.objects.create(
            location=cls.location_a,
            department=cls.department_a2,
            name="Packing",
            code="PACK",
        )
        cls.section_without_department = Section.objects.create(
            location=cls.location_a,
            name="Unmapped",
            code="NO-DEPT",
        )
        cls.section_b = Section.objects.create(
            location=cls.location_b,
            department=cls.department_b,
            name="Remote",
            code="REMOTE",
        )
        cls.team_a = Team.objects.create(
            section=cls.section_a, name="Team Alpha", code="ALPHA"
        )
        cls.team_a2 = Team.objects.create(
            section=cls.section_a2, name="Team Packing", code="PACK"
        )
        cls.team_without_department = Team.objects.create(
            section=cls.section_without_department, name="No department", code="NONE"
        )
        cls.team_b = Team.objects.create(
            section=cls.section_b, name="Team Outside", code="OUT"
        )

        work_info = cls.employee.employee_work_info
        work_info.company_id = cls.company_a
        work_info.department_id = cls.department_a
        work_info.job_position_id = cls.job_a
        work_info.location = "Legacy location"
        work_info.save()
        operator_work_info = cls.operator_employee.employee_work_info
        operator_work_info.company_id = cls.company_a
        operator_work_info.save()

        cls.person = Person.objects.create(
            passport_name="IRYNA WORKER",
            first_name="Iryna",
            last_name="Worker",
            date_of_birth=date(1992, 3, 4),
            citizenship="UA",
            preferred_language=Person.PreferredLanguage.UKRAINIAN,
            lifecycle_state=Person.LifecycleState.EMPLOYEE,
            employee=cls.employee,
            created_by=cls.admin,
            modified_by=cls.admin,
        )
        cls.initial_assignment = assign_person(
            assignment=PersonAssignment(
                person=cls.person,
                team=cls.team_a,
                department=cls.department_a,
                valid_from=timezone.localdate() - timedelta(days=10),
            ),
            actor=cls.admin,
        )
        save_scope_grant(
            grant=ScopeGrant(user=cls.operator, company=cls.company_a),
            actor=cls.admin,
        )

    @classmethod
    def make_company(cls, name, address):
        return Company.objects.create(
            company=name,
            address=address,
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

    def setUp(self):
        self.operator = User.objects.get(pk=self.operator.pk)

    def grant_assignment_permissions(self, *, include_work_information=True):
        permissions = [
            ("hydra_people", "view_person"),
            ("hydra_coordination", "add_personassignment"),
            ("hydra_coordination", "assign_person"),
            ("employee", "view_employee"),
        ]
        if include_work_information:
            permissions.append(("employee", "change_employeeworkinformation"))
        for app_label, codename in permissions:
            self.operator.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.operator.__dict__.pop(attribute, None)

    def assign_to_packing(self):
        return assign_employee_to_team(
            person=self.person,
            team=self.team_a2,
            valid_from=timezone.localdate(),
            actor=self.operator,
        )


class EmployeeTeamAssignmentServiceTests(EmployeeTeamAssignmentTestCase):
    def test_reassignment_closes_history_and_synchronizes_horilla_work_info(self):
        self.grant_assignment_permissions()
        history_count = self.employee.employee_work_info.history.count()

        assignment = self.assign_to_packing()

        previous = PersonAssignment.objects.get(pk=self.initial_assignment.pk)
        self.assertEqual(previous.valid_until, timezone.localdate() - timedelta(days=1))
        self.assertEqual(previous.modified_by, self.operator)
        self.assertEqual(assignment.department, self.department_a2)
        self.assertEqual(assignment.created_by, self.operator)
        work_info = Employee.objects.get(pk=self.employee.pk).employee_work_info
        self.assertEqual(work_info.company_id, self.company_a)
        self.assertEqual(work_info.department_id, self.department_a2)
        self.assertEqual(work_info.location, self.location_a.name)
        self.assertIsNone(work_info.job_position_id)
        self.assertIsNone(work_info.job_role_id)
        self.assertGreater(work_info.history.count(), history_count)

    def test_repeating_same_assignment_is_idempotent(self):
        self.grant_assignment_permissions()

        first = self.assign_to_packing()
        second = self.assign_to_packing()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            PersonAssignment.objects.filter(person=self.person).count(),
            2,
        )

    def test_work_information_change_permission_is_required(self):
        self.grant_assignment_permissions(include_work_information=False)

        with self.assertRaises(PermissionDenied):
            self.assign_to_packing()

        self.assertEqual(
            PersonAssignment.objects.filter(person=self.person).count(),
            1,
        )

    def test_out_of_scope_team_is_denied(self):
        self.grant_assignment_permissions()

        with self.assertRaises(PermissionDenied):
            assign_employee_to_team(
                person=self.person,
                team=self.team_b,
                valid_from=timezone.localdate(),
                actor=self.operator,
            )

    def test_team_without_department_is_rejected(self):
        self.grant_assignment_permissions()

        with self.assertRaises(ValidationError):
            assign_employee_to_team(
                person=self.person,
                team=self.team_without_department,
                valid_from=timezone.localdate(),
                actor=self.operator,
            )

    def test_unconverted_person_is_rejected(self):
        self.grant_assignment_permissions()
        person = Person.objects.create(
            passport_name="OLEH CANDIDATE",
            first_name="Oleh",
            last_name="Candidate",
            date_of_birth=date(1990, 1, 2),
            citizenship="UA",
            created_by=self.admin,
            modified_by=self.admin,
        )
        assign_person(
            assignment=PersonAssignment(
                person=person,
                team=self.team_a,
                department=self.department_a,
            ),
            actor=self.admin,
        )

        with self.assertRaises(ValidationError):
            assign_employee_to_team(
                person=person,
                team=self.team_a2,
                valid_from=timezone.localdate(),
                actor=self.operator,
            )

    def test_future_assignment_is_rejected_without_changing_history(self):
        self.grant_assignment_permissions()

        with self.assertRaises(ValidationError):
            assign_employee_to_team(
                person=self.person,
                team=self.team_a2,
                valid_from=timezone.localdate() + timedelta(days=1),
                actor=self.operator,
            )

        self.assertEqual(
            PersonAssignment.objects.filter(person=self.person).count(),
            1,
        )


class EmployeeTeamAssignmentViewTests(EmployeeTeamAssignmentTestCase):
    def login(self):
        self.client.force_login(self.operator)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

    def test_form_is_scoped_and_derives_department_server_side(self):
        self.grant_assignment_permissions()
        self.login()

        response = self.client.get(
            reverse("hydra-person-assign", args=(self.person.uuid,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assign employee")
        self.assertContains(response, self.team_a2.name)
        self.assertNotContains(response, self.team_b.name)
        self.assertNotContains(response, self.team_without_department.name)
        self.assertNotContains(response, 'name="department"')

        posted = self.client.post(
            reverse("hydra-person-assign", args=(self.person.uuid,)),
            {"team": self.team_a2.pk, "valid_from": timezone.localdate()},
        )

        self.assertRedirects(posted, self.person.get_absolute_url())
        assignment = PersonAssignment.objects.filter(person=self.person).first()
        self.assertEqual(assignment.department, self.department_a2)

    def test_direct_form_access_without_work_information_permission_is_denied(self):
        self.grant_assignment_permissions(include_work_information=False)
        self.login()

        response = self.client.get(
            reverse("hydra-person-assign", args=(self.person.uuid,))
        )

        self.assertEqual(response.status_code, 403)

    def test_future_date_is_reported_in_form(self):
        self.grant_assignment_permissions()
        self.login()

        response = self.client.post(
            reverse("hydra-person-assign", args=(self.person.uuid,)),
            {
                "team": self.team_a2.pk,
                "valid_from": timezone.localdate() + timedelta(days=1),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot start in the future")
        self.assertEqual(
            PersonAssignment.objects.filter(person=self.person).count(),
            1,
        )
