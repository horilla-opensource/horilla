"""
base/sidebar.py

Settings menu registrations for the base app.

Sections registered:
  - General       : general settings, permissions, tags, mail
  - Base          : department, job position, job role, company
  - Theme Manager : color theme (only when horilla_theme is installed)
  - Integrations  : gdrive, linkedin, ldap, google meet, whatsapp
"""

from django.apps import apps
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.menu import settings_menu

# ---------------------------------------------------------------------------
# Accessibility functions
# ---------------------------------------------------------------------------


def system_preferences_accessibility(request, submenu, user_perms, *args, **kwargs):
    return any(
        request.user.has_perm(p)
        for p in [
            "base.change_announcementexpire",
            "base.view_dynamicpagination",
            "horilla_audit.view_accountblockunblock",
            "employee.change_employeegeneralsetting",
            "base.view_historytrackingfields",
            "payroll.view_payrollsettings",
            "base.view_company",
        ]
    )


def general_settings_accessibility(request, submenu, user_perms, *args, **kwargs):
    return system_preferences_accessibility(
        request, submenu, user_perms, *args, **kwargs
    )


def employee_permission_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("auth.view_permission")


def user_group_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("auth.view_group")


def date_settings_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_company")


def history_tags_accessibility(request, submenu, user_perms, *args, **kwargs):
    return any(
        request.user.has_perm(p)
        for p in [
            "base.view_tags",
            "employee.view_employeetag",
            "horilla_audit.view_audittag",
        ]
    )


def audit_tracking_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("horilla_audit.view_auditmodelconfig")


def audit_history_accessibility(request, submenu, user_perms, *args, **kwargs):
    return any(
        request.user.has_perm(p)
        for p in [
            "horilla_audit.view_audittag",
            "horilla_audit.view_auditmodelconfig",
        ]
    )


def mail_server_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_dynamicemailconfiguration"
    ) and not apps.is_installed("outlook_auth")


def mail_template_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_horillamailtemplate")


def mail_automation_accessibility(request, submenu, user_perms, *args, **kwargs):
    return apps.is_installed("horilla_automations") and request.user.has_perm(
        "horilla_automations.view_mailautomation"
    )


def outlook_mail_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm(
        "base.view_dynamicemailconfiguration"
    ) and apps.is_installed("outlook_auth")


def department_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_department")


def job_position_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_jobposition")


def job_role_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_jobrole")


def company_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_company")


def holidays_settings_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("base.view_holidays")


def company_leaves_settings_accessibility(
    request, submenu, user_perms, *args, **kwargs
):
    return request.user.has_perm("base.view_companyleaves")


def color_theme_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("horilla_theme.view_horillacolortheme")


def gdrive_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("horilla_backup.view_googledrivebackup")


def linkedin_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.has_perm("recruitment.view_linkedinaccount")


def ldap_accessibility(request, submenu, user_perms, *args, **kwargs):
    return apps.is_installed("horilla_ldap") and any(
        request.user.has_perm(p)
        for p in ["horilla_ldap.add_ldapsettings", "horilla_ldap.update_ldapsettings"]
    )


def google_meet_accessibility(request, submenu, user_perms, *args, **kwargs):
    return apps.is_installed("horilla_meet") and request.user.has_perm(
        "horilla_meet.view_googlecloudcredential"
    )


def whatsapp_accessibility(request, submenu, user_perms, *args, **kwargs):
    return apps.is_installed("whatsapp") and request.user.has_perm(
        "whatsapp.add_whatsappcredentials"
    )


# ---------------------------------------------------------------------------
# 1. General settings section
# ---------------------------------------------------------------------------


@settings_menu.register
class GeneralSettings:
    title = _("General")
    order = 1
    items = [
        {
            "label": _("System Preferences"),
            "url": reverse_lazy("system-preferences-view"),
            "accessibility": system_preferences_accessibility,
        },
        {
            "label": _("Employee Permission"),
            "url": reverse_lazy("employee-permission-assign"),
            "accessibility": employee_permission_accessibility,
        },
        {
            "label": _("Accessibility Restriction"),
            "url": reverse_lazy("user-accessibility"),
            "accessibility": employee_permission_accessibility,
        },
        {
            "label": _("User Group"),
            "url": reverse_lazy("user-group-view"),
            "accessibility": user_group_accessibility,
        },
        {
            "label": _("Audit & History"),
            "url": reverse_lazy("audit-history-view"),
            "accessibility": audit_history_accessibility,
        },
        {
            "label": _("Outlook Mail"),
            "url": reverse_lazy("outlook_view_records"),
            "accessibility": outlook_mail_accessibility,
        },
    ]


# ---------------------------------------------------------------------------
# 2. Organization section
# ---------------------------------------------------------------------------


@settings_menu.register
class BaseSettings:
    title = _("Organization")
    order = 2
    items = [
        {
            "label": _("Company"),
            "url": reverse_lazy("company-view"),
            "accessibility": company_accessibility,
        },
        {
            "label": _("Department"),
            "url": reverse_lazy("department-view"),
            "accessibility": department_accessibility,
        },
        {
            "label": _("Job Positions"),
            "url": reverse_lazy("job-position-view"),
            "accessibility": job_position_accessibility,
        },
        {
            "label": _("Job Role"),
            "url": reverse_lazy("job-role-view"),
            "accessibility": job_role_accessibility,
        },
        {
            "label": _("Weekly Off Days"),
            "url": reverse_lazy("company-leaves-view"),
            "accessibility": company_leaves_settings_accessibility,
        },
        {
            "label": _("Public Holidays"),
            "url": reverse_lazy("holidays-view"),
            "accessibility": holidays_settings_accessibility,
        },
    ]


# ---------------------------------------------------------------------------
# 3. Mail section
# ---------------------------------------------------------------------------


@settings_menu.register
class MailSettings:
    title = _("Mail")
    order = 3
    items = [
        {
            "label": _("Mail Server"),
            "url": reverse_lazy("mail-server-conf"),
            "accessibility": mail_server_accessibility,
        },
        {
            "label": _("Mail Template"),
            "url": reverse_lazy("mail-templates-view"),
            "accessibility": mail_template_accessibility,
        },
        {
            "label": _("Mail Automation"),
            "url": reverse_lazy("mail-automations-view"),
            "accessibility": mail_automation_accessibility,
        },
    ]


# ---------------------------------------------------------------------------
# 4. Theme Manager section (only when horilla_theme is installed)
# ---------------------------------------------------------------------------


@settings_menu.register
class ThemeManagerSettings:
    title = _("Theme Manager")
    order = 10
    condition = lambda self, request: apps.is_installed("horilla_theme")
    items = [
        {
            "label": _("Color Theme"),
            "url": reverse_lazy("horilla_theme:color_theme_view"),
            "accessibility": color_theme_accessibility,
        },
    ]


# ---------------------------------------------------------------------------
# 5. Integrations section
# ---------------------------------------------------------------------------


@settings_menu.register
class IntegrationsSettings:
    title = _("Integrations")
    order = 11
    items = [
        {
            "label": _("Gdrive Backup"),
            "url": reverse_lazy("gdrive"),
            "accessibility": gdrive_accessibility,
        },
        {
            "label": _("Linkedin"),
            "url": reverse_lazy("linkedin-integration-setting"),
            "accessibility": linkedin_accessibility,
        },
        {
            "label": _("LDAP"),
            "url": reverse_lazy("ldap-settings"),
            "accessibility": ldap_accessibility,
        },
        {
            "label": _("Google Meet"),
            "url": reverse_lazy("gmeet-setting"),
            "accessibility": google_meet_accessibility,
        },
        {
            "label": _("Whatsapp"),
            "url": reverse_lazy("whatsapp-credential-view"),
            "accessibility": whatsapp_accessibility,
        },
    ]
