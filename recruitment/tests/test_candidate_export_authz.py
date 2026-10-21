"""Exporting candidates takes the same permission as listing them."""

from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from base.models import Department, JobPosition
from horilla.testkit import make_company, make_employee, make_user
from recruitment.models import Candidate, Recruitment


class CandidateExportAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Candidate Export Co")
        cls.plain_user = make_user("cx_plain", password="secret123")
        make_employee(
            company=company, email="cx_plain@test.horilla", user=cls.plain_user
        )
        cls.hr_user = make_user("cx_hr", password="secret123")
        make_employee(company=company, email="cx_hr@test.horilla", user=cls.hr_user)
        cls.hr_user.user_permissions.add(
            Permission.objects.get(codename="view_candidate")
        )
        department = Department.objects.create(department="Engineering")
        job_position = JobPosition.objects.create(
            job_position="Engineer", department_id=department
        )
        recruitment = Recruitment.objects.create(
            title="Engineer", closed=False, is_active=True
        )
        recruitment.open_positions.add(job_position)
        Candidate.objects.create(
            name="Exported Applicant",
            email="applicant@example.com",
            mobile="1000000000",
            recruitment_id=recruitment,
            job_position_id=job_position,
            stage_id=recruitment.stage_set.first(),
            resume=SimpleUploadedFile("a.pdf", b"%PDF-1.4 test"),
        )

    def _export(self, user):
        client = Client()
        client.force_login(type(user).objects.get(pk=user.pk))
        return client.get(reverse("candidate-info-export"))

    def test_employee_without_the_permission_gets_no_file(self):
        response = self._export(self.plain_user)
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn(b"Exported Applicant", response.content)

    def test_permission_holder_still_gets_the_export(self):
        response = self._export(self.hr_user)
        self.assertEqual(response.status_code, 200)
        self.assertIn("excel", response["Content-Type"])
