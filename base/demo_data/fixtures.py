"""Demo JSON files loaded by `load_demo_data` and the login-screen loader."""

from __future__ import annotations

from django.apps import apps

CORE_DEMO_FIXTURES = (
    "user_data.json",
    "employee_info_data.json",
    "base_data.json",
    "work_info_data.json",
    "mail_log_data.json",
)

OPTIONAL_DEMO_FIXTURES = (
    ("attendance", "attendance_data.json"),
    ("leave", "leave_data.json"),
    ("asset", "asset_data.json"),
    ("recruitment", "recruitment_data.json"),
    ("onboarding", "onboarding_data.json"),
    ("offboarding", "offboarding_data.json"),
    ("pms", "pms_data.json"),
    ("pms", "pms_scenarios_data.json"),
    ("payroll", "payroll_scenarios_data.json"),
    ("payroll", "payroll_data.json"),
    ("payroll", "payroll_loanaccount_data.json"),
    ("project", "project_data.json"),
    ("project", "project_scenarios_data.json"),
    ("helpdesk", "helpdesk_scenarios_data.json"),
)

# Mail Automation / Tags UIs — existing JSON, previously side-loaded only.
# faq.json is skipped (invalid JSON); helpdesk expansion already seeds FAQs.
SIDE_DEMO_FIXTURES = (
    (None, "tags.json"),
    (None, "mail_templates.json"),
    ("horilla_automations", "mail_automations.json"),
)


def demo_fixture_files() -> list[str]:
    files = list(CORE_DEMO_FIXTURES)
    files += [f for app, f in OPTIONAL_DEMO_FIXTURES if apps.is_installed(app)]
    files += [
        f for app, f in SIDE_DEMO_FIXTURES if app is None or apps.is_installed(app)
    ]
    return files
