"""
hydra_apps

This module is used to register horilla addons
"""

from hydra import settings
from hydra.settings import INSTALLED_APPS

INSTALLED_APPS.append("accessibility")
INSTALLED_APPS.append("horilla_audit")
INSTALLED_APPS.append("horilla_widgets")
INSTALLED_APPS.append("horilla_crumbs")
INSTALLED_APPS.append("horilla_documents")
INSTALLED_APPS.append("horilla_views")
INSTALLED_APPS.append("horilla_automations")
INSTALLED_APPS.append("auditlog")
INSTALLED_APPS.append("biometric")
INSTALLED_APPS.append("helpdesk")
INSTALLED_APPS.append("offboarding")
INSTALLED_APPS.append("horilla_backup")
INSTALLED_APPS.append("project")
INSTALLED_APPS.append("hydra_shell.apps.HydraShellConfig")
INSTALLED_APPS.append("hydra_people.apps.HydraPeopleConfig")
INSTALLED_APPS.append("hydra_coordination.apps.HydraCoordinationConfig")
INSTALLED_APPS.append("hydra_documents.apps.HydraDocumentsConfig")
INSTALLED_APPS.append("hydra_legalization.apps.HydraLegalizationConfig")
INSTALLED_APPS.append("hydra_imports.apps.HydraImportsConfig")
INSTALLED_APPS.append("hydra_arrivals.apps.HydraArrivalsConfig")
INSTALLED_APPS.append("hydra_housing.apps.HydraHousingConfig")
INSTALLED_APPS.append("hydra_tasks.apps.HydraTasksConfig")
INSTALLED_APPS.append("hydra_notifications.apps.HydraNotificationsConfig")
INSTALLED_APPS.append("hydra_onboarding.apps.HydraOnboardingConfig")
INSTALLED_APPS.append("hydra_templates.apps.HydraTemplatesConfig")
INSTALLED_APPS.append("hydra_links.apps.HydraLinksConfig")
INSTALLED_APPS.append("hydra_reports.apps.HydraReportsConfig")
INSTALLED_APPS.append("hydra_ops.apps.HydraOpsConfig")
if settings.env("AWS_ACCESS_KEY_ID", default=None) and "storages" not in INSTALLED_APPS:
    INSTALLED_APPS.append("storages")


AUDITLOG_INCLUDE_ALL_MODELS = True

AUDITLOG_EXCLUDE_TRACKING_MODELS = (
    # "<app_name>",
    # "<app_name>.<model>"
)

setattr(settings, "AUDITLOG_INCLUDE_ALL_MODELS", AUDITLOG_INCLUDE_ALL_MODELS)
setattr(settings, "AUDITLOG_EXCLUDE_TRACKING_MODELS", AUDITLOG_EXCLUDE_TRACKING_MODELS)

settings.MIDDLEWARE.append(
    "auditlog.middleware.AuditlogMiddleware",
)

SETTINGS_EMAIL_BACKEND = getattr(settings, "EMAIL_BACKEND", False)
setattr(settings, "EMAIL_BACKEND", "base.backends.ConfiguredEmailBackend")
if SETTINGS_EMAIL_BACKEND:
    setattr(settings, "EMAIL_BACKEND", SETTINGS_EMAIL_BACKEND)


SIDEBARS = [
    "hydra_people",
    "recruitment",
    "onboarding",
    "employee",
    "attendance",
    "leave",
    "payroll",
    "pms",
    "offboarding",
    "asset",
    "helpdesk",
    "project",
]

WHITE_LABELLING = False
NESTED_SUBORDINATE_VISIBILITY = False
TWO_FACTORS_AUTHENTICATION = False
