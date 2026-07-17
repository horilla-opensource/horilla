from django import template
from django.conf import settings
from django.utils.translation import get_language

from hydra_shell.links import public_portal_url


register = template.Library()

PEOPLE_URLS = {
    "hydra-duplicate-commit",
    "hydra-duplicate-detail",
    "hydra-duplicate-dismiss",
    "hydra-duplicate-list",
    "hydra-duplicate-preview",
    "hydra-person-candidate-link",
    "hydra-person-create",
    "hydra-person-detail",
    "hydra-person-employee-conversion",
    "hydra-person-list",
    "hydra-person-update",
}
ORGANIZATION_URLS = {
    "hydra-location-create",
    "hydra-organization",
    "hydra-person-assign",
    "hydra-scope-grant-create",
    "hydra-section-create",
    "hydra-team-create",
}
LEGALIZATION_URLS = {
    "hydra-legalization-authority-create",
    "hydra-legalization-authority-update",
    "hydra-legalization-attach-document",
    "hydra-legalization-configuration",
    "hydra-legalization-create",
    "hydra-legalization-detail",
    "hydra-legalization-list",
    "hydra-legalization-procedure-create",
    "hydra-legalization-procedure-update",
    "hydra-legalization-requirement-create",
    "hydra-legalization-requirement-update",
    "hydra-legalization-transition",
    "hydra-legalization-update",
}
RECRUITMENT_URLS = {
    "hydra-candidate-import",
    "hydra-candidate-import-apply",
    "hydra-candidate-import-detail",
    "hydra-candidate-import-template",
    "hydra-candidate-documents",
    "hydra-private-document-download",
    "hydra-private-document-type-create",
    "hydra-private-document-type-list",
    "hydra-private-document-type-update",
    "hydra-recruitment-create",
    "hydra-recruitment-detail",
    "hydra-recruitment-link-person",
    "hydra-recruitment-list",
}
ARRIVAL_URLS = {
    "hydra-arrival-create",
    "hydra-arrival-detail",
    "hydra-arrival-list",
    "hydra-arrival-transition",
    "hydra-arrival-update",
}
HOUSING_URLS = {
    "hydra-housing-assign",
    "hydra-housing-assignment-end",
    "hydra-housing-assignment-move",
    "hydra-housing-bed-create",
    "hydra-housing-building-create",
    "hydra-housing-dashboard",
    "hydra-housing-facility-create",
    "hydra-housing-facility-detail",
    "hydra-housing-floor-create",
    "hydra-housing-reservation-cancel",
    "hydra-housing-reservation-confirm",
    "hydra-housing-reservation-renew",
    "hydra-housing-room-create",
}
TASK_URLS = {
    "hydra-task-create",
    "hydra-task-detail",
    "hydra-task-list",
    "hydra-task-reassign",
    "hydra-task-transition",
    "hydra-task-update",
}
NOTIFICATION_URLS = {
    "hydra-notification-archive",
    "hydra-notification-center",
    "hydra-notification-open",
    "hydra-notification-preferences",
    "hydra-notification-read",
    "hydra-notification-read-all",
    "hydra-notification-restore",
    "hydra-notification-unread",
}
ONBOARDING_CONTENT_URLS = {
    "hydra-onboarding-assignment-confirm",
    "hydra-onboarding-assignment-detail",
    "hydra-onboarding-assignment-quiz",
    "hydra-onboarding-assignment-start",
    "hydra-onboarding-course-create",
    "hydra-onboarding-course-detail",
    "hydra-onboarding-dashboard",
    "hydra-onboarding-lesson-create",
    "hydra-onboarding-option-create",
    "hydra-onboarding-person-apply-rules",
    "hydra-onboarding-person-assign",
    "hydra-onboarding-question-create",
    "hydra-onboarding-quiz-create",
    "hydra-onboarding-rule-create",
    "hydra-onboarding-version-create",
    "hydra-onboarding-version-detail",
    "hydra-onboarding-version-publish",
}
BRIGADIER_URLS = {"hydra-brigadier-panel"}
COORDINATOR_URLS = {"hydra-coordinator-panel"}
TEMPLATE_URLS = {
    "hydra-template-create",
    "hydra-template-data-export",
    "hydra-template-list",
    "hydra-template-update",
}
PUBLIC_LINK_URLS = {
    "hydra-public-link-create",
    "hydra-public-link-list",
    "hydra-public-link-update",
}
REPORT_URLS = {
    "hydra-operational-report",
    "hydra-operational-report-export",
}


@register.simple_tag(takes_context=True)
def hydra_nav_is_active(context, module):
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", "")
    if module == "people":
        return url_name in PEOPLE_URLS
    if module == "organization":
        return url_name in ORGANIZATION_URLS
    if module == "legalization":
        return url_name in LEGALIZATION_URLS
    if module == "recruitment":
        return url_name in RECRUITMENT_URLS
    if module == "arrivals":
        return url_name in ARRIVAL_URLS
    if module == "housing":
        return url_name in HOUSING_URLS
    if module == "tasks":
        return url_name in TASK_URLS
    if module == "notifications":
        return url_name in NOTIFICATION_URLS
    if module == "onboarding_content":
        return url_name in ONBOARDING_CONTENT_URLS
    if module == "brigadier":
        return url_name in BRIGADIER_URLS
    if module == "coordinator":
        return url_name in COORDINATOR_URLS
    if module == "templates":
        return url_name in TEMPLATE_URLS
    if module == "public_links":
        return url_name in PUBLIC_LINK_URLS
    if module == "reports":
        return url_name in REPORT_URLS
    return False


@register.simple_tag
def hydra_public_portal_url():
    return public_portal_url(
        base_url=settings.HYDRA_PORTAL_URL,
        language_code=get_language() or "ru",
    )
