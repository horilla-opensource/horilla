"""Deterministic, privacy-minimising Person identity match helpers."""

from __future__ import annotations

from hashlib import sha256
import re
import unicodedata

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


MATCH_REASON_LABELS = {
    "identity_exact": "Same normalized name, date of birth and citizenship",
    "passport_dob": "Same normalized passport name and date of birth",
    "email_exact": "Same normalized email address",
    "phone_exact": "Same normalized phone or messenger number",
}

MATCH_REASON_WEIGHTS = {
    "identity_exact": 100,
    "passport_dob": 90,
    "email_exact": 65,
    "phone_exact": 60,
}


def normalize_identity_text(value) -> str:
    """Normalize comparison text without transliteration or fuzzy matching."""

    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(normalized.casefold().split())


def normalize_email(value) -> str:
    return normalize_identity_text(value)


def normalize_phone(value) -> str:
    return "".join(re.findall(r"\d", unicodedata.normalize("NFKC", str(value or ""))))


def _digest(parts) -> str:
    normalized = "\x1f".join(str(part) for part in parts)
    if not normalized.strip("\x1f"):
        return ""
    return sha256(normalized.encode("utf-8")).hexdigest()


def person_fingerprints(person) -> dict[str, str]:
    dob = person.date_of_birth.isoformat() if person.date_of_birth else ""
    first_name = normalize_identity_text(person.first_name)
    last_name = normalize_identity_text(person.last_name)
    citizenship = normalize_identity_text(person.citizenship)
    passport_name = normalize_identity_text(person.passport_name)
    email = normalize_email(person.email)
    phone = normalize_phone(person.phone)
    messenger = normalize_phone(person.whatsapp_viber)
    return {
        "identity_fingerprint": _digest((first_name, last_name, dob, citizenship)),
        "passport_dob_fingerprint": _digest((passport_name, dob)),
        "email_fingerprint": _digest((email,)) if email else "",
        "phone_fingerprint": _digest((phone,)) if phone else "",
        "messenger_fingerprint": _digest((messenger,)) if messenger else "",
    }


def populate_person_fingerprints(person) -> None:
    for field_name, value in person_fingerprints(person).items():
        setattr(person, field_name, value)


def ensure_canonical_person(person) -> None:
    if person.merged_into_id:
        raise ValidationError(
            {"person": _("Use the canonical Person; this identifier is a merged alias.")}
        )


def duplicate_match_reasons(person_a, person_b) -> tuple[str, ...]:
    """Return deterministic reason codes after verifying raw normalized values.

    Fingerprints select possible matches efficiently. Comparing normalized source
    values again makes a theoretical SHA-256 collision a false suggestion rather
    than an incorrect match.
    """

    reasons: list[str] = []
    a_dob = person_a.date_of_birth
    b_dob = person_b.date_of_birth
    if (
        a_dob
        and a_dob == b_dob
        and normalize_identity_text(person_a.first_name)
        == normalize_identity_text(person_b.first_name)
        and normalize_identity_text(person_a.last_name)
        == normalize_identity_text(person_b.last_name)
        and normalize_identity_text(person_a.citizenship)
        == normalize_identity_text(person_b.citizenship)
    ):
        reasons.append("identity_exact")
    if (
        a_dob
        and a_dob == b_dob
        and normalize_identity_text(person_a.passport_name)
        == normalize_identity_text(person_b.passport_name)
    ):
        reasons.append("passport_dob")
    email_a = normalize_email(person_a.email)
    email_b = normalize_email(person_b.email)
    if email_a and email_a == email_b:
        reasons.append("email_exact")
    phones_a = {
        value
        for value in (
            normalize_phone(person_a.phone),
            normalize_phone(person_a.whatsapp_viber),
        )
        if value
    }
    phones_b = {
        value
        for value in (
            normalize_phone(person_b.phone),
            normalize_phone(person_b.whatsapp_viber),
        )
        if value
    }
    if phones_a.intersection(phones_b):
        reasons.append("phone_exact")
    return tuple(reasons)


def duplicate_match_score(reasons) -> int:
    weights = sorted(
        (MATCH_REASON_WEIGHTS[reason] for reason in reasons),
        reverse=True,
    )
    if not weights:
        return 0
    return min(100, weights[0] + 5 * (len(weights) - 1))
