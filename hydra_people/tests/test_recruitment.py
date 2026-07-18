from datetime import date

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from base.models import Company, Department, JobPosition
from employee.models import Employee
from hydra_coordination.models import Location, PersonAssignment, ScopeGrant, Section, Team
from hydra_coordination.services import assign_person
from hydra_people.models import Person, PersonApplication
from hydra_people.services import link_candidate, save_person
from recruitment.models import Candidate, Recruitment, Stage


class HydraRecruitmentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="recruitment-admin",
            email="recruitment-admin@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.admin_employee = Employee.objects.create(
            employee_user_id=cls.admin,
            employee_first_name="Recruitment",
            employee_last_name="Admin",
            email="recruitment-admin@example.test",
            phone="+48100000000",
        )
        cls.user = User.objects.create_user(
            username="team-a-recruiter",
            email="team-a-recruiter@example.test",
            password="test-password",
            is_new_employee=False,
        )
        cls.employee = Employee.objects.create(
            employee_user_id=cls.user,
            employee_first_name="Team A",
            employee_last_name="Recruiter",
            email="team-a-recruiter@example.test",
            phone="+48111111111",
        )
        cls.company_a = cls.make_company("Hydra Recruitment A", "A Street")
        cls.company_b = cls.make_company("Hydra Recruitment B", "B Street")
        cls.employee.employee_work_info.company_id = cls.company_a
        cls.employee.employee_work_info.save()
        cls.admin_employee.employee_work_info.company_id = cls.company_a
        cls.admin_employee.employee_work_info.save()

        cls.department_a = cls.make_department("Production A", cls.company_a)
        cls.department_b = cls.make_department("Production B", cls.company_b)
        cls.job_a = cls.make_job("Greenhouse A", cls.department_a, cls.company_a)
        cls.job_b = cls.make_job("Greenhouse B", cls.department_b, cls.company_b)
        cls.recruitment_a, cls.stage_a = cls.make_recruitment(
            "Hydra intake A", cls.company_a, cls.job_a
        )
        cls.recruitment_b, cls.stage_b = cls.make_recruitment(
            "Hydra intake B", cls.company_b, cls.job_b
        )

        location_a = Location.objects.create(
            company=cls.company_a, name="Location A", code="LOC-A"
        )
        location_b = Location.objects.create(
            company=cls.company_b, name="Location B", code="LOC-B"
        )
        section_a = Section.objects.create(
            location=location_a,
            department=cls.department_a,
            name="Section A",
            code="SEC-A",
        )
        section_b = Section.objects.create(
            location=location_b,
            department=cls.department_b,
            name="Section B",
            code="SEC-B",
        )
        cls.team_a = Team.objects.create(
            section=section_a, name="Team A", code="TEAM-A"
        )
        cls.team_b = Team.objects.create(
            section=section_b, name="Team B", code="TEAM-B"
        )
        cls.person_a = cls.make_person("ANNA ALPHA", "Anna", "Alpha")
        cls.person_b = cls.make_person("BOHDAN BETA", "Bohdan", "Beta")
        cls.person_c = cls.make_person("CELINA ALPHA", "Celina", "Alpha")
        for person, team, department in (
            (cls.person_a, cls.team_a, cls.department_a),
            (cls.person_b, cls.team_b, cls.department_b),
            (cls.person_c, cls.team_a, cls.department_a),
        ):
            assign_person(
                assignment=PersonAssignment(
                    person=person,
                    team=team,
                    department=department,
                ),
                actor=cls.admin,
            )
        ScopeGrant.objects.create(user=cls.user, team=cls.team_a)

        cls.candidate_a = cls.make_candidate(
            "Anna application",
            "anna.application@example.test",
            cls.recruitment_a,
            cls.job_a,
            cls.stage_a,
        )
        cls.candidate_b = cls.make_candidate(
            "Bohdan application",
            "bohdan.application@example.test",
            cls.recruitment_b,
            cls.job_b,
            cls.stage_b,
        )
        link_candidate(person=cls.person_a, candidate=cls.candidate_a, actor=cls.admin)
        link_candidate(person=cls.person_b, candidate=cls.candidate_b, actor=cls.admin)
        from hydra_legalization.models import (
            LegalizationAuthority,
            LegalizationAuthorityEvent,
            LegalizationProcedureType,
        )

        cls.legalization_authority = LegalizationAuthority.objects.create(
            code="test-competent-authority",
            name="Lower Silesian Office",
            jurisdiction="Test jurisdiction",
            allowed_channels=list(LegalizationAuthorityEvent.Channel.values),
            created_by=cls.admin,
            modified_by=cls.admin,
        )
        for procedure in LegalizationProcedureType.objects.all():
            procedure.authorities.add(cls.legalization_authority)
        cls.unlinked_a = cls.make_candidate(
            "Legacy A",
            "legacy-a@example.test",
            cls.recruitment_a,
            cls.job_a,
            cls.stage_a,
        )
        cls.unlinked_b = cls.make_candidate(
            "Legacy B",
            "legacy-b@example.test",
            cls.recruitment_b,
            cls.job_b,
            cls.stage_b,
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

    @classmethod
    def make_job(cls, name, department, company):
        job = JobPosition.objects.create(job_position=name, department_id=department)
        job.company_id.add(company)
        return job

    @classmethod
    def make_recruitment(cls, title, company, job):
        recruitment = Recruitment.default.create(
            title=title,
            description="Test recruitment",
            company_id=company,
            vacancy=5,
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
    def make_person(cls, passport_name, first_name, last_name):
        return save_person(
            person=Person(
                passport_name=passport_name,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date(1992, 4, 5),
                gender=Person.Gender.FEMALE,
                citizenship="UA",
                preferred_language=Person.PreferredLanguage.UKRAINIAN,
            ),
            actor=cls.admin,
        )

    @classmethod
    def make_candidate(cls, name, email, recruitment, job, stage):
        candidate = Candidate(
            name=name,
            email=email,
            resume="",
            recruitment_id=recruitment,
            job_position_id=job,
            stage_id=stage,
        )
        Candidate._base_manager.bulk_create([candidate])
        return Candidate._base_manager.get(pk=candidate.pk)

    def setUp(self):
        self.user = User.objects.get(pk=self.user.pk)

    def grant(self, *permissions):
        for app_label, codename in permissions:
            self.user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def login(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["selected_company"] = "all"
        session.save()

    def grant_read(self):
        self.grant(
            ("hydra_people", "view_person"),
            ("recruitment", "view_candidate"),
        )

    def grant_write(self):
        self.grant_read()
        self.grant(
            ("hydra_people", "change_person"),
            ("hydra_people", "link_candidate"),
            ("recruitment", "add_candidate"),
            ("recruitment", "view_recruitment"),
        )

    @classmethod
    def legalization_case_configuration(cls, *, company, case_type="work_permit"):
        from hydra_legalization.models import LegalizationProcedureType

        procedure = LegalizationProcedureType.objects.get(
            company__isnull=True,
            case_type=case_type,
        )
        return {
            "company": company,
            "procedure_type": procedure,
            "procedure_snapshot": procedure.rules_snapshot(company_id=company.pk),
        }


class RecruitmentScopeAndPermissionTests(HydraRecruitmentTestCase):
    def test_list_and_direct_detail_intersect_permission_person_and_team_scope(self):
        self.grant_read()
        self.login()

        response = self.client.get(reverse("hydra-recruitment-list"))
        denied = self.client.get(
            reverse("hydra-recruitment-detail", args=(self.candidate_b.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.person_a.hydra_id)
        self.assertNotContains(response, self.person_b.hydra_id)
        self.assertContains(response, 'aria-current="page"')
        self.assertEqual(denied.status_code, 404)

    def test_missing_model_permission_returns_403(self):
        self.login()

        response = self.client.get(reverse("hydra-recruitment-list"))

        self.assertEqual(response.status_code, 403)

    def test_backfill_queue_and_direct_url_are_company_scoped(self):
        self.grant_write()
        self.login()

        team_scope_only = self.client.get(
            reverse("hydra-recruitment-link-person", args=(self.unlinked_a.pk,))
        )
        ScopeGrant.objects.create(user=self.user, company=self.company_a)
        allowed = self.client.get(
            reverse("hydra-recruitment-link-person", args=(self.unlinked_a.pk,))
        )
        denied = self.client.get(
            reverse("hydra-recruitment-link-person", args=(self.unlinked_b.pk,))
        )

        self.assertEqual(team_scope_only.status_code, 404)
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, self.person_c.hydra_id)
        self.assertNotContains(allowed, self.person_b.hydra_id)
        self.assertEqual(denied.status_code, 404)


class RecruitmentApplicationWorkflowTests(HydraRecruitmentTestCase):
    def test_create_form_lists_only_positions_from_scoped_recruitments(self):
        self.grant_write()
        self.login()

        response = self.client.get(
            reverse("hydra-recruitment-create", args=(self.person_c.uuid,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.job_a.job_position)
        self.assertNotContains(response, self.job_b.job_position)

    def test_hydra_intake_creates_standard_candidate_and_person_link(self):
        self.grant_write()
        self.login()

        response = self.client.post(
            reverse("hydra-recruitment-create", args=(self.person_c.uuid,)),
            {
                "recruitment_id": self.recruitment_a.pk,
                "job_position_id": self.job_a.pk,
                "email": "celina.application@example.test",
                "mobile": "+48123456789",
                "source": "software",
            },
        )

        self.assertEqual(response.status_code, 302)
        candidate = Candidate._base_manager.get(email="celina.application@example.test")
        link = candidate.hydra_person_link
        self.assertEqual(candidate.name, self.person_c.passport_name)
        self.assertEqual(candidate.dob, self.person_c.date_of_birth)
        self.assertEqual(candidate.stage_id, self.stage_a)
        self.assertEqual(link.person, self.person_c)
        self.assertEqual(link.link_source, PersonApplication.LinkSource.HYDRA_INTAKE)

    def test_duplicate_person_recruitment_is_rejected_without_partial_write(self):
        self.grant_write()
        self.login()
        url = reverse("hydra-recruitment-create", args=(self.person_c.uuid,))
        base_payload = {
            "recruitment_id": self.recruitment_a.pk,
            "job_position_id": self.job_a.pk,
            "mobile": "",
            "source": "software",
        }
        first = self.client.post(
            url,
            {**base_payload, "email": "celina-first@example.test"},
        )
        candidate_count = Candidate._base_manager.count()

        second = self.client.post(
            url,
            {**base_payload, "email": "celina-second@example.test"},
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 200)
        self.assertContains(second, "already has an application")
        self.assertEqual(Candidate._base_manager.count(), candidate_count)

    def test_reviewed_backfill_records_link_source(self):
        self.grant_write()
        ScopeGrant.objects.create(user=self.user, company=self.company_a)
        self.login()

        response = self.client.post(
            reverse("hydra-recruitment-link-person", args=(self.unlinked_a.pk,)),
            {"person": self.person_c.pk},
        )

        self.assertEqual(response.status_code, 302)
        link = PersonApplication.objects.get(candidate=self.unlinked_a)
        self.assertEqual(link.person, self.person_c)
        self.assertEqual(link.link_source, PersonApplication.LinkSource.BACKFILL)

    def test_existing_hydra_candidate_view_remains_operational(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("candidate-view"))

        self.assertEqual(response.status_code, 200)
