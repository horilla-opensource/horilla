from django import template
from django.conf import settings
from django.utils.translation import get_language

from hydra_shell.links import public_portal_url


register = template.Library()

PEOPLE_URLS = {
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
    "hydra-legalization-attach-document",
    "hydra-legalization-create",
    "hydra-legalization-detail",
    "hydra-legalization-list",
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
