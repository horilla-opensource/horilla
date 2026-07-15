from urllib.parse import urlencode, urlsplit, urlunsplit

from django.core.exceptions import ImproperlyConfigured


PORTAL_LANGUAGE_CODES = {
    "az": "az",
    "en": "en",
    "es": "es",
    "fil": "fil",
    "id": "id",
    "ne": "ne",
    "pl": "pl",
    "ru": "ru",
    "uk": "ua",
    "ua": "ua",
}


def public_portal_url(*, base_url: str, language_code: str) -> str:
    """Build a public-only portal URL without identity or assignment data."""

    parts = urlsplit(base_url.strip())
    if parts.scheme != "https" or not parts.netloc:
        raise ImproperlyConfigured("HYDRA_PORTAL_URL must be an absolute HTTPS URL.")

    normalized_language = (language_code or "").lower().split("-", 1)[0]
    portal_language = PORTAL_LANGUAGE_CODES.get(normalized_language, "ru")
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path or "/",
            urlencode({"lang": portal_language, "from": "hydra"}),
            "",
        )
    )
