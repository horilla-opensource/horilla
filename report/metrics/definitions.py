"""
Register all Phase-1 (and compliance) standard reports with the registry.
"""

from django.utils.translation import gettext_lazy as _

from report.registry import ReportDefinition, register

# Shared filter packs keyed to the underlying model family.
_EMPLOYEE = (
    "employment_status",
    "department_id",
    "job_position_id",
    "job_role_id",
    "employee_type_id",
    "work_type_id",
    "shift_id",
    "company_id",
    "location",
    "gender",
    "reporting_manager_id",
)
_ATTENDANCE = (
    "employment_status",
    "department_id",
    "job_position_id",
    "work_type_id",
    "shift_id",
    "company_id",
    "gender",
)
_LEAVE = (
    "employment_status",
    "department_id",
    "job_position_id",
    "company_id",
    "gender",
    "leave_type_id",
    "leave_status",
)
_LEAVE_BALANCE = (
    "employment_status",
    "department_id",
    "job_position_id",
    "company_id",
    "gender",
    "leave_type_id",
)
_PAYROLL = (
    "employment_status",
    "department_id",
    "job_position_id",
    "employee_type_id",
    "company_id",
    "gender",
    "payslip_status",
)
_CANDIDATE = (
    "department_id",
    "job_position_id",
    "company_id",
    "gender",
    "recruitment_id",
    "source",
    "offer_letter_status",
)
_ONBOARDING = (
    "company_id",
    "recruitment_id",
)
_PMS = (
    "employment_status",
    "department_id",
    "company_id",
    "gender",
    "reporting_manager_id",
)
_COMPLIANCE = (
    "employment_status",
    "department_id",
    "company_id",
)


def _load():
    from report.metrics import compliance, payroll, talent, time_leave, workforce

    # --- Workforce ---
    register(
        ReportDefinition(
            slug="workforce-composition",
            name=_("Workforce Composition"),
            domain="workforce",
            description=_(
                "Headcount, FTE proxy, and distribution by dept/type/job/location."
            ),
            permission="employee.view_employee",
            query_fn=workforce.workforce_composition,
            drilldown_fn=workforce.workforce_composition_drilldown,
            explorer_url_name="employee-report",
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_EMPLOYEE,
        )
    )
    register(
        ReportDefinition(
            slug="diversity-snapshot",
            name=_("Diversity Snapshot"),
            domain="workforce",
            description=_(
                "Gender, age bands, marital status, and leadership diversity."
            ),
            permission="employee.view_employee",
            query_fn=workforce.diversity_snapshot,
            explorer_url_name="employee-report",
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_EMPLOYEE,
        )
    )
    register(
        ReportDefinition(
            slug="tenure-longevity",
            name=_("Tenure & Longevity"),
            domain="workforce",
            description=_("Average tenure and tenure bands by department."),
            permission="employee.view_employee",
            query_fn=workforce.tenure_longevity,
            explorer_url_name="employee-report",
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_EMPLOYEE,
        )
    )
    register(
        ReportDefinition(
            slug="turnover-attrition",
            name=_("Turnover & Attrition"),
            domain="workforce",
            description=_(
                "Hires vs exits, turnover rate, and first-year attrition proxy."
            ),
            permission="employee.view_employee",
            query_fn=workforce.turnover_attrition,
            explorer_url_name="employee-report",
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_EMPLOYEE,
        )
    )
    register(
        ReportDefinition(
            slug="joiners-leavers",
            name=_("Joiners & Leavers"),
            domain="workforce",
            description=_("Period hires, exits, net change, and headcount trend."),
            permission="employee.view_employee",
            query_fn=workforce.joiners_leavers,
            explorer_url_name="employee-report",
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_EMPLOYEE,
        )
    )

    # --- Time & Leave ---
    register(
        ReportDefinition(
            slug="attendance-summary",
            name=_("Attendance Summary"),
            domain="time_leave",
            description=_(
                "Present days, late comes, overtime, and department breakdown."
            ),
            permission="attendance.view_attendance",
            query_fn=time_leave.attendance_summary,
            explorer_url_name="attendance-report",
            export_model="attendance.Attendance",
            required_apps=("attendance", "employee"),
            filter_fields=_ATTENDANCE,
        )
    )
    register(
        ReportDefinition(
            slug="absenteeism-rate",
            name=_("Absenteeism Rate"),
            domain="time_leave",
            description=_("Monthly absenteeism rate trend vs expected working days."),
            permission="attendance.view_attendance",
            query_fn=time_leave.absenteeism_rate,
            explorer_url_name="attendance-report",
            export_model="attendance.Attendance",
            required_apps=("attendance", "employee"),
            filter_fields=_ATTENDANCE,
        )
    )
    register(
        ReportDefinition(
            slug="overtime-analysis",
            name=_("Overtime Analysis"),
            domain="time_leave",
            description=_("OT hours by department and top employees."),
            permission="attendance.view_attendance",
            query_fn=time_leave.overtime_analysis,
            explorer_url_name="attendance-report",
            export_model="attendance.Attendance",
            required_apps=("attendance",),
            filter_fields=_ATTENDANCE,
        )
    )
    register(
        ReportDefinition(
            slug="leave-utilization",
            name=_("Leave Utilization"),
            domain="time_leave",
            description=_("Entitlement vs used vs remaining by leave type."),
            permission="leave.view_leaverequest",
            query_fn=time_leave.leave_utilization,
            explorer_url_name="leave-report",
            export_model="leave.LeaveRequest",
            required_apps=("leave",),
            filter_fields=_LEAVE,
        )
    )
    register(
        ReportDefinition(
            slug="leave-liability",
            name=_("Leave Liability"),
            domain="time_leave",
            description=_(
                "Open leave balances (available + carry forward) by type/dept."
            ),
            permission="leave.view_leaverequest",
            query_fn=time_leave.leave_liability,
            explorer_url_name="leave-report",
            export_model="leave.AvailableLeave",
            required_apps=("leave",),
            filter_fields=_LEAVE_BALANCE,
        )
    )

    # --- Payroll ---
    register(
        ReportDefinition(
            slug="labor-cost-summary",
            name=_("Labor Cost Summary"),
            domain="payroll",
            description=_("Gross, net, deductions, and cost by department."),
            permission="payroll.view_payslip",
            query_fn=payroll.labor_cost_summary,
            explorer_url_name="payroll-report",
            export_model="payroll.Payslip",
            required_apps=("payroll",),
            filter_fields=_PAYROLL,
        )
    )
    register(
        ReportDefinition(
            slug="cost-composition",
            name=_("Cost Composition"),
            domain="payroll",
            description=_("Allowance and deduction component mix from payslip heads."),
            permission="payroll.view_payslip",
            query_fn=payroll.cost_composition,
            explorer_url_name="payroll-report",
            export_model="payroll.Payslip",
            required_apps=("payroll",),
            filter_fields=_PAYROLL,
        )
    )
    register(
        ReportDefinition(
            slug="payroll-headcount-cost",
            name=_("Payroll Headcount Cost"),
            domain="payroll",
            description=_("Cost per FTE / average pay by department."),
            permission="payroll.view_payslip",
            query_fn=payroll.payroll_headcount_cost,
            explorer_url_name="payroll-report",
            export_model="payroll.Payslip",
            required_apps=("payroll", "employee"),
            filter_fields=_PAYROLL,
        )
    )
    register(
        ReportDefinition(
            slug="payslip-register",
            name=_("Payslip Register"),
            domain="payroll",
            description=_("Audit-friendly payslip register for the selected period."),
            permission="payroll.view_payslip",
            query_fn=payroll.payslip_register,
            drilldown_fn=payroll.payslip_register_drilldown,
            explorer_url_name="payroll-report",
            export_model="payroll.Payslip",
            required_apps=("payroll",),
            filter_fields=_PAYROLL,
        )
    )

    # --- Talent ---
    register(
        ReportDefinition(
            slug="recruitment-funnel",
            name=_("Recruitment Funnel"),
            domain="talent",
            description=_("Candidates by stage, conversion, and source mix."),
            permission="recruitment.view_recruitment",
            query_fn=talent.recruitment_funnel,
            drilldown_fn=talent.recruitment_funnel_drilldown,
            explorer_url_name="recruitment-report",
            export_model="recruitment.Candidate",
            required_apps=("recruitment",),
            filter_fields=_CANDIDATE,
        )
    )
    register(
        ReportDefinition(
            slug="time-to-hire",
            name=_("Time to Hire / Fill"),
            domain="talent",
            description=_("Average days to hire and open requisition aging."),
            permission="recruitment.view_recruitment",
            query_fn=talent.time_to_hire,
            explorer_url_name="recruitment-report",
            export_model="recruitment.Candidate",
            required_apps=("recruitment",),
            filter_fields=_CANDIDATE,
        )
    )
    register(
        ReportDefinition(
            slug="offer-acceptance",
            name=_("Offer & Acceptance"),
            domain="talent",
            description=_("Offer letter status mix and acceptance rate."),
            permission="recruitment.view_recruitment",
            query_fn=talent.offer_acceptance,
            explorer_url_name="recruitment-report",
            export_model="recruitment.Candidate",
            required_apps=("recruitment",),
            filter_fields=_CANDIDATE,
        )
    )
    register(
        ReportDefinition(
            slug="onboarding-progress",
            name=_("Onboarding Progress"),
            domain="talent",
            description=_("Onboarding stage distribution and task completion."),
            permission="recruitment.view_recruitment",
            query_fn=talent.onboarding_progress,
            explorer_url_name="recruitment-report",
            export_model="recruitment.Candidate",
            required_apps=("recruitment", "onboarding"),
            filter_fields=_ONBOARDING,
        )
    )
    register(
        ReportDefinition(
            slug="performance-distribution",
            name=_("Performance Distribution"),
            domain="talent",
            description=_("Objective, key-result, and feedback status mix."),
            permission="pms.view_objective",
            query_fn=talent.performance_distribution,
            explorer_url_name="pms-report",
            export_model="pms.EmployeeObjective",
            required_apps=("pms",),
            filter_fields=_PMS,
        )
    )

    # --- Compliance (Phase 2) ---
    register(
        ReportDefinition(
            slug="audit-activity",
            name=_("Audit Activity"),
            domain="compliance",
            description=_("Audit log volume by action and model."),
            permission="employee.view_employee",
            query_fn=compliance.audit_activity,
            export_model="employee.Employee",
            required_apps=(),
            filter_fields=("company_id",),
        )
    )
    register(
        ReportDefinition(
            slug="document-expiry",
            name=_("Document Expiry"),
            domain="compliance",
            description=_("Items expiring in the selected period."),
            permission="employee.view_employee",
            query_fn=compliance.document_expiry,
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_COMPLIANCE,
        )
    )

    # --- Phase 7 packs ---
    from report.metrics import packs

    register(
        ReportDefinition(
            slug="span-of-control",
            name=_("Span of Control"),
            domain="workforce",
            description=_(
                "Manager count, average span, and manager-to-headcount ratio."
            ),
            permission="employee.view_employee",
            query_fn=packs.span_of_control,
            explorer_url_name="employee-report",
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_EMPLOYEE,
        )
    )
    register(
        ReportDefinition(
            slug="pipeline-aging",
            name=_("Pipeline Aging"),
            domain="talent",
            description=_("How long open candidates sit in each stage."),
            permission="recruitment.view_recruitment",
            query_fn=packs.pipeline_aging,
            explorer_url_name="recruitment-report",
            export_model="recruitment.Candidate",
            required_apps=("recruitment",),
            filter_fields=_CANDIDATE,
        )
    )
    register(
        ReportDefinition(
            slug="source-quality",
            name=_("Source Quality"),
            domain="talent",
            description=_("Hire conversion rate by candidate source."),
            permission="recruitment.view_recruitment",
            query_fn=packs.source_quality,
            explorer_url_name="recruitment-report",
            export_model="recruitment.Candidate",
            required_apps=("recruitment",),
            filter_fields=_CANDIDATE,
        )
    )
    register(
        ReportDefinition(
            slug="document-expiry-aging",
            name=_("Document Expiry Aging"),
            domain="compliance",
            description=_(
                "Overdue and upcoming document expiry buckets (90-day horizon)."
            ),
            permission="employee.view_employee",
            query_fn=packs.document_expiry_aging,
            export_model="employee.Employee",
            required_apps=("employee",),
            filter_fields=_COMPLIANCE,
        )
    )
    register(
        ReportDefinition(
            slug="ot-concentration",
            name=_("OT Concentration"),
            domain="time_leave",
            description=_("Share of overtime concentrated in top employees."),
            permission="attendance.view_attendance",
            query_fn=packs.ot_concentration,
            explorer_url_name="attendance-report",
            export_model="attendance.Attendance",
            required_apps=("attendance", "employee"),
            filter_fields=_ATTENDANCE,
        )
    )


_load()
