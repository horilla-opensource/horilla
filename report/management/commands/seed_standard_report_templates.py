from django.core.management.base import BaseCommand

from report.models import ReportTemplate

# Default pivot layouts for deep-linking from standard reports into Explorer.
SYSTEM_TEMPLATES = [
    {
        "report_slug": "employee_report",
        "name": "Workforce Composition",
        "config": {
            "rows": ["Department"],
            "cols": ["Employee Type"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "employee_report",
        "name": "Diversity Snapshot",
        "config": {
            "rows": ["Gender"],
            "cols": ["Department"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "employee_report",
        "name": "Headcount by Job Position",
        "config": {
            "rows": ["Job Position"],
            "cols": ["Department"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "employee_report",
        "name": "Company Overview",
        "config": {
            "rows": ["Company"],
            "cols": ["Work Type"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "attendance_report",
        "name": "Attendance Summary",
        "config": {
            "rows": ["Department"],
            "cols": ["Attendance Day"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "attendance_report",
        "name": "Overtime by Department",
        "config": {
            "rows": ["Department"],
            "cols": [],
            "rendererName": "Table",
            "aggregatorName": "Sum",
            "vals": ["Overtime Decimal"],
        },
    },
    {
        "report_slug": "attendance_report",
        "name": "Attendance by Work Type",
        "config": {
            "rows": ["Work Type"],
            "cols": ["Attendance Day"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "leave_report_leave_request",
        "name": "Leave Utilization",
        "config": {
            "rows": ["Leave Type"],
            "cols": ["Status"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "leave_report_leave_request",
        "name": "Leave Days by Department",
        "config": {
            "rows": ["Department"],
            "cols": [],
            "rendererName": "Table",
            "aggregatorName": "Sum",
            "vals": ["Requested Days"],
        },
    },
    {
        "report_slug": "leave_report_leave_request",
        "name": "Leave Requests by Status",
        "config": {
            "rows": ["Status"],
            "cols": ["Leave Type"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "payroll_report_payslip",
        "name": "Labor Cost Summary",
        "config": {
            "rows": ["Department"],
            "cols": [],
            "rendererName": "Table",
            "aggregatorName": "Sum",
            "vals": ["Gross Pay"],
        },
    },
    {
        "report_slug": "payroll_report_payslip",
        "name": "Net Pay by Department",
        "config": {
            "rows": ["Department"],
            "cols": [],
            "rendererName": "Table",
            "aggregatorName": "Sum",
            "vals": ["Net Pay"],
        },
    },
    {
        "report_slug": "payroll_report_payslip",
        "name": "Payslip Status Overview",
        "config": {
            "rows": ["Status"],
            "cols": ["Department"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "recruitment_report_candidate",
        "name": "Recruitment Funnel",
        "config": {
            # The candidate pivot exposes this dimension as "Current Stage",
            # not "Stage" -- the prior value never matched any real field,
            # so this template silently produced an empty grouping.
            "rows": ["Current Stage"],
            "cols": ["Source"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "recruitment_report_candidate",
        "name": "Offer Letter Status",
        "config": {
            "rows": ["Offer Letter"],
            "cols": ["Recruitment"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "asset_report",
        "name": "Assets by Category",
        "config": {
            "rows": ["Category"],
            "cols": [],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "asset_report",
        "name": "Assets by Department",
        "config": {
            "rows": ["Department"],
            "cols": ["Status"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "pms_report_objective",
        "name": "Objectives by Department",
        "config": {
            "rows": ["Assignee Department"],
            "cols": [],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
    {
        "report_slug": "pms_report_objective",
        "name": "Objectives by Manager",
        "config": {
            "rows": ["Manager"],
            "cols": ["Assignee Department"],
            "rendererName": "Table",
            "aggregatorName": "Count",
        },
    },
]


def seed_standard_report_templates(dry_run: bool = False) -> tuple[int, int]:
    """
    Upsert SYSTEM_TEMPLATES as system ReportTemplate rows.

    Shared by the management command and the enterprise demo seeder
    (base/demo_data/runner.py) so a --flush demo reload doesn't wipe these
    out silently -- flush clears ReportTemplate along with everything else,
    and these aren't part of any load_data/*.json fixture. Returns
    (created, updated).
    """
    created = 0
    updated = 0
    for item in SYSTEM_TEMPLATES:
        existing = ReportTemplate.objects.filter(
            report_slug=item["report_slug"],
            name=item["name"],
            visibility=ReportTemplate.VISIBILITY_SYSTEM,
            created_by__isnull=True,
        ).first()
        if existing:
            if not dry_run:
                existing.config = item["config"]
                existing.is_standard = True
                existing.save(update_fields=["config", "is_standard"])
            updated += 1
        else:
            if not dry_run:
                ReportTemplate.objects.create(
                    report_slug=item["report_slug"],
                    name=item["name"],
                    config=item["config"],
                    visibility=ReportTemplate.VISIBILITY_SYSTEM,
                    is_standard=True,
                    created_by=None,
                )
            created += 1
    return created, updated


class Command(BaseCommand):
    help = "Seed system ReportTemplate layouts for standard enterprise reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created, updated = seed_standard_report_templates(dry_run=dry_run)

        msg = f"System templates — created: {created}, updated: {updated}"
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: {msg}"))
        else:
            self.stdout.write(self.style.SUCCESS(msg))
