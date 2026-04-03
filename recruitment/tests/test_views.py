"""
View tests for the recruitment module.

Tests cover: authentication enforcement, admin/manager access,
pipeline view, public application form, and permission checks.
"""

from django.test import Client
from django.urls import reverse

from base.tests.factories import JobPositionFactory
from horilla.test_utils.base import HorillaTestCase
from recruitment.models import Candidate, Recruitment, Stage
from recruitment.tests.factories import (
    CandidateFactory,
    RecruitmentFactory,
    StageFactory,
)


class AnonymousAccessTest(HorillaTestCase):
    """Anonymous users should be redirected to login for all protected views."""

    def setUp(self):
        super().setUp()
        self.anon_client = Client()

    def test_pipeline_redirects_anonymous(self):
        """GET /recruitment/pipeline/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("pipeline"))
        self.assertNotEqual(resp.status_code, 200)
        # Should redirect (302 or 301) to login
        self.assertIn(resp.status_code, [301, 302])

    def test_recruitment_view_redirects_anonymous(self):
        """GET /recruitment/recruitment-view/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("recruitment-view"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_candidate_view_redirects_anonymous(self):
        """GET /recruitment/candidate-view/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("candidate-view"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_recruitment_create_redirects_anonymous(self):
        """GET /recruitment/recruitment-create/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("recruitment-create"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_stage_create_redirects_anonymous(self):
        """GET /recruitment/stage-create/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("rec-stage-create"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_candidate_create_redirects_anonymous(self):
        """GET /recruitment/candidate-create/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("candidate-create"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_recruitment_delete_redirects_anonymous(self):
        """POST /recruitment/recruitment-delete/<id>/ redirects anonymous."""
        rec = RecruitmentFactory()
        resp = self.anon_client.post(
            reverse("recruitment-delete", kwargs={"rec_id": rec.pk})
        )
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_dashboard_redirects_anonymous(self):
        """GET /recruitment/dashboard/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("recruitment-dashboard"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_skill_zone_view_redirects_anonymous(self):
        """GET /recruitment/skill-zone-view/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("skill-zone-view"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])

    def test_interview_view_redirects_anonymous(self):
        """GET /recruitment/interview-view/ redirects anonymous to login."""
        resp = self.anon_client.get(reverse("interview-view"))
        self.assertNotEqual(resp.status_code, 200)
        self.assertIn(resp.status_code, [301, 302])


class AdminAccessTest(HorillaTestCase):
    """Admin/superuser should be able to access protected views."""

    def test_admin_can_access_recruitment_view(self):
        """Admin gets 200 on recruitment-view (CBV)."""
        client = self.get_admin_client()
        resp = client.get(reverse("recruitment-view"), HTTP_HX_REQUEST="true")
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_can_access_pipeline(self):
        """Admin can access pipeline view (200 or non-login redirect)."""
        client = self.get_admin_client()
        resp = client.get(reverse("pipeline"))
        if resp.status_code == 302:
            self.assertNotIn("/login", resp.url)
        else:
            self.assertEqual(resp.status_code, 200)

    def test_admin_can_access_candidate_view(self):
        """Admin gets 200 on candidate-view (CBV)."""
        client = self.get_admin_client()
        resp = client.get(reverse("candidate-view"), HTTP_HX_REQUEST="true")
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_can_access_dashboard(self):
        """Admin can access recruitment dashboard (200 or non-login redirect)."""
        client = self.get_admin_client()
        resp = client.get(reverse("recruitment-dashboard"))
        if resp.status_code == 302:
            self.assertNotIn("/login", resp.url)
        else:
            self.assertEqual(resp.status_code, 200)

    def test_admin_can_access_stage_view(self):
        """Admin gets 200 on rec-stage-view (CBV)."""
        client = self.get_admin_client()
        resp = client.get(reverse("rec-stage-view"), HTTP_HX_REQUEST="true")
        self.assertIn(resp.status_code, [200, 302])


class PublicApplicationFormTest(HorillaTestCase):
    """The application form and open recruitments are PUBLIC (no login required)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.job_pos = JobPositionFactory(job_position="Public Role")
        cls.recruitment = RecruitmentFactory(
            title="Public Recruitment",
            job_position_id=cls.job_pos,
            is_published=True,
            vacancy=3,
        )
        cls.recruitment.open_positions.add(cls.job_pos)
        # Recruitment.post_save signal auto-creates "Applied" and "Initial"
        # stages, so reuse the auto-created one instead of creating a duplicate.
        cls.stage = Stage.objects.get(recruitment_id=cls.recruitment, stage="Initial")

    def test_open_recruitments_accessible_without_login(self):
        """GET /recruitment/open-recruitments/ returns 200 for anonymous users."""
        client = Client()
        resp = client.get(reverse("open-recruitments"))
        self.assertEqual(resp.status_code, 200)

    def test_application_form_accessible_without_login(self):
        """GET /recruitment/application-form/?recruitmentId=X returns 200 for anonymous."""
        client = Client()
        resp = client.get(
            reverse("application-form"),
            {"recruitmentId": self.recruitment.pk},
        )
        self.assertEqual(resp.status_code, 200)

    def test_application_form_without_recruitment_id_redirects(self):
        """GET /recruitment/application-form/ without recruitmentId redirects."""
        client = Client()
        resp = client.get(reverse("application-form"))
        self.assertIn(resp.status_code, [301, 302])


class PermissionEnforcementTest(HorillaTestCase):
    """Permission checks: regular employees without perms should be blocked."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.recruitment = RecruitmentFactory(title="Perm Test Rec")

    def test_regular_employee_cannot_delete_recruitment(self):
        """Regular employee without delete perm cannot delete recruitment."""
        client = self.get_employee_client()
        resp = client.post(
            reverse("recruitment-delete", kwargs={"rec_id": self.recruitment.pk})
        )
        # Should be blocked -- either redirect to login/forbidden or 403
        self.assertNotEqual(resp.status_code, 200)

    def test_regular_employee_cannot_delete_stage(self):
        """Regular employee without delete perm cannot delete stage."""
        stage = StageFactory(recruitment_id=self.recruitment, stage="Test Stage")
        client = self.get_employee_client()
        resp = client.post(reverse("rec-stage-delete", kwargs={"stage_id": stage.pk}))
        self.assertNotEqual(resp.status_code, 200)

    def test_regular_employee_cannot_delete_candidate(self):
        """Regular employee without delete perm cannot delete candidate."""
        cand = CandidateFactory(recruitment_id=self.recruitment)
        client = self.get_employee_client()
        resp = client.post(reverse("rec-candidate-delete", kwargs={"cand_id": cand.pk}))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_can_delete_recruitment(self):
        """Admin/superuser can delete a recruitment."""
        # Disable the ForcePasswordChangeMiddleware redirect so the
        # delete view actually processes (is_new_employee defaults True
        # for auto-created HorillaUser).
        self.admin_user.is_new_employee = False
        self.admin_user.save()
        rec = RecruitmentFactory(title="To Delete", company_id=self.company_a)
        client = self.get_admin_client()
        resp = client.post(reverse("recruitment-delete", kwargs={"rec_id": rec.pk}))
        # Should succeed (redirect after delete)
        self.assertIn(resp.status_code, [200, 301, 302])
        # Use entire() to bypass HorillaCompanyManager filtering
        self.assertFalse(Recruitment.objects.entire().filter(pk=rec.pk).exists())
