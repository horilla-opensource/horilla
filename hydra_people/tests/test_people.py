from datetime import date

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from base.models import Company, Department, JobPosition
from employee.models import Employee
from hydra_coordination.models import ScopeGrant
from hydra_people.models import Person, PersonApplication
from hydra_people.services import link_candidate, save_person
from recruitment.models import Candidate, Recruitment, Stage


class HydraPeopleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            company="Hydra Test",
            address="Test address",
            country="PL",
            state="Dolnoslaskie",
            city="Siechnice",
            zip="55-011",
            icon="images/ui/company.png",
        )
        cls.user = User.objects.create_user(
            username="people-user",
            email="people-user@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.employee = Employee.objects.create(
            employee_user_id=cls.user,
            employee_first_name="Hydra",
            employee_last_name="Operator",
            email="people-user@example.test",
            phone="+48111111111",
        )
        work_info = cls.employee.employee_work_info
        work_info.company_id = cls.company
        work_info.save()
        cls.department = Department(department="Recruitment")
        cls.department.save()
        cls.department.company_id.add(cls.company)
        cls.job = JobPosition.objects.create(
            job_position="Greenhouse worker",
            department_id=cls.department,
        )
        cls.job.company_id.add(cls.company)
        cls.job_two = JobPosition.objects.create(
            job_position="Packing worker",
            department_id=cls.department,
        )
        cls.job_two.company_id.add(cls.company)
        cls.recruitment = Recruitment.default.create(
            title="Greenhouse intake",
            description="Test",
            company_id=cls.company,
            vacancy=2,
            is_published=False,
            optional_resume=True,
        )
        cls.recruitment.open_positions.add(cls.job)
        cls.stage = Stage._base_manager.get(
            recruitment_id=cls.recruitment,
            stage_type="initial",
        )
        cls.recruitment_two = Recruitment.default.create(
            title="Packing intake",
            description="Test",
            company_id=cls.company,
            vacancy=2,
            is_published=False,
            optional_resume=True,
        )
        cls.recruitment_two.open_positions.add(cls.job_two)
        cls.stage_two = Stage._base_manager.get(
            recruitment_id=cls.recruitment_two,
            stage_type="initial",
        )
        ScopeGrant.objects.create(user=cls.user, company=cls.company)

    def setUp(self):
        self.user = User.objects.get(pk=self.user.pk)

    def grant(self, *codenames):
        permissions = Permission.objects.filter(codename__in=codenames)
        self.user.user_permissions.add(*permissions)
        for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(attribute, None)

    def login(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

    def unsaved_person(self, **overrides):
        values = {
            "passport_name": "  OLENA   KOVAL  ",
            "first_name": "Olena",
            "last_name": "Koval",
            "date_of_birth": date(1992, 4, 5),
            "gender": Person.Gender.FEMALE,
            "citizenship": "ua",
            "preferred_language": Person.PreferredLanguage.UKRAINIAN,
            "phone": "+380 11 222 33 44",
            "whatsapp_viber": "",
            "email": "OLENA@example.test",
        }
        values.update(overrides)
        return Person(**values)

    def create_person(self, **overrides):
        self.grant("add_person")
        return save_person(person=self.unsaved_person(**overrides), actor=self.user)

    def create_candidate(self, suffix="one"):
        second_recruitment = suffix == "two"
        candidate = Candidate(
            name=f"Candidate {suffix}",
            email=f"candidate-{suffix}@example.test",
            resume="",
            recruitment_id=(
                self.recruitment_two if second_recruitment else self.recruitment
            ),
            job_position_id=self.job_two if second_recruitment else self.job,
            stage_id=self.stage_two if second_recruitment else self.stage,
        )
        Candidate._base_manager.bulk_create([candidate])
        return Candidate._base_manager.get(pk=candidate.pk)


class PersonModelAndServiceTests(HydraPeopleTestCase):
    def test_person_has_stable_identifiers_and_optional_email(self):
        person = self.create_person(email="")

        self.assertTrue(person.hydra_id.startswith("HYD-"))
        self.assertEqual(len(person.hydra_id), 20)
        self.assertIsNotNone(person.uuid)
        self.assertEqual(person.email, "")

    def test_service_normalizes_owned_identity_fields(self):
        person = self.create_person()

        self.assertEqual(person.passport_name, "OLENA KOVAL")
        self.assertEqual(person.citizenship, "UA")
        self.assertEqual(person.email, "olena@example.test")
        self.assertEqual(person.created_by, self.user)
        self.assertEqual(person.modified_by, self.user)

    def test_save_service_denies_actor_without_permission(self):
        with self.assertRaises(PermissionDenied):
            save_person(person=self.unsaved_person(), actor=self.user)

    def test_one_person_can_link_multiple_applications(self):
        person = self.create_person()
        first = self.create_candidate("one")
        second = self.create_candidate("two")
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")

        first_link = link_candidate(person=person, candidate=first, actor=self.user)
        second_link = link_candidate(person=person, candidate=second, actor=self.user)

        self.assertEqual(first_link.person, person)
        self.assertEqual(second_link.person, person)
        self.assertEqual(person.applications.count(), 2)
        person.refresh_from_db()
        self.assertEqual(person.lifecycle_state, Person.LifecycleState.CANDIDATE)

    def test_linking_same_application_is_idempotent(self):
        person = self.create_person()
        candidate = self.create_candidate()
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")

        first = link_candidate(person=person, candidate=candidate, actor=self.user)
        second = link_candidate(person=person, candidate=candidate, actor=self.user)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PersonApplication.objects.count(), 1)

    def test_application_cannot_be_relinked_to_another_person(self):
        first_person = self.create_person()
        second_person = self.create_person(
            passport_name="IVAN KOVAL",
            first_name="Ivan",
            email="ivan@example.test",
        )
        candidate = self.create_candidate()
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")
        link_candidate(person=first_person, candidate=candidate, actor=self.user)

        with self.assertRaises(ValidationError):
            link_candidate(person=second_person, candidate=candidate, actor=self.user)

    def test_employee_link_is_optional_and_unique(self):
        first_person = self.create_person(employee=self.employee)
        second_person = self.unsaved_person(
            passport_name="IVAN KOVAL",
            first_name="Ivan",
            email="ivan@example.test",
            employee=self.employee,
        )
        self.assertEqual(first_person.employee, self.employee)

        with self.assertRaises(ValidationError):
            second_person.full_clean()


class PersonPermissionViewTests(HydraPeopleTestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("hydra-person-list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_user_without_view_permission_gets_403_for_list_and_direct_url(self):
        person = self.create_person()
        self.login()

        list_response = self.client.get(reverse("hydra-person-list"))
        detail_response = self.client.get(person.get_absolute_url())

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(detail_response.status_code, 403)

    def test_view_permission_allows_list_and_detail(self):
        person = self.create_person()
        self.grant("view_person")
        self.login()

        list_response = self.client.get(reverse("hydra-person-list"))
        detail_response = self.client.get(person.get_absolute_url())

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, person.hydra_id)
        self.assertContains(list_response, "Operations workspace")
        self.assertContains(list_response, "Training / Hydra")
        self.assertContains(list_response, 'aria-current="page"')
        self.assertContains(
            list_response,
            'href="/hydra/people/"',
        )
        self.assertNotContains(
            list_response,
            'href="/hydra/coordination/organization/"',
        )
        self.assertContains(
            list_response,
            "hydra_shell/css/shell.css",
        )
        self.assertContains(
            list_response,
            "hydra_shell/js/shell.js",
        )
        self.assertContains(list_response, 'aria-label="Toggle sidebar"')
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, person.passport_name)

    def test_add_permission_allows_person_creation(self):
        self.grant("add_person")
        self.login()
        payload = {
            "passport_name": "MARIA NOWAK",
            "first_name": "Maria",
            "last_name": "Nowak",
            "date_of_birth": "1995-06-07",
            "gender": Person.Gender.FEMALE,
            "citizenship": "PL",
            "preferred_language": Person.PreferredLanguage.POLISH,
            "phone": "+48123456789",
            "whatsapp_viber": "",
            "email": "",
            "lifecycle_state": Person.LifecycleState.PROSPECT,
            "is_active": "on",
        }

        response = self.client.post(reverse("hydra-person-create"), payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Person.objects.filter(passport_name="MARIA NOWAK").exists())

    def test_candidate_link_requires_candidate_permission(self):
        person = self.create_person()
        self.grant("change_person", "link_candidate")
        self.login()

        response = self.client.get(
            reverse("hydra-person-candidate-link", args=(person.uuid,))
        )

        self.assertEqual(response.status_code, 403)

    def test_authorized_candidate_link_works(self):
        person = self.create_person()
        candidate = self.create_candidate()
        self.grant("view_person", "change_person", "link_candidate", "view_candidate")
        self.login()

        response = self.client.post(
            reverse("hydra-person-candidate-link", args=(person.uuid,)),
            {"candidate": candidate.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PersonApplication.objects.filter(person=person, candidate=candidate).exists()
        )

    def test_authorized_create_edit_and_link_forms_render(self):
        person = self.create_person()
        self.grant(
            "view_person",
            "add_person",
            "change_person",
            "link_candidate",
            "view_candidate",
        )
        self.login()

        responses = (
            self.client.get(reverse("hydra-person-create")),
            self.client.get(reverse("hydra-person-update", args=(person.uuid,))),
            self.client.get(
                reverse("hydra-person-candidate-link", args=(person.uuid,))
            ),
        )

        self.assertTrue(all(response.status_code == 200 for response in responses))
