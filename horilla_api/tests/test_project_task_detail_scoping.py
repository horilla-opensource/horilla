"""The project and task detail endpoints apply the scope their list endpoints apply."""

from datetime import date

from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from horilla.testkit import make_company, make_employee, make_user
from project.models import Project, ProjectStage, Task


class ProjectTaskDetailScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = make_company("Project Co")
        cls.plain_user = make_user("prj_plain", password="secret123")
        make_employee(
            company=company, email="prj_plain@test.horilla", user=cls.plain_user
        )
        cls.viewer_user = make_user("prj_viewer", password="secret123")
        make_employee(
            company=company, email="prj_viewer@test.horilla", user=cls.viewer_user
        )
        cls.viewer_user.user_permissions.add(
            Permission.objects.get(codename="view_project"),
            Permission.objects.get(codename="view_task"),
        )
        cls.project = Project.objects.create(
            title="Confidential merger", status="new", start_date=date.today()
        )
        # Creating a project already creates its default stage.
        stage = ProjectStage.objects.filter(project=cls.project).first()
        cls.task = Task.objects.create(
            title="Draft the announcement", project=cls.project, stage=stage
        )

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user=type(user).objects.get(pk=user.pk))
        return client

    def test_plain_employee_cannot_read_a_project_by_id(self):
        response = self._client(self.plain_user).get(
            f"/api/v1/project/project/{self.project.pk}/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Confidential", response.content.decode())

    def test_plain_employee_cannot_read_a_task_by_id(self):
        response = self._client(self.plain_user).get(
            f"/api/v1/project/task/{self.task.pk}/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("announcement", response.content.decode())

    def test_the_list_hides_them_too(self):
        """The scope the detail now matches."""
        response = self._client(self.plain_user).get("/api/v1/project/project/")
        self.assertNotIn("Confidential", response.content.decode())

    def test_permission_holder_still_reads_both(self):
        """A fix that denies everyone would pass the tests above."""
        client = self._client(self.viewer_user)
        project = client.get(f"/api/v1/project/project/{self.project.pk}/")
        task = client.get(f"/api/v1/project/task/{self.task.pk}/")
        self.assertEqual(project.status_code, 200)
        self.assertIn("Confidential", project.content.decode())
        self.assertEqual(task.status_code, 200)
        self.assertIn("announcement", task.content.decode())
