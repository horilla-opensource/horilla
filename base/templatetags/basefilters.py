import json

from django import template
from django.core.paginator import Page, Paginator
from django.template.defaultfilters import register

from base.methods import get_pagination
from base.models import MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation
from horilla.menu.settings_menu import get_settings_menu

register = template.Library()


@register.filter
def equals(value, arg):
    """Check if value equals arg"""
    return value == arg


@register.simple_tag
def is_manager_of(user, instance, field_name="employee_id"):
    employee = Employee.objects.filter(employee_user_id=user).first()

    target_employee = getattr(instance, field_name, None)

    return EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee, employee_id=target_employee
    ).exists()


@register.filter(name="is_reportingmanager")
def is_reportingmanager(user):
    """

    This method will return true if the user employee profile is reporting manager to any employee
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    return EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee
    ).exists()


@register.filter(name="is_leave_approval_manager")
def is_leave_approval_manager(user):
    """
    This method will return true if the user is comes in MultipleApprovalCondition model as approving manager
    """
    employee = Employee.objects.filter(employee_user_id=user).first()
    manager = (
        MultipleApprovalManagers.objects.entire()
        .filter(employee_id=employee.id)
        .exists()
        if employee
        else False
    )
    return manager


@register.filter(name="check_manager")
def check_manager(user, instance):
    try:
        if isinstance(instance, Employee):
            return instance.employee_work_info.reporting_manager_id == user.employee_get
        return (
            user.employee_get
            == instance.employee_id.employee_work_info.reporting_manager_id
        )
    except:
        return False


@register.filter(name="filtersubordinates")
def filtersubordinates(user):
    """
    This method returns true if the user employee has corresponding related reporting manager object in EmployeeWorkInformation model
    args:
        user    : request.user
    """

    employee = user.employee_get
    employee_manages = employee.reporting_manager.all()
    return employee_manages.exists()


@register.filter(name="filter_field")
def filter_field(value):
    if value.endswith("_id"):
        value = value[:-3]
    if value.endswith("_ids"):
        value = value[:-4]
    splitted = value.split("__")

    return splitted[-1].replace("_", " ").capitalize()


@register.filter(name="user_perms")
def user_perms(perms):
    """
    permission names return method
    """
    return json.dumps(list(perms.values_list("codename", flat="True")))


@register.filter(name="abs_value")
def abs_value(value):
    """
    permission names return method
    """
    return abs(value)


@register.filter(name="startswith")
def startswith(value, arg):
    """Checks if the value starts with the provided argument."""
    return value.startswith(arg)


@register.filter(name="has_content")
def has_content(value):
    """Returns True if the input string has non-whitespace content."""
    if isinstance(value, str):
        return bool(value.strip())
    return True


@register.filter(name="readable")
def readable(value):
    try:
        value = value.replace("_", " ").replace("id", "").title()
    except:
        value = value
    return value


@register.simple_tag(takes_context=True)
def general_section_main(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("horilla_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsetting"),
            user.has_perm("base.view_historytrackingfields"),
            user.has_perm("payroll.view_payrollsettings"),
            user.has_perm("auth.view_permission"),
            user.has_perm("auth.view_group"),
            user.has_perm("base.view_company"),
            user.has_perm("base.view_tags"),
            user.has_perm("employee.view_employeetag"),
            user.has_perm("horilla_audit.view_audittag"),
            user.has_perm("base.view_dynamicemailconfiguration"),
            user.has_perm("horilla_backup.view_googledrivebackup"),
        ]
    )


@register.simple_tag(takes_context=True)
def general_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("horilla_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsetting"),
            user.has_perm("base.view_historytrackingfields"),
            user.has_perm("payroll.view_payrollsettings"),
        ]
    )


@register.simple_tag(takes_context=True)
def employee_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.view_worktype"),
            user.has_perm("base.view_rotatingworktype"),
            user.has_perm("base.view_employeeshift"),
            user.has_perm("base.view_rotatingshift"),
            user.has_perm("base.view_employeeshiftschedule"),
            user.has_perm("base.view_employeetype"),
            user.has_perm("employee.view_actiontype"),
            user.has_perm("employee.view_employeetag"),
        ]
    )


@register.simple_tag(takes_context=True)
def attendance_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("attendance.view_attendancevalidationcondition"),
            user.has_perm("base.view_biometricattendance"),
            user.has_perm("attendance.add_attendance"),
            user.has_perm("geofencing.add_geofencing"),
            user.has_perm("facedetection.add_facedetection"),
        ]
    )


@register.simple_tag(takes_context=True)
def show_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("attendance.view_attendancevalidationcondition"),
            user.has_perm("helpdesk.view_departmentmanager"),
            user.has_perm("helpdesk.view_tickettype"),
            user.has_perm("employee.view_employeetag"),
            user.has_perm("pms.add_bonuspointsetting"),
            user.has_perm("payroll.view_payslipautogenerate"),
            user.has_perm("leave.add_restrictleave"),
            user.has_perm("base.view_biometricattendance"),
            user.has_perm("attendance.add_attendance"),
            user.has_perm("geofencing.add_geofencing"),
            user.has_perm("facedetection.add_facedetection"),
            user.has_perm("recruitment.view_recruitment"),
            user.has_perm("recruitment.view_rejectreason"),
            user.has_perm("recruitment.add_recruitment"),
            user.has_perm("recruitment.add_linkedinaccount"),
            user.has_perm("horilla_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsetting"),
            user.has_perm("payroll.view_payrollsettings"),
            user.has_perm("auth.view_permission"),
            user.has_perm("auth.view_group"),
            user.has_perm("horilla_audit.view_audittag"),
            user.has_perm("horilla_backup.view_googledrivebackup"),
            user.has_perm("horilla_ldap.add_ldapsettings"),
            user.has_perm("horilla_ldap.update_ldapsettings"),
            user.has_perm("employee.view_actiontype"),
            user.has_perm("helpdesk.view_tag"),
            user.has_perm("whatsapp.view_whatsappcredentials"),
            user.has_perm("base.view_company"),
            user.has_perm("base.view_tags"),
            user.has_perm("base.view_dynamicemailconfiguration"),
            user.has_perm("base.view_department"),
            user.has_perm("base.view_jobposition"),
            user.has_perm("base.view_jobrole"),
            user.has_perm("base.view_worktype"),
            user.has_perm("base.view_rotatingworktype"),
            user.has_perm("base.view_employeeshift"),
            user.has_perm("base.view_rotatingshift"),
            user.has_perm("base.view_employeeshiftschedule"),
            user.has_perm("base.view_employeetype"),
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("horilla_backup.view_googledrivebackup"),
            user.has_perm("recruitment.view_linkedinaccount"),
            user.has_perm("horilla_ldap.add_ldapsettings"),
            user.has_perm("horilla_ldap.update_ldapsettings"),
            user.has_perm("horilla_meet.view_googlecloudcredential"),
            user.has_perm("whatsapp.add_whatsappcredentials"),
            user.has_perm("horilla_theme.view_horillacolortheme"),
        ]
    )


@register.simple_tag(takes_context=True)
def settings_menu(context):

    request = context.get("request")
    if request is None:
        return []
    return get_settings_menu(request)


@register.simple_tag
def settings_search_index():
    import json

    from django.urls import NoReverseMatch, reverse

    _RAW = [
        # General — System Preferences
        (
            "Default Expire Days",
            "Auto-expiry days for announcements",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Default Records Per Page",
            "Pagination count shown per page",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Badge ID Prefix",
            "Prefix added to employee badge IDs",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Currency Symbol",
            "Symbol shown for monetary values (e.g. $, €)",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Currency Position",
            "Whether currency symbol appears before or after the amount",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Date Format",
            "How dates are displayed across the system",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Time Format",
            "12-hour or 24-hour display format",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Restrict Login Account",
            "Allow admins to block or unblock employee login accounts",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "Restrict Profile Edit",
            "Prevent employees from editing their own profile details",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        (
            "History Tracking Fields",
            "Which work-information fields are tracked in audit history",
            "General",
            "System Preferences",
            "system-preferences-view",
        ),
        # General — User Groups
        (
            "User Group",
            "Create and manage Django permission groups",
            "General",
            "User Groups",
            "user-group-view",
        ),
        (
            "Group Permissions",
            "Assign permissions to a user group",
            "General",
            "User Groups",
            "user-group-view",
        ),
        # General — Accessibility
        (
            "Accessibility Restriction",
            "Control which user roles can see which menu items",
            "General",
            "Accessibility",
            "user-accessibility",
        ),
        # Organization — Company
        (
            "Company Name",
            "Legal name of the company",
            "Organization",
            "Company",
            "company-view",
        ),
        (
            "Company Address",
            "Street address of the company",
            "Organization",
            "Company",
            "company-view",
        ),
        (
            "Company Country",
            "Country where the company is registered",
            "Organization",
            "Company",
            "company-view",
        ),
        (
            "Company State",
            "State or province",
            "Organization",
            "Company",
            "company-view",
        ),
        (
            "Company City",
            "City of the company",
            "Organization",
            "Company",
            "company-view",
        ),
        (
            "Company Zip",
            "Postal or ZIP code",
            "Organization",
            "Company",
            "company-view",
        ),
        (
            "Company Icon",
            "Logo or icon for the company",
            "Organization",
            "Company",
            "company-view",
        ),
        # Organization — Department
        (
            "Department",
            "Name of the department",
            "Organization",
            "Department",
            "department-view",
        ),
        (
            "Department Manager",
            "Manager assigned to this department",
            "Organization",
            "Department",
            "department-view",
        ),
        # Organization — Job Position
        (
            "Job Position",
            "Name of the job position",
            "Organization",
            "Job Position",
            "job-position-view",
        ),
        # Organization — Job Role
        (
            "Job Role",
            "Name of the job role",
            "Organization",
            "Job Role",
            "job-role-view",
        ),
        # Organization — Weekly Off Days
        (
            "Weekly Off Days",
            "Configure recurring weekly off days for the company",
            "Organization",
            "Weekly Off Days",
            "company-leaves-view",
        ),
        (
            "Based On Week",
            "Which week of the month the off day applies",
            "Organization",
            "Weekly Off Days",
            "company-leaves-view",
        ),
        (
            "Based On Week Day",
            "Which day of the week is the off day",
            "Organization",
            "Weekly Off Days",
            "company-leaves-view",
        ),
        # Organization — Public Holidays
        (
            "Public Holiday",
            "Name of the public holiday",
            "Organization",
            "Public Holidays",
            "holidays-view",
        ),
        (
            "Holiday Start Date",
            "Start date of the public holiday",
            "Organization",
            "Public Holidays",
            "holidays-view",
        ),
        (
            "Holiday End Date",
            "End date of the public holiday",
            "Organization",
            "Public Holidays",
            "holidays-view",
        ),
        (
            "Recurring Holiday",
            "Whether this holiday repeats every year",
            "Organization",
            "Public Holidays",
            "holidays-view",
        ),
        # Mail — Mail Server
        (
            "Email Host",
            "SMTP server hostname",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Email Port",
            "SMTP server port number",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Default From Email",
            "Sender email address for outgoing mail",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Email Host Username",
            "Username for SMTP authentication",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Display Name",
            "Name shown in the From field of outgoing emails",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Email Authentication Password",
            "Password for SMTP authentication",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Use TLS",
            "Enable TLS encryption for SMTP",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Use SSL",
            "Enable SSL encryption for SMTP",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Fail Silently",
            "Suppress errors when email sending fails",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Primary Mail Server",
            "Mark this as the primary outgoing mail server",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "Email Send Timeout",
            "Timeout in seconds for SMTP connections",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        (
            "SMTP",
            "Configure SMTP mail server settings",
            "Mail",
            "Mail Server",
            "mail-server-conf",
        ),
        # Mail — Mail Template
        (
            "Mail Template",
            "Create reusable email body templates",
            "Mail",
            "Mail Template",
            "mail-templates-view",
        ),
        (
            "Template Title",
            "Name of the email template",
            "Mail",
            "Mail Template",
            "mail-templates-view",
        ),
        (
            "Template Body",
            "Rich-text body content of the email template",
            "Mail",
            "Mail Template",
            "mail-templates-view",
        ),
        # Mail — Mail Automation
        (
            "Mail Automation",
            "Trigger automated emails on model events",
            "Mail",
            "Mail Automation",
            "mail-automations-view",
        ),
        (
            "Automation Title",
            "Name of the mail automation rule",
            "Mail",
            "Mail Automation",
            "mail-automations-view",
        ),
        (
            "Trigger Condition",
            "When the automation fires: On Create, Update, or Delete",
            "Mail",
            "Mail Automation",
            "mail-automations-view",
        ),
        (
            "Delivery Channel",
            "Send via Email, Notification, or Both",
            "Mail",
            "Mail Automation",
            "mail-automations-view",
        ),
        # Approvals
        (
            "Multiple Approval",
            "Configure multi-level approval rules by condition",
            "Approvals",
            "Multiple Approval Rules",
            "multiple-approval-rules-view",
        ),
        (
            "Approval Condition Field",
            "Which field is evaluated for the approval condition",
            "Approvals",
            "Multiple Approval Rules",
            "multiple-approval-rules-view",
        ),
        (
            "Approval Condition Operator",
            "Comparison operator for the approval condition",
            "Approvals",
            "Multiple Approval Rules",
            "multiple-approval-rules-view",
        ),
        (
            "Approval Manager",
            "Who approves when the condition is met",
            "Approvals",
            "Multiple Approval Rules",
            "multiple-approval-rules-view",
        ),
        # Attendance — Attendance Rule
        (
            "Enable Check In / Check Out",
            "Employees use Check-In/Out button to record attendance",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "At-Work Tracker",
            "Show live at-work hours in the navbar",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "Track Late Come & Early Out",
            "Track late arrivals and early departures",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "IP Login Restriction",
            "Restrict attendance marking to specific IP addresses",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "Allowed IPs",
            "List of IP addresses permitted for attendance marking",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "Biometric Attendance",
            "Enable biometric devices for attendance marking",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "Face Detection",
            "Allow employees to mark attendance using face detection",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        (
            "Geofencing",
            "Restrict attendance marking to a geographic area",
            "Attendance",
            "Attendance Rule",
            "attendance-rule-view",
        ),
        # Attendance — Time Policies
        (
            "Worked Hours Auto Approve",
            "At-work hours threshold before attendance is not auto-validated",
            "Attendance",
            "Time Policies",
            "time-policies-view",
        ),
        (
            "Minimum Overtime to Approve",
            "Minimum overtime hours required for approval",
            "Attendance",
            "Time Policies",
            "time-policies-view",
        ),
        (
            "Maximum Overtime Per Day",
            "Cap on overtime hours per day",
            "Attendance",
            "Time Policies",
            "time-policies-view",
        ),
        (
            "Grace Time",
            "Buffer time allowed for late arrivals before marking as late",
            "Attendance",
            "Time Policies",
            "time-policies-view",
        ),
        (
            "Grace Time Allowed",
            "Duration of the grace period",
            "Attendance",
            "Time Policies",
            "time-policies-view",
        ),
        # Leave — Leave Rules
        (
            "Compensatory Leave",
            "Enable compensatory leave requests",
            "Leave",
            "Leave Rules",
            "leave-rules-view",
        ),
        (
            "Restrict Past Date Leave",
            "Only admins can create leave requests for past dates",
            "Leave",
            "Leave Rules",
            "leave-rules-view",
        ),
        # Leave — Restrict Leaves
        (
            "Restrict Leaves",
            "Create blackout periods when leave cannot be taken",
            "Leave",
            "Restrict Leaves",
            "restrict-leaves-view",
        ),
        (
            "Blackout Period Title",
            "Name of the leave restriction period",
            "Leave",
            "Restrict Leaves",
            "restrict-leaves-view",
        ),
        (
            "Blackout Start Date",
            "Start date of the leave restriction",
            "Leave",
            "Restrict Leaves",
            "restrict-leaves-view",
        ),
        (
            "Blackout End Date",
            "End date of the leave restriction",
            "Leave",
            "Restrict Leaves",
            "restrict-leaves-view",
        ),
        # Payroll — Auto Payslip
        (
            "Auto Generate Payslip",
            "Automatically generate payslips on a set day each month",
            "Payroll",
            "Auto Payslip Generation",
            "auto-payslip-settings-view",
        ),
        (
            "Payslip Generate Day",
            "Day of the month payslips are auto-generated",
            "Payroll",
            "Auto Payslip Generation",
            "auto-payslip-settings-view",
        ),
        # Payroll — Encashment
        (
            "Encashment",
            "Configure leave and bonus point encashment rules",
            "Payroll",
            "Encashment Settings",
            "encashment-settings-view",
        ),
        (
            "Bonus Unit",
            "Monetary value credited per bonus point redeemed",
            "Payroll",
            "Encashment Settings",
            "encashment-settings-view",
        ),
        (
            "Leave Unit Amount",
            "Monetary value credited per leave day encashed",
            "Payroll",
            "Encashment Settings",
            "encashment-settings-view",
        ),
        # Recruitment — Self Tracking
        (
            "Application Tracking",
            "Allow candidates to track their recruitment pipeline status",
            "Recruitment",
            "Candidate Self Tracking",
            "self-tracking-feature",
        ),
        (
            "Rating Visibility",
            "Allow candidates to view their recruitment rating",
            "Recruitment",
            "Candidate Self Tracking",
            "self-tracking-feature",
        ),
        # Recruitment — Reject Reasons
        (
            "Candidate Reject Reason",
            "Define reasons for rejecting a candidate",
            "Recruitment",
            "Reject Reasons",
            "candidate-reject-reasons",
        ),
        # Recruitment — Skills
        (
            "Skills",
            "Manage the list of skills available for candidates and employees",
            "Recruitment",
            "Skills",
            "skills-view",
        ),
        # Helpdesk — Department Managers
        (
            "Helpdesk Department Manager",
            "Assign managers responsible for helpdesk tickets per department",
            "Help Desk",
            "Department Managers",
            "department-manager-view",
        ),
        # Helpdesk — Ticket Type
        (
            "Ticket Type",
            "Define categories of helpdesk tickets",
            "Help Desk",
            "Ticket Type",
            "ticket-type-view",
        ),
        (
            "Ticket Prefix",
            "Short prefix used in ticket IDs",
            "Help Desk",
            "Ticket Type",
            "ticket-type-view",
        ),
        # Helpdesk — Tags
        (
            "Helpdesk Tag",
            "Create tags for classifying helpdesk tickets",
            "Help Desk",
            "Helpdesk Tags",
            "helpdesk-tag-view",
        ),
        # Offboarding
        (
            "Allow Resignation Request",
            "Allow employees to submit resignation requests themselves",
            "Offboarding",
            "Offboarding Rules",
            "offboarding-rules-view",
        ),
        (
            "Default Notice Period",
            "Default number of days between resignation and last working day",
            "Offboarding",
            "Offboarding Rules",
            "offboarding-rules-view",
        ),
        # Performance
        (
            "Bonus Point Setting",
            "Configure bonus points awarded for completing objectives, tasks, and projects",
            "Performance",
            "Bonus Point Setting",
            "bonus-point-setting",
        ),
        (
            "Bonus Points",
            "Points awarded for performance milestones",
            "Performance",
            "Bonus Point Setting",
            "bonus-point-setting",
        ),
    ]

    # Optional integrations — silently skip if the app or URL is not installed
    _OPTIONAL = [
        (
            "Google Drive Backup",
            "Back up the database and media files to Google Drive",
            "Integrations",
            "Google Drive Backup",
            "gdrive",
        ),
        (
            "OAuth Credentials File",
            "Google OAuth 2.0 credentials JSON file for Drive backup",
            "Integrations",
            "Google Drive Backup",
            "gdrive",
        ),
        (
            "Gdrive Folder ID",
            "Google Drive folder where backups are stored",
            "Integrations",
            "Google Drive Backup",
            "gdrive",
        ),
        (
            "Backup DB",
            "Include the database in the Google Drive backup",
            "Integrations",
            "Google Drive Backup",
            "gdrive",
        ),
        (
            "Backup Media",
            "Include media files in the Google Drive backup",
            "Integrations",
            "Google Drive Backup",
            "gdrive",
        ),
        (
            "LinkedIn Integration",
            "Connect LinkedIn for job posting and recruitment",
            "Integrations",
            "LinkedIn",
            "linkedin-integration-setting",
        ),
        (
            "LinkedIn API Token",
            "API token for LinkedIn integration",
            "Integrations",
            "LinkedIn",
            "linkedin-integration-setting",
        ),
        (
            "LDAP",
            "Connect to an LDAP directory for employee authentication",
            "Integrations",
            "LDAP",
            "ldap-settings",
        ),
        (
            "LDAP Server",
            "LDAP server address (e.g. ldap://127.0.0.1:389)",
            "Integrations",
            "LDAP",
            "ldap-settings",
        ),
        (
            "Bind DN",
            "LDAP bind distinguished name for authentication",
            "Integrations",
            "LDAP",
            "ldap-settings",
        ),
        (
            "Base DN",
            "LDAP base distinguished name for user search",
            "Integrations",
            "LDAP",
            "ldap-settings",
        ),
        (
            "Google Meet",
            "Configure Google Meet integration for interviews",
            "Integrations",
            "Google Meet",
            "gmeet-setting",
        ),
        (
            "Google Cloud Project ID",
            "Google Cloud project ID for Meet integration",
            "Integrations",
            "Google Meet",
            "gmeet-setting",
        ),
        (
            "Google Client ID",
            "OAuth client ID for Google Meet",
            "Integrations",
            "Google Meet",
            "gmeet-setting",
        ),
        (
            "Google Client Secret",
            "OAuth client secret for Google Meet",
            "Integrations",
            "Google Meet",
            "gmeet-setting",
        ),
        (
            "WhatsApp",
            "Configure WhatsApp Business API for notifications",
            "Integrations",
            "WhatsApp",
            "whatsapp-credential-view",
        ),
        (
            "Meta Token",
            "WhatsApp Business API access token",
            "Integrations",
            "WhatsApp",
            "whatsapp-credential-view",
        ),
        (
            "Meta Business ID",
            "WhatsApp Meta business account ID",
            "Integrations",
            "WhatsApp",
            "whatsapp-credential-view",
        ),
        (
            "Meta Phone Number",
            "WhatsApp business phone number",
            "Integrations",
            "WhatsApp",
            "whatsapp-credential-view",
        ),
        (
            "Webhook Token",
            "Token for verifying WhatsApp webhook callbacks",
            "Integrations",
            "WhatsApp",
            "whatsapp-credential-view",
        ),
        (
            "Color Theme",
            "Customise the UI colour palette",
            "Theme Manager",
            "Color Theme",
            "horilla_theme:color_theme_view",
        ),
    ]

    entries = []
    for text, description, section, page, url_name in _RAW + _OPTIONAL:
        try:
            url = reverse(url_name)
        except NoReverseMatch:
            continue
        entries.append(
            {
                "text": text,
                "description": description,
                "section": section,
                "page": page,
                "url": url,
            }
        )

    return json.dumps(entries, ensure_ascii=False)


@register.filter(name="config_perms")
def config_perms(user):
    from django.apps import apps

    app_permissions = {
        "leave": ["leave.view_restrictleave"],
        "base": [
            "base.add_holiday",
            "base.change_holiday",
            "base.add_companyleaves",
            "base.change_companyleaves",
            "base.add_horillamailtemplates",
            "base.view_horillamailtemplates",
        ],
    }
    for app, perms in app_permissions.items():
        if apps.is_installed(app):
            for perm in perms:
                if user.has_perm(perm):
                    return True
    return False
