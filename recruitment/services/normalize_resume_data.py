"""
Normalize extracted resume data to canonical schema for form fill.

- Country/state: map to values present in base.countries (dropdown compatibility)
- DOB: YYYY-MM-DD
- Phone/email: strip and truncate to model max lengths
"""

import re
from datetime import datetime

from base.countries import country_arr, states

# Common country aliases for normalization
COUNTRY_ALIASES = {
    "usa": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "u.s.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united states of america": "United States",
    "united kingdom of great britain": "United Kingdom",
}


def normalize_country(value):
    """Map country string to a value in country_arr, or return as-is if already valid."""
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()
    if not value:
        return ""
    v_lower = value.lower()
    if v_lower in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[v_lower]
    if value in country_arr:
        return value
    for c in country_arr:
        if c.lower() == v_lower:
            return c
    return value[:50]


def normalize_state(value):
    """Map state string to a value in states list if possible."""
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()[:50]
    if not value:
        return ""
    if value in states:
        return value
    v_lower = value.lower()
    for s in states:
        if s.lower() == v_lower:
            return s
    return value


def normalize_dob(value):
    """Ensure DOB is YYYY-MM-DD or empty."""
    if not value:
        return ""
    if isinstance(value, str):
        value = value.strip()
    else:
        value = str(value)
    if not value:
        return ""
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
    ]
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value[:10]


def normalize_phone(value):
    """Strip and limit length for mobile field (max 15)."""
    if not value:
        return ""
    s = re.sub(r"[\s\-\.\(\)]", "", str(value).strip())
    return s[:15] if s else ""


def normalize_email(value):
    """Strip and limit length for email (max 254)."""
    if not value:
        return ""
    return str(value).strip()[:254]


def normalize_resume_output(raw: dict) -> dict:
    """
    Normalize raw extraction (from AI or legacy) to canonical schema.
    Ensures keys expected by front end exist and values match dropdowns/format.
    """
    schema = {
        "full_name": "",
        "email_id": "",
        "phone_number": "",
        "address": "",
        "country": "",
        "state": "",
        "city": "",
        "zip": "",
        "dob": "",
        "gender": "",
        "portfolio": "",
    }
    for key in schema:
        if key in raw and raw[key]:
            val = raw[key]
            if key == "country":
                schema[key] = normalize_country(val)
            elif key == "state":
                schema[key] = normalize_state(val)
            elif key == "dob":
                schema[key] = normalize_dob(val)
            elif key == "phone_number":
                schema[key] = normalize_phone(val)
            elif key == "email_id":
                schema[key] = normalize_email(val)
            elif key == "full_name":
                schema[key] = str(val).strip()[:100]
            elif key == "address":
                schema[key] = str(val).strip()[:255]
            elif key in ("city", "zip"):
                schema[key] = str(val).strip()[:30]
            elif key == "gender":
                v = str(val).strip().lower()
                if v in ("male", "female", "other"):
                    schema[key] = v
            elif key == "portfolio":
                schema[key] = str(val).strip()[:200]
            else:
                schema[key] = str(val).strip()
    return schema
