from django.conf import settings
from django.core.checks import Error, Tags, register
from django.core.exceptions import ImproperlyConfigured

from hydra_shell.links import public_portal_url


@register(Tags.security)
def check_public_portal_url(app_configs, **kwargs):
    try:
        public_portal_url(base_url=settings.HYDRA_PORTAL_URL, language_code="en")
    except ImproperlyConfigured as error:
        return [
            Error(
                str(error),
                id="hydra_shell.E001",
                hint="Set HYDRA_PORTAL_URL to the audited public HTTPS portal root.",
            )
        ]
    return []
