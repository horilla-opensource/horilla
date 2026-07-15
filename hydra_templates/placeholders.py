import re
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class Placeholder:
    name: str
    label: str
    sample: str

    @property
    def token(self):
        return "{{" + self.name + "}}"


PLACEHOLDERS = (
    Placeholder("HYDRA_ID", "Immutable Hydra identifier", "HYD-0123456789ABCDEF"),
    Placeholder("PASSPORT_NAME", "Name exactly as in passport", "ANNA KOWALSKA"),
    Placeholder("FIRST_NAME", "First name", "Anna"),
    Placeholder("LAST_NAME", "Last name", "Kowalska"),
    Placeholder("DATE_OF_BIRTH", "Date of birth (YYYY-MM-DD)", "1992-04-05"),
    Placeholder("CITIZENSHIP", "Two-letter citizenship code", "UA"),
    Placeholder("PREFERRED_LANGUAGE", "Preferred language code", "uk"),
    Placeholder("PHONE", "Phone number", "+48123123123"),
    Placeholder("WHATSAPP_VIBER", "WhatsApp / Viber number", "+48123123123"),
    Placeholder("EMAIL", "Email address", "anna.kowalska@example.test"),
    Placeholder("LIFECYCLE_STATE", "Hydra lifecycle code", "employee"),
    Placeholder("COMPANY_NAME", "Legal company", "Citronex I Sp. z o.o."),
    Placeholder("LOCATION_NAME", "Current location", "Siechnice"),
    Placeholder("SECTION_NAME", "Current section / stage", "Packing"),
    Placeholder("TEAM_NAME", "Current team", "Team A"),
)
PLACEHOLDER_MAP = {placeholder.name: placeholder for placeholder in PLACEHOLDERS}
PLACEHOLDER_NAMES = tuple(PLACEHOLDER_MAP)

TOKEN_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_.-]{0,127})\s*}}")


def placeholder_names(source):
    """Return validated placeholder names in their first-use order."""

    source = source or ""
    names = [match.group(1) for match in TOKEN_RE.finditer(source)]
    remainder = TOKEN_RE.sub("", source)
    if "{" in remainder or "}" in remainder:
        raise ValidationError(
            _(
                "Malformed placeholder. Use {{NAME}} with an ASCII letter or "
                "underscore first and at most 128 identifier characters."
            ),
            code="malformed_placeholder",
        )
    unknown = sorted(set(names) - set(PLACEHOLDER_MAP))
    if unknown:
        raise ValidationError(
            _("Unknown placeholders: %(names)s") % {"names": ", ".join(unknown)},
            code="unknown_placeholder",
        )
    return tuple(dict.fromkeys(names))


def render_template_text(source, values):
    placeholder_names(source)

    def replace(match):
        return str(values.get(match.group(1), ""))

    return TOKEN_RE.sub(replace, source or "")


def sample_values():
    return {placeholder.name: placeholder.sample for placeholder in PLACEHOLDERS}
