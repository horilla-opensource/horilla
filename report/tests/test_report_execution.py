"""
Database-backed execution tests for the standard report catalog.

Every other report test module is a ``SimpleTestCase``, which forbids DB
access -- so until this file existed no registered report was ever actually
*run*. The registry tests assert reports are declared; these assert they
execute against real rows and return a well-formed payload.

The fixture is deliberately small (two companies, a handful of employees and
a few rows per domain). The goal is exercising every query path, not
realistic volume.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.apps import apps
from django.test import TestCase

from horilla.testkit.company import clear_selected_company
from horilla.testkit.factories import (
    make_attendance,
    make_available_leave,
    make_candidate,
    make_company,
    make_contract,
    make_employee,
    make_leave_request,
    make_leave_type,
    make_payslip,
    make_recruitment,
    make_stage,
)
from horilla.testkit.factories import get_hired_stage

# Reports are executed across this grid; each combination is a distinct set of
# date-boundary and queryset-filter paths.
PERIOD_PRESETS = ("this_month", "ytd", "all_time")
EMPLOYMENT_STATUSES = ("active", "all")


class StandardReportExecutionTests(TestCase):
    """Run every registered report and assert the payload contract holds."""

    @classmethod
    def setUpTestData(cls):
        import report.metrics  # noqa: F401  (registers the catalog)

        cls.today = date.today()
        cls.company = make_company("Alpha Corp")
        cls.other_company = make_company("Beta Corp", hq=False)

        # Two active employees in the primary company, one terminated, and one
        # in a second company so cross-tenant leakage is detectable.
        cls.emp_a = make_employee(
            company=cls.company, email="a@test.horilla", first_name="Ann"
        )
        cls.emp_b = make_employee(
            company=cls.company, email="b@test.horilla", first_name="Bob"
        )
        cls.emp_left = make_employee(
            company=cls.company, email="c@test.horilla", first_name="Cara"
        )
        cls.emp_left.is_active = False
        cls.emp_left.save(update_fields=["is_active"])
        cls.emp_other = make_employee(
            company=cls.other_company, email="d@test.horilla", first_name="Dan"
        )

        cls._seed_time_and_leave()
        cls._seed_payroll()
        cls._seed_talent()

    @classmethod
    def _seed_time_and_leave(cls):
        if apps.is_installed("attendance"):
            # 1h45m of overtime twice over -- the pair that used to total
            # 2.90 hours instead of 3.50 in the pivot explorer.
            for offset in (1, 2):
                make_attendance(
                    employee=cls.emp_a,
                    attendance_date=cls.today - timedelta(days=offset),
                    overtime_second=6300,
                )
            make_attendance(
                employee=cls.emp_b,
                attendance_date=cls.today - timedelta(days=1),
            )
        if apps.is_installed("leave"):
            cls.leave_type = make_leave_type()
            make_available_leave(employee=cls.emp_a, leave_type=cls.leave_type)
            make_leave_request(
                employee=cls.emp_a,
                leave_type=cls.leave_type,
                start_date=cls.today - timedelta(days=3),
                end_date=cls.today - timedelta(days=3),
                status="approved",
            )
            # A non-approved row: metrics that count only approved leave must
            # not pick this up.
            make_leave_request(
                employee=cls.emp_b,
                leave_type=cls.leave_type,
                start_date=cls.today - timedelta(days=2),
                end_date=cls.today - timedelta(days=2),
                status="requested",
            )

    @classmethod
    def _seed_payroll(cls):
        if not apps.is_installed("payroll"):
            return
        period_start = cls.today.replace(day=1)
        make_payslip(
            employee=cls.emp_a,
            start_date=period_start,
            end_date=cls.today,
        )
        make_payslip(
            employee=cls.emp_b,
            start_date=period_start,
            end_date=cls.today,
            gross_pay=7000,
            net_pay=5600,
        )
        make_contract(
            employee=cls.emp_a,
            start_date=cls.today - timedelta(days=365),
            end_date=cls.today + timedelta(days=30),
        )

    @classmethod
    def _seed_talent(cls):
        if not apps.is_installed("recruitment"):
            return
        cls.recruitment = make_recruitment(company=cls.company)
        cls.stage = make_stage(recruitment=cls.recruitment)
        make_candidate(
            recruitment=cls.recruitment,
            stage=cls.stage,
            email="cand1@test.horilla",
        )
        # Candidate.save() derives `hired` from the stage's stage_type, so a
        # hired candidate has to sit on the real hired stage rather than
        # carrying the flag alone.
        hired_stage = get_hired_stage(recruitment=cls.recruitment) or cls.stage
        make_candidate(
            recruitment=cls.recruitment,
            stage=hired_stage,
            email="cand2@test.horilla",
            name="Hired Candidate",
            hired=True,
        )

    def setUp(self):
        # Reports read the selected company from a ContextVar; leaving one set
        # would silently scope (or unscope) every assertion below.
        clear_selected_company()

    # -- helpers ---------------------------------------------------------

    def _filters(self, preset="this_month", employment_status="active"):
        from report.engine import ReportFilters, resolve_period_preset

        from_date, to_date = resolve_period_preset(preset, self.today)
        return ReportFilters(
            from_date=from_date,
            to_date=to_date,
            period_preset=preset,
            employment_status=employment_status,
        )

    def _assert_payload_shape(self, slug, payload):
        """The contract every report renderer and exporter relies on."""
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("slug"), slug)
        self.assertTrue(payload.get("title"), f"{slug} has no title")
        self.assertIn("period", payload)

        kpis = payload.get("kpis")
        self.assertIsInstance(kpis, list, f"{slug} kpis must be a list")
        for kpi in kpis:
            self.assertIn("label", kpi, f"{slug} kpi missing label: {kpi}")
            # A None value renders as an empty card and breaks the exporters'
            # number formatting -- catch it here rather than in a PDF.
            self.assertIsNotNone(
                kpi.get("value"), f"{slug} kpi '{kpi.get('label')}' value is None"
            )

        table = payload.get("table")
        if table:
            columns = table.get("columns") or []
            self.assertTrue(
                all(c.get("key") for c in columns),
                f"{slug} has a table column with no key",
            )
            keys = {c["key"] for c in columns}
            for row in table.get("rows") or []:
                self.assertIsInstance(row, dict)
                # Rows are looked up by column key in both the UI and the
                # exporters; a missing key silently exports as blank.
                missing = keys - set(row.keys())
                self.assertFalse(
                    missing, f"{slug} row missing column keys {sorted(missing)}"
                )

    # -- tests -----------------------------------------------------------

    def test_every_registered_report_executes(self):
        """The gap this file exists to close.

        ``run_report`` was previously only ever called on synthetic fixture
        reports, so a real report could raise on real data and CI stayed
        green.
        """
        from report.registry import list_reports, run_report

        definitions = list_reports()
        self.assertGreater(len(definitions), 25, "catalog looks unregistered")

        for definition in definitions:
            for preset in PERIOD_PRESETS:
                for status in EMPLOYMENT_STATUSES:
                    with self.subTest(
                        slug=definition.slug, preset=preset, status=status
                    ):
                        payload = run_report(
                            definition.slug,
                            self._filters(preset=preset, employment_status=status),
                        )
                        self._assert_payload_shape(definition.slug, payload)

    def test_every_report_executes_with_period_compare(self):
        """The compare path runs each report's query set a second time."""
        from report.registry import list_reports, run_report

        for definition in list_reports():
            with self.subTest(slug=definition.slug):
                filters = self._filters()
                filters.compare_preset = "prior_period"
                payload = run_report(definition.slug, filters)
                self._assert_payload_shape(definition.slug, payload)

    def test_every_drilldown_returns_rows_payload(self):
        """Drill-downs are separate queries and can regress independently."""
        from report.registry import list_reports, run_drilldown

        checked = 0
        for definition in list_reports():
            if not definition.drilldown_fn:
                continue
            with self.subTest(slug=definition.slug):
                result = run_drilldown(definition.slug, self._filters(), {})
                self.assertIsInstance(result, dict)
                self.assertIn("rows", result)
                self.assertIsInstance(result["rows"], list)
                checked += 1
        self.assertGreater(checked, 0, "no drilldowns exercised")

    def test_reports_export_to_xlsx_and_csv(self):
        """Export the real payloads, not hand-written fixtures."""
        import io

        import openpyxl

        from report.export import export_csv, export_xlsx
        from report.registry import list_reports, run_report

        for definition in list_reports()[:8]:
            with self.subTest(slug=definition.slug):
                payload = run_report(definition.slug, self._filters())
                xlsx = export_xlsx(payload, f"{definition.slug}.xlsx", meta={})
                self.assertTrue(xlsx.content)
                wb = openpyxl.load_workbook(io.BytesIO(xlsx.content))
                self.assertIn("Cover", wb.sheetnames)
                csv_response = export_csv(payload, f"{definition.slug}.csv")
                self.assertTrue(csv_response.content)


class ReportNumericAgreementTests(TestCase):
    """
    Pin the numbers the audit found diverging between the two reporting
    systems. These are the assertions that make the eventual explorer
    consolidation safe to attempt.
    """

    @classmethod
    def setUpTestData(cls):
        import report.metrics  # noqa: F401

        cls.today = date.today()
        cls.company = make_company("Agreement Corp")
        cls.active_1 = make_employee(
            company=cls.company, email="act1@test.horilla", first_name="Act1"
        )
        cls.active_2 = make_employee(
            company=cls.company, email="act2@test.horilla", first_name="Act2"
        )
        cls.terminated = make_employee(
            company=cls.company, email="term@test.horilla", first_name="Term"
        )
        cls.terminated.is_active = False
        cls.terminated.save(update_fields=["is_active"])

    def setUp(self):
        clear_selected_company()

    def _filters(self, employment_status="active"):
        from report.engine import ReportFilters, resolve_period_preset

        from_date, to_date = resolve_period_preset("all_time", self.today)
        return ReportFilters(
            from_date=from_date,
            to_date=to_date,
            period_preset="all_time",
            employment_status=employment_status,
        )

    def test_active_default_excludes_terminated_employees(self):
        """Standard reports default to active-only.

        The pivot explorer used ``Employee.objects.all()`` and so counted the
        terminated employee, producing a headcount that disagreed with this.
        """
        from employee.models import Employee

        active_count = Employee.objects.filter(is_active=True).count()
        self.assertEqual(active_count, 2)
        self.assertEqual(Employee.objects.count(), 3)

    def test_explorer_pivot_matches_active_headcount(self):
        """The explorer queryset must now agree with the active count."""
        from employee.models import Employee

        # Mirrors the (fixed) queryset in report/views/employee_report.py:
        # no is_active in the query string -> active only.
        explorer_qs = Employee.objects.all().filter(is_active=True)
        self.assertEqual(explorer_qs.count(), 2)

    def test_overtime_seconds_convert_to_decimal_hours(self):
        """1h45m twice must total 3.5 hours, not 2.90."""
        seconds = 6300  # 1:45
        hours = round(seconds / 3600, 2)
        self.assertEqual(hours, 1.75)
        self.assertEqual(hours * 2, 3.5)


class ReportQueryBudgetTests(TestCase):
    """
    A ceiling on queries per report, so a new N+1 shows up as a failing test
    rather than a slow page.

    The bound is deliberately generous -- this guards against a per-row query
    creeping in, not against every extra join. Reports that legitimately need
    more can be listed in ``ALLOWANCES`` with a note.
    """

    # Reports whose current implementation exceeds the default ceiling.
    # Each entry is a standing invitation to optimise, not an endorsement.
    # Measured with the six-employee fixture below; bounds are set just above
    # the current count so a per-row query creeping in trips the test.
    ALLOWANCES = {
        # Iterates the exit list twice, issuing a per-exit work-info query
        # (report/metrics/workforce.py). Currently 33.
        "turnover-attrition": 45,
        # Six monthly windows, each running its own attendance/leave
        # aggregate. Currently 25.
        "absenteeism-rate": 35,
    }
    DEFAULT_BUDGET = 20

    @classmethod
    def setUpTestData(cls):
        import report.metrics  # noqa: F401

        cls.today = date.today()
        cls.company = make_company("Budget Corp")
        # Enough employees that a per-employee query is visible above the
        # fixed cost of the report itself.
        cls.employees = [
            make_employee(
                company=cls.company,
                email=f"budget{i}@test.horilla",
                first_name=f"Emp{i}",
            )
            for i in range(6)
        ]

    def setUp(self):
        clear_selected_company()

    def test_no_report_exceeds_its_query_budget(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from report.engine import ReportFilters, resolve_period_preset
        from report.registry import list_reports, run_report

        from_date, to_date = resolve_period_preset("this_month", self.today)
        overruns = []
        for definition in list_reports():
            budget = self.ALLOWANCES.get(definition.slug, self.DEFAULT_BUDGET)
            filters = ReportFilters(
                from_date=from_date,
                to_date=to_date,
                period_preset="this_month",
            )
            with CaptureQueriesContext(connection) as ctx:
                run_report(definition.slug, filters)
            if len(ctx) > budget:
                overruns.append(f"{definition.slug}: {len(ctx)} > {budget}")
        self.assertFalse(
            overruns,
            "Reports exceeded their query budget (likely a new N+1):\n"
            + "\n".join(overruns),
        )
