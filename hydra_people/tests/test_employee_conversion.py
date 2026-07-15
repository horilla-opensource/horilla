from datetime import date

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from base.models import Company, Department, JobPosition
from employee.models import Employee
from hydra_coordination.models import ScopeGrant
from hydra_people.models import EmployeeConversion, Person
from hydra_people.services import (
    CONVERSION_PERMISSIONS,
    convert_person_to_employee,
    link_candidate,
    synchronize_onboarding_employee,
)
from recruitment.models import Candidate, Recruitment, Stage


class EmployeeConversionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="conversion-admin",
            email="conversion-admin@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.user = User.objects.create_user(
            username="conversion-operator",
            email="conversion-operator@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.admin_employee = Employee.objects.create(
            employee_user_id=cls.admin,
            employee_first_name="Conversion",
            employee_last_name="Admin",
            email="conversion-admin@example.test",
            phone="+48101010101",
        )
        cls.operator_employee = Employee.objects.create(
            employee_user_id=cls.user,
            employee_first_name="Conversion",
            employee_last_name="Operator",
            email="conversion-operator@example.test",
            phone="+48202020202",
        )
        cls.company_a = cls.make_company("Conversion Company A", "A Street")
        cls.company_b = cls.make_company("Conversion Company B", "B Street")
        cls.department_a = cls.make_department("Conversion Department A", cls.company_a)
        cls.department_b = cls.make_department("Conversion Department B", cls.company_b)
        cls.job_a = cls.make_job("Conversion Job A", cls.department_a, cls.company_a)
        cls.job_b = cls.make_job("Conversion Job B", cls.department_b, cls.company_b)
        cls.recruitment_a, cls.stage_a = cls.make_recruitment(
            "Conversion recruitment A", cls.company_a, cls.job_a
        )
        cls.recruitment_b, cls.stage_b = cls.make_recruitment(
            "Conversion recruitment B", cls.company_b, cls.job_b
        )
        cls.admin_employee.employee_work_info.company_id = cls.company_a
        cls.admin_employee.employee_work_info.save()
        cls.operator_employee.employee_work_info.company_id = cls.company_a
        cls.operator_employee.employee_work_info.save()
        cls.person_a = cls.make_person(
            "OLENA CONVERSION",
            "Olena",
            "Conversion",
            "olena.person@example.test",
            cls.user,
        )
        cls.person_b = cls.make_person(
            "TARAS OUTSIDE",
            "Taras",
            "Outside",
            "taras.person@example.test",
            cls.admin,
        )
        cls.candidate_a = cls.make_candidate(
            "Olena application",
            "olena.employee@example.test",
            cls.recruitment_a,
            cls.job_a,
            cls.stage_a,
        )
        cls.candidate_b = cls.make_candidate(
            "Taras application",
            "taras.employee@example.test",
            cls.recruitment_b,
            cls.job_b,
            cls.stage_b,
        )
        link_candidate(person=cls.person_a, candidate=cls.candidate_a, actor=cls.admin)
        link_candidate(person=cls.person_b, candidate=cls.candidate_b, actor=cls.admin)
        ScopeGrant.objects.create(user=cls.user, company=cls.company_a)

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

    @classmethod
    def make_job(cls, name, department, company):
        job = JobPosition.objects.create(job_position=name, department_id=department)
        job.company_id.add(company)
        return job

    @classmethod
    def make_recruitment(cls, title, company, job):
        recruitment = Recruitment.default.create(
            title=title,
            description="Employee conversion test",
            company_id=company,
            vacancy=2,
            is_published=False,
            optional_resume=True,
        )
        recruitment.open_positions.add(job)
        stage = Stage._base_manager.get(
            recruitment_id=recruitment,
            stage_type="initial",
        )
        return recruitment, stage

    @classmethod
    def make_person(cls, passport_name, first_name, last_name, email, creator):
        person = Person(
            passport_name=passport_name,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date(1993, 5, 17),
            gender=Person.Gender.FEMALE,
            citizenship="UA",
            preferred_language=Person.PreferredLanguage.UKRAINIAN,
            phone="+48123123123",
            email=email,
            created_by=creator,
            modified_by=creator,
        )
        person.full_clean()
        person.save()
        return person

    @classmethod
    def make_candidate(cls, name, email, recruitment, job, stage):
        candidate = Candidate(
            name=name,
            email=email,
            mobile="+48123123123",
            resume="",
            recruitment_id=recruitment,
            job_position_id=job,
            stage_id=stage,
            hired=True,
            joining_date=date(2026, 8, 3),
            gender="female",
        )
        Candidate._base_manager.bulk_create([candidate])
        return Candidate._base_manager.get(pk=candidate.pk)

    def setUp(self):
        self.user = User.objects.get(pk=self.user.pk)
        self.person_a = Person.objects.get(pk=self.person_a.pk)
        self.person_b = Person.objects.get(pk=self.person_b.pk)
        self.candidate_a = Candidate._base_manager.get(pk=self.candidate_a.pk)
        self.candidate_b = Candidate._base_manager.get(pk=self.candidate_b.pk)

    def grant(self, *permissions):
        for permission_name in permissions:
            app_label, codename = permission_name.split(".", 1)
            self.user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def grant_conversion(self, *, include_history=True):
        permissions = list(CONVERSION_PERMISSIONS)
        if include_history:
            permissions.append("hydra_people.view_employeeconversion")
        self.grant(*permissions)

    def login(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

    def convert(self, **overrides):
        data = {
            "person": self.person_a,
            "candidate": self.candidate_a,
            "work_email": "olena.employee@example.test",
            "phone": "+48123123123",
            "joining_date": date(2026, 8, 3),
            "actor": self.user,
        }
        data.update(overrides)
        return convert_person_to_employee(**data)

    def make_existing_employee(self, prefix):
        email = f"{prefix}@example.test"
        employee_user = User.objects.create_user(
            username=email,
            email=email,
            password="test-password",
            is_new_employee=False,
        )
        employee = Employee.objects.create(
            employee_user_id=employee_user,
            employee_first_name=f"{prefix} retained",
            employee_last_name="Employee",
            email=email,
            phone="+48999999999",
        )
        work_info = employee.employee_work_info
        work_info.company_id = self.company_a
        work_info.department_id = self.department_a
        work_info.job_position_id = self.job_a
        work_info.date_joining = date(2026, 8, 3)
        work_info.email = email
        work_info.save()
        return employee


class EmployeeConversionServiceTests(EmployeeConversionTestCase):
    def test_conversion_creates_employee_links_and_immutable_source_snapshot(self):
        self.grant_conversion()

        employee, conversion, created = self.convert()

        self.assertTrue(created)
        self.assertEqual(employee.employee_first_name, self.person_a.first_name)
        self.assertEqual(employee.employee_last_name, self.person_a.last_name)
        self.assertEqual(employee.dob, self.person_a.date_of_birth)
        self.assertEqual(employee.employee_work_info.company_id, self.company_a)
        self.assertEqual(employee.employee_work_info.department_id, self.department_a)
        self.assertEqual(employee.employee_work_info.job_position_id, self.job_a)
        self.assertEqual(employee.employee_work_info.date_joining, date(2026, 8, 3))
        self.assertFalse(employee.employee_user_id.is_active)
        self.assertFalse(employee.employee_user_id.has_usable_password())
        self.person_a.refresh_from_db()
        self.candidate_a.refresh_from_db()
        self.assertEqual(self.person_a.employee, employee)
        self.assertEqual(self.person_a.lifecycle_state, Person.LifecycleState.EMPLOYEE)
        self.assertEqual(self.candidate_a.converted_employee_id, employee)
        self.assertTrue(self.candidate_a.converted)
        self.assertEqual(conversion.person, self.person_a)
        self.assertEqual(
            conversion.source_snapshot["pre_conversion"]["person_lifecycle_state"],
            Person.LifecycleState.CANDIDATE,
        )
        self.assertEqual(
            conversion.field_decisions["employee_first_name"],
            "person.first_name",
        )

    def test_conversion_is_idempotent_for_the_same_decision(self):
        self.grant_conversion()
        first_employee, first_record, first_created = self.convert()
        employee_count = Employee._base_manager.count()
        user_count = User.objects.count()

        second_employee, second_record, second_created = self.convert()

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(second_employee, first_employee)
        self.assertEqual(second_record, first_record)
        self.assertEqual(Employee._base_manager.count(), employee_count)
        self.assertEqual(User.objects.count(), user_count)
        self.assertEqual(EmployeeConversion.objects.count(), 1)

    def test_unhired_application_is_rejected_without_partial_write(self):
        self.grant_conversion()
        self.candidate_a.hired = False
        self.candidate_a.save(update_fields=("hired",))
        employee_count = Employee._base_manager.count()
        user_count = User.objects.count()

        with self.assertRaises(ValidationError):
            self.convert()

        self.assertEqual(Employee._base_manager.count(), employee_count)
        self.assertEqual(User.objects.count(), user_count)
        self.person_a.refresh_from_db()
        self.assertIsNone(self.person_a.employee_id)
        self.assertFalse(EmployeeConversion.objects.exists())

    def test_existing_user_email_is_rejected_without_automatic_link(self):
        self.grant_conversion()
        User.objects.create_user(
            username="occupied-account",
            email="occupied@example.test",
            password="test-password",
        )

        with self.assertRaises(ValidationError):
            self.convert(work_email=" OCCUPIED@example.test ")

        self.person_a.refresh_from_db()
        self.assertIsNone(self.person_a.employee_id)
        self.assertFalse(EmployeeConversion.objects.exists())

    def test_explicit_candidate_employee_is_linked_without_overwriting(self):
        self.grant_conversion()
        employee = self.make_existing_employee("retained")
        self.candidate_a.converted_employee_id = employee
        self.candidate_a.converted = True
        self.candidate_a.save(
            update_fields=("converted_employee_id", "converted")
        )

        linked, conversion, created = self.convert(
            work_email=employee.email,
            phone=employee.phone,
        )

        self.assertFalse(created)
        self.assertEqual(linked, employee)
        employee.refresh_from_db()
        self.assertEqual(employee.employee_first_name, "retained retained")
        self.person_a.refresh_from_db()
        self.assertEqual(self.person_a.employee, employee)
        self.assertEqual(
            conversion.field_decisions["employee"],
            "retained_existing_candidate_employee",
        )

    def test_conflicting_person_and_candidate_employee_is_rejected(self):
        self.grant_conversion()
        person_employee = self.make_existing_employee("person-target")
        candidate_employee = self.make_existing_employee("candidate-target")
        self.person_a.employee = person_employee
        self.person_a.save(update_fields=("employee",))
        self.candidate_a.converted_employee_id = candidate_employee
        self.candidate_a.converted = True
        self.candidate_a.save(
            update_fields=("converted_employee_id", "converted")
        )

        with self.assertRaises(ValidationError):
            self.convert(
                work_email=person_employee.email,
                phone=person_employee.phone,
            )

        self.assertFalse(EmployeeConversion.objects.exists())

    def test_conversion_record_is_append_only(self):
        self.grant_conversion()
        _, conversion, _ = self.convert()

        with self.assertRaises(TypeError):
            EmployeeConversion.objects.filter(pk=conversion.pk).update(
                source=EmployeeConversion.Source.HORILLA_ONBOARDING
            )
        with self.assertRaises(TypeError):
            conversion.save()
        with self.assertRaises(TypeError):
            conversion.delete()

    def test_onboarding_sync_records_link_and_is_idempotent(self):
        employee = self.make_existing_employee("onboarding")

        first = synchronize_onboarding_employee(
            candidate=self.candidate_a,
            employee=employee,
            actor=self.admin,
        )
        second = synchronize_onboarding_employee(
            candidate=self.candidate_a,
            employee=employee,
            actor=self.admin,
        )

        self.assertEqual(first, second)
        self.assertEqual(first.source, EmployeeConversion.Source.HORILLA_ONBOARDING)
        self.person_a.refresh_from_db()
        self.assertEqual(self.person_a.employee, employee)
        self.assertEqual(EmployeeConversion.objects.count(), 1)


class EmployeeConversionPermissionViewTests(EmployeeConversionTestCase):
    def test_missing_conversion_permission_returns_403(self):
        self.grant(
            *(
                permission
                for permission in CONVERSION_PERMISSIONS
                if permission != "hydra_people.convert_person_to_employee"
            )
        )
        self.login()

        response = self.client.get(
            reverse("hydra-person-employee-conversion", args=(self.person_a.uuid,))
        )

        self.assertEqual(response.status_code, 403)

    def test_direct_url_outside_person_scope_returns_404(self):
        self.grant_conversion()
        self.login()

        response = self.client.get(
            reverse("hydra-person-employee-conversion", args=(self.person_b.uuid,))
        )

        self.assertEqual(response.status_code, 404)

    def test_form_contains_only_hired_application_for_scoped_person(self):
        self.grant_conversion()
        self.login()

        response = self.client.get(
            reverse("hydra-person-employee-conversion", args=(self.person_a.uuid,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.candidate_a.name)
        self.assertNotContains(response, self.candidate_b.name)
        self.assertContains(response, "inactive with an unusable password")
        self.assertContains(response, 'href="/hydra/people/" aria-current="page"')

    def test_authorized_form_creates_and_redirects_to_person(self):
        self.grant_conversion()
        self.login()

        response = self.client.post(
            reverse("hydra-person-employee-conversion", args=(self.person_a.uuid,)),
            {
                "candidate": self.candidate_a.pk,
                "work_email": "VIEW.CONVERT@example.test",
                "phone": "+48123123123",
                "joining_date": "2026-08-03",
                "confirmation": "on",
            },
        )

        self.assertRedirects(response, self.person_a.get_absolute_url())
        self.person_a.refresh_from_db()
        self.assertEqual(self.person_a.employee.email, "view.convert@example.test")
        self.assertTrue(EmployeeConversion.objects.filter(person=self.person_a).exists())

    def test_horilla_direct_conversion_redirects_linked_candidate_to_hydra(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("candidate-conversion", args=(self.candidate_a.pk,)),
            HTTP_HX_REQUEST="true",
        )

        expected = reverse(
            "hydra-person-employee-conversion",
            args=(self.person_a.uuid,),
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response.headers["HX-Redirect"],
            f"{expected}?candidate={self.candidate_a.pk}",
        )
        self.assertIsNone(
            Candidate._base_manager.get(pk=self.candidate_a.pk).converted_employee_id
        )

    def test_original_horilla_conversion_remains_available_for_legacy_candidate(self):
        legacy = self.make_candidate(
            "Legacy conversion",
            "legacy-conversion@example.test",
            self.recruitment_a,
            self.job_a,
            self.stage_a,
        )
        self.client.force_login(self.admin)

        response = self.client.post(reverse("candidate-conversion", args=(legacy.pk,)))

        self.assertEqual(response.status_code, 302)
        legacy.refresh_from_db()
        self.assertIsNotNone(legacy.converted_employee_id)
