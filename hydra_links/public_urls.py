import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from hydra_shell.links import PORTAL_LANGUAGE_CODES


ALLOWED_FIXED_QUERY_KEYS = {"v"}
PUBLIC_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def validate_public_hydra_url(value):
    try:
        parts = urlsplit((value or "").strip())
        port = parts.port
    except ValueError as error:
        raise ValidationError(_("Enter a valid public HTTPS URL.")) from error
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
        or port not in (None, 443)
    ):
        raise ValidationError(
            _(
                "Use an absolute public HTTPS URL without credentials, a custom port or fragment."
            )
        )
    query = parse_qsl(parts.query, keep_blank_values=True)
    if len(query) > 1 or any(key not in ALLOWED_FIXED_QUERY_KEYS for key, _ in query):
        raise ValidationError(
            _("Only the fixed public version parameter v is allowed in the stored URL.")
        )
    if query and not PUBLIC_VERSION_RE.fullmatch(query[0][1]):
        raise ValidationError(
            _("The public version parameter must contain 1-64 safe characters.")
        )


def public_hydra_url(*, base_url, language_code):
    validate_public_hydra_url(base_url)
    parts = urlsplit(base_url.strip())
    fixed_query = parse_qsl(parts.query, keep_blank_values=True)
    normalized_language = (language_code or "").lower().split("-", 1)[0]
    portal_language = PORTAL_LANGUAGE_CODES.get(normalized_language, "ru")
    query = fixed_query + [("lang", portal_language), ("from", "hydra")]
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path or "/",
            urlencode(query),
            "",
        )
    )


@dataclass(frozen=True)
class ResolvedPublicHydraLink:
    record: object
    url: str

    @property
    def label(self):
        return self.record.label

    @property
    def location(self):
        return self.record.location

    @property
    def kind_display(self):
        return self.record.get_kind_display()


def resolve_public_links(*, links, language_code):
    return [
        ResolvedPublicHydraLink(
            record=link,
            url=public_hydra_url(
                base_url=link.base_url,
                language_code=language_code,
            ),
        )
        for link in links
    ]
