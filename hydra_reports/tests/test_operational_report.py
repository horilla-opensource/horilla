import csv
import hashlib
from datetime import timedelta
from io import StringIO

from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils import timezone

from hydra_arrivals.models import ArrivalPlan
from hydra_coordination.models import ScopeGrant
from hydra_legalization.models import LegalizationCase
from hydra_people.tests.test_recruitment import HydraRecruitmentTestCase
from hydra_reports.models import OperationalReportExport
from hydra_reports.services import create_operational_report_export
from hydra_shell.templatetags.hydra_shell_tags import hydra_nav_is_active


class OperationalReportTestCase(HydraRecruitmentTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.location_a = cls.team_a.section.location
        cls.location_b = cls.team_b.section.location
        cls.arrival_a = ArrivalPlan.objects.create(
            person=cls.person_a,
            candidate=cls.candidate_a,
            destination_location=cls.location_a,
            coordinator=cls.admin,
            planned_at=timezone.now() - timedelta(days=1),
            status=ArrivalPlan.Status.PLANNED,
        )
        cls.arrival_b = ArrivalPlan.objects.create(
            person=cls.person_b,
            candidate=cls.candidate_b,
            destination_location=cls.location_b,
            coordinator=cls.admin,
            planned_at=timezone.now() + timedelta(days=2),
            status=ArrivalPlan.Status.PLANNED,
        )
        cls.case_a = LegalizationCase.objects.create(
            person=cls.person_a,
            case_type=LegalizationCase.CaseType.WORK_PERMIT,
            status=LegalizationCase.Status.SUBMITTED,
            responsible=cls.admin,
            deadline=timezone.localdate() + timedelta(days=10),
        )
        cls.case_b = LegalizationCase.objects.create(
            person=cls.person_b,
            case_type=LegalizationCase.CaseType.VISA,
            status=LegalizationCase.Status.SUBMITTED,
            responsible=cls.admin,
            deadline=timezone.localdate() + timedelta(days=10),
        )

    def grant_report_dependencies(self):
        self.grant(
            ("hydra_people", "view_person"),
            ("hydra_coordination", "view_personassignment"),
            ("hydra_coordination", "view_location"),
            ("hydra_coordination", "view_team"),
            ("hydra_arrivals", "view_arrivalplan"),
            ("recruitment", "view_candidate"),
            ("hydra_legalization", "view_legalizationcase"),
        )

    def grant_report_view(self):
        self.grant_report_dependencies()
        self.grant(("hydra_reports", "view_operational_report"))

    def grant_report_export(self):
        self.grant_report_view()
        self.grant(
            ("hydra_reports", "export_operational_report"),
            ("hydra_reports", "view_operationalreportexport"),
        )

    @staticmethod
    def filters(**overrides):
        filters = {
            "q": "",
            "lifecycle": "",
            "location": None,
            "team": None,
            "arrival_status": "",
            "legalization_status": "",
            "attention": "",
        }
        filters.update(overrides)
        return filters


class OperationalReportScopeTests(OperationalReportTestCase):
    def test_report_intersects_permissions_scope_and_active_navigation(self):
        self.grant_report_view()
        self.login()

        response = self.client.get(reverse("hydra-operational-report"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.person_a.hydra_id)
        self.assertContains(response, self.person_c.hydra_id)
        self.assertNotContains(response, self.person_b.hydra_id)
        self.assertEqual(response.context["summary"].total_people, 2)
        self.assertTrue(hydra_nav_is_active(response.context, "reports"))
        self.assertContains(response, 'aria-current="page"')

    def test_missing_report_permission_returns_403(self):
        self.grant_report_dependencies()
        self.login()

        response = self.client.get(reverse("hydra-operational-report"))

        self.assertEqual(response.status_code, 403)

    def test_missing_domain_permission_returns_403(self):
        self.grant(("hydra_reports", "view_operational_report"))
        self.login()

        response = self.client.get(reverse("hydra-operational-report"))

        self.assertEqual(response.status_code, 403)

    def test_forged_location_filter_and_company_all_do_not_widen_scope(self):
        self.grant_report_view()
        self.login()

        response = self.client.get(
            reverse("hydra-operational-report"),
            {"location": self.location_b.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertNotContains(response, self.person_b.hydra_id)
        self.assertEqual(response.context["summary"].total_people, 0)

    def test_location_team_and_attention_filters_remain_scoped(self):
        self.grant_report_view()
        ScopeGrant.objects.create(user=self.user, location=self.location_a)
        self.login()

        response = self.client.get(
            reverse("hydra-operational-report"),
            {
                "location": self.location_a.pk,
                "team": self.team_a.pk,
                "attention": "arrival",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.person_a.hydra_id)
        self.assertNotContains(response, self.person_c.hydra_id)
        self.assertNotContains(response, self.person_b.hydra_id)
        self.assertContains(response, "Arrival overdue")


class OperationalReportExportTests(OperationalReportTestCase):
    def test_missing_export_permission_returns_403(self):
        self.grant_report_view()
        self.login()

        response = self.client.post(reverse("hydra-operational-report-export"), {})

        self.assertEqual(response.status_code, 403)

    def test_csv_is_scoped_formula_safe_private_and_audited(self):
        self.grant_report_export()
        self.login()
        type(self.person_a).objects.filter(pk=self.person_a.pk).update(
            passport_name="=2+2"
        )

        response = self.client.post(reverse("hydra-operational-report-export"), {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
        exported_ids = {row["HYDRA_ID"] for row in rows}
        self.assertEqual(exported_ids, {self.person_a.hydra_id, self.person_c.hydra_id})
        self.assertNotIn(self.person_b.hydra_id, exported_ids)
        self.assertIn("'=2+2", {row["PASSPORT_NAME"] for row in rows})
        audit = OperationalReportExport.objects.get()
        self.assertEqual(audit.actor, self.user)
        self.assertEqual(audit.row_count, 2)
        self.assertEqual(audit.sha256, hashlib.sha256(response.content).hexdigest())
        self.assertEqual(audit.scope_location_ids, [self.location_a.pk])
        self.assertEqual(audit.scope_team_ids, [self.team_a.pk])

    def test_out_of_scope_export_filter_is_rejected_without_audit(self):
        self.grant_report_export()
        self.login()

        response = self.client.post(
            reverse("hydra-operational-report-export"),
            {"location": self.location_b.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(OperationalReportExport.objects.exists())

    def test_export_service_rechecks_filter_scope(self):
        self.grant_report_export()

        with self.assertRaises(PermissionDenied):
            create_operational_report_export(
                actor=self.user,
                filters=self.filters(location=self.location_b),
            )
        self.assertFalse(OperationalReportExport.objects.exists())

    def test_export_uses_exact_filtered_rows(self):
        self.grant_report_export()
        ScopeGrant.objects.create(user=self.user, location=self.location_a)
        self.login()

        response = self.client.post(
            reverse("hydra-operational-report-export"),
            {"attention": "arrival"},
        )

        rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual([row["HYDRA_ID"] for row in rows], [self.person_a.hydra_id])
        self.assertEqual(rows[0]["ARRIVAL_STATUS"], ArrivalPlan.Status.PLANNED)
        self.assertIn("arrival_overdue", rows[0]["ATTENTION_FLAGS"])

    def test_export_audit_is_append_only(self):
        audit = OperationalReportExport.objects.create(
            actor=self.admin,
            format=OperationalReportExport.Format.CSV,
            filename="audit.csv",
            row_count=0,
            sha256="0" * 64,
            filters={},
            scope_location_ids=[],
            scope_team_ids=[],
        )

        audit.row_count = 2
        with self.assertRaisesMessage(TypeError, "append-only"):
            audit.save()
        with self.assertRaisesMessage(TypeError, "append-only"):
            audit.delete()
        with self.assertRaisesMessage(TypeError, "append-only"):
            OperationalReportExport.objects.update(row_count=2)
        with self.assertRaisesMessage(TypeError, "append-only"):
            OperationalReportExport.objects.all().delete()

    def test_recent_audit_is_actor_scoped(self):
        self.grant_report_export()
        own = OperationalReportExport.objects.create(
            actor=self.user,
            format="csv",
            filename="own.csv",
            row_count=1,
            sha256="a" * 64,
            filters={},
            scope_location_ids=[],
            scope_team_ids=[],
        )
        OperationalReportExport.objects.create(
            actor=self.admin,
            format="csv",
            filename="admin.csv",
            row_count=1,
            sha256="b" * 64,
            filters={},
            scope_location_ids=[],
            scope_team_ids=[],
        )
        self.login()

        response = self.client.get(reverse("hydra-operational-report"))

        self.assertContains(response, own.sha256)
        self.assertNotContains(response, "b" * 64)

    def test_existing_horilla_employee_view_remains_operational(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("employee-view"))

        self.assertEqual(response.status_code, 200)
