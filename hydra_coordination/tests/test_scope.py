from datetime import date, timedelta

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from base.models import Company, Department
from employee.models import Employee
from hydra_coordination.models import (
    Location,
    PersonAssignment,
    ScopeGrant,
    Section,
    Team,
)
from hydra_coordination.services import (
    assign_person,
    save_location,
    save_scope_grant,
    save_team,
)
from hydra_people.models import Person
from hydra_people.selectors import people_for_user
from hydra_people.services import save_person


class OrganizationScopeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="scope-admin",
            email="scope-admin@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.user = User.objects.create_user(
            username="team-a-user",
            email="team-a@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.employee = Employee.objects.create(
            employee_user_id=cls.user,
            employee_first_name="Team",
            employee_last_name="Coordinator",
            email="team-a@example.test",
            phone="+48111111111",
        )
        cls.company_a = cls.make_company("Hydra A", "A Street")
        cls.company_b = cls.make_company("Hydra B", "B Street")
        work_info = cls.employee.employee_work_info
        work_info.company_id = cls.company_a
        work_info.save()

        cls.department_a = Department(department="Production A")
        cls.department_a.save()
        cls.department_a.company_id.add(cls.company_a)
        cls.department_b = Department(department="Production B")
        cls.department_b.save()
        cls.department_b.company_id.add(cls.company_b)

        cls.location_a = Location.objects.create(
            company=cls.company_a, name="Siechnice A", code="S-A"
        )
        cls.location_b = Location.objects.create(
            company=cls.company_b, name="Siechnice B", code="S-B"
        )
        cls.section_a = Section.objects.create(
            location=cls.location_a,
            department=cls.department_a,
            name="Stage A",
            code="ST-A",
        )
        cls.section_b = Section.objects.create(
            location=cls.location_b,
            department=cls.department_b,
            name="Stage B",
            code="ST-B",
        )
        cls.team_a = Team.objects.create(
            section=cls.section_a, name="Team Alpha", code="A"
        )
        cls.team_b = Team.objects.create(
            section=cls.section_b, name="Team Beta", code="B"
        )

        cls.person_a = cls.make_person("ANNA ALPHA", "Anna", "Alpha")
        cls.person_b = cls.make_person("BOHDAN BETA", "Bohdan", "Beta")
        assign_person(
            assignment=PersonAssignment(
                person=cls.person_a,
                team=cls.team_a,
                department=cls.department_a,
                valid_from=timezone.localdate(),
            ),
            actor=cls.admin,
        )
        assign_person(
            assignment=PersonAssignment(
                person=cls.person_b,
                team=cls.team_b,
                department=cls.department_b,
                valid_from=timezone.localdate(),
            ),
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
    def make_person(cls, passport_name, first_name, last_name):
        return save_person(
            person=Person(
                passport_name=passport_name,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date(1990, 1, 2),
                citizenship="UA",
                preferred_language=Person.PreferredLanguage.UKRAINIAN,
            ),
            actor=cls.admin,
        )

    def setUp(self):
        self.user = User.objects.get(pk=self.user.pk)

    def grant_permissions(self, *permissions):
        for app_label, codename in permissions:
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
            self.user.user_permissions.add(permission)
        self.clear_permission_cache()

    def clear_permission_cache(self):
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(attribute, None)

    def grant_scope(self, *, valid_from=None, valid_until=None, **target):
        return save_scope_grant(
            grant=ScopeGrant(
                user=self.user,
                valid_from=valid_from or timezone.localdate(),
                valid_until=valid_until,
                **target,
            ),
            actor=self.admin,
        )

    def login_with_all_companies_selected(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()


class PersonScopeTests(OrganizationScopeTestCase):
    def test_permission_without_scope_returns_no_people(self):
        self.grant_permissions(("hydra_people", "view_person"))

        self.assertFalse(people_for_user(user=self.user).exists())

    def test_team_scope_returns_only_people_in_that_team(self):
        self.grant_permissions(("hydra_people", "view_person"))
        self.grant_scope(team=self.team_a)

        self.assertQuerySetEqual(
            people_for_user(user=self.user),
            [self.person_a],
            transform=lambda person: person,
        )

    def test_expired_scope_returns_no_people(self):
        self.grant_permissions(("hydra_people", "view_person"))
        yesterday = timezone.localdate() - timedelta(days=1)
        self.grant_scope(
            team=self.team_a,
            valid_from=yesterday - timedelta(days=5),
            valid_until=yesterday,
        )

        self.assertFalse(people_for_user(user=self.user).exists())

    def test_all_company_session_value_does_not_widen_list_or_direct_url(self):
        self.grant_permissions(("hydra_people", "view_person"))
        self.grant_scope(team=self.team_a)
        self.login_with_all_companies_selected()

        response = self.client.get(reverse("hydra-person-list"))
        denied_detail = self.client.get(self.person_b.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.person_a.hydra_id)
        self.assertNotContains(response, self.person_b.hydra_id)
        self.assertEqual(denied_detail.status_code, 404)

    def test_person_update_service_denies_other_team(self):
        self.grant_permissions(
            ("hydra_people", "view_person"),
            ("hydra_people", "change_person"),
        )
        self.grant_scope(team=self.team_a)
        self.person_b.first_name = "Changed"

        with self.assertRaises(PermissionDenied):
            save_person(person=self.person_b, actor=self.user)


class OrganizationServiceTests(OrganizationScopeTestCase):
    def test_company_scope_allows_location_creation(self):
        self.grant_permissions(("hydra_coordination", "add_location"))
        self.grant_scope(company=self.company_a)

        location = save_location(
            location=Location(
                company=self.company_a,
                name="  New   Hall  ",
                code=" new-hall ",
            ),
            actor=self.user,
        )

        self.assertEqual(location.name, "New Hall")
        self.assertEqual(location.code, "NEW-HALL")

    def test_team_scope_cannot_create_sibling_team(self):
        self.grant_permissions(("hydra_coordination", "add_team"))
        self.grant_scope(team=self.team_a)

        with self.assertRaises(PermissionDenied):
            save_team(
                team=Team(section=self.section_a, name="Sibling", code="SIB"),
                actor=self.user,
            )

    def test_scope_grant_requires_exactly_one_target(self):
        no_target = ScopeGrant(user=self.user)
        two_targets = ScopeGrant(
            user=self.user,
            company=self.company_a,
            team=self.team_a,
        )

        with self.assertRaises(ValidationError):
            no_target.full_clean()
        with self.assertRaises(ValidationError):
            two_targets.full_clean()

    def test_non_superuser_cannot_grant_scope_outside_own_scope(self):
        self.grant_permissions(("hydra_coordination", "add_scopegrant"))
        self.grant_scope(team=self.team_a)

        with self.assertRaises(PermissionDenied):
            save_scope_grant(
                grant=ScopeGrant(user=self.user, team=self.team_b),
                actor=self.user,
            )

    def test_primary_assignments_cannot_overlap(self):
        with self.assertRaises(ValidationError):
            assign_person(
                assignment=PersonAssignment(
                    person=self.person_a,
                    team=self.team_a,
                    department=self.department_a,
                    valid_from=timezone.localdate() + timedelta(days=1),
                ),
                actor=self.admin,
            )

    def test_actor_cannot_assign_person_to_team_outside_scope(self):
        self.grant_permissions(
            ("hydra_people", "view_person"),
            ("hydra_coordination", "add_personassignment"),
            ("hydra_coordination", "assign_person"),
        )
        self.grant_scope(team=self.team_a)

        with self.assertRaises(PermissionDenied):
            assign_person(
                assignment=PersonAssignment(
                    person=self.person_a,
                    team=self.team_b,
                    department=self.department_b,
                    valid_from=timezone.localdate() + timedelta(days=1),
                ),
                actor=self.user,
            )


class OrganizationViewTests(OrganizationScopeTestCase):
    def test_organization_page_contains_only_scoped_hierarchy(self):
        self.grant_permissions(
            ("hydra_coordination", "view_location"),
            ("hydra_coordination", "view_section"),
            ("hydra_coordination", "view_team"),
        )
        self.grant_scope(team=self.team_a)
        self.login_with_all_companies_selected()

        response = self.client.get(reverse("hydra-organization"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.location_a.name)
        self.assertContains(response, self.team_a.name)
        self.assertNotContains(response, self.location_b.name)
        self.assertNotContains(response, self.team_b.name)
        self.assertContains(response, "Operations workspace")
        self.assertContains(response, "Training / Hydra")
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(
            response,
            'href="/hydra/coordination/organization/"',
        )
        self.assertNotContains(response, 'href="/hydra/people/"')

    def test_authorized_organization_forms_render(self):
        self.grant_permissions(
            ("hydra_people", "view_person"),
            ("hydra_coordination", "view_location"),
            ("hydra_coordination", "add_location"),
            ("hydra_coordination", "add_section"),
            ("hydra_coordination", "add_team"),
            ("hydra_coordination", "add_scopegrant"),
            ("hydra_coordination", "add_personassignment"),
            ("hydra_coordination", "assign_person"),
        )
        self.grant_scope(company=self.company_a)
        self.login_with_all_companies_selected()

        responses = (
            self.client.get(reverse("hydra-location-create")),
            self.client.get(reverse("hydra-section-create")),
            self.client.get(reverse("hydra-team-create")),
            self.client.get(reverse("hydra-scope-grant-create")),
            self.client.get(reverse("hydra-person-assign", args=(self.person_a.uuid,))),
        )

        self.assertTrue(all(response.status_code == 200 for response in responses))
