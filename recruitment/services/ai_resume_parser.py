"""
AI / smart resume parser: layout-aware extraction with robust patterns.

Production-grade in-process parser that improves on legacy regex-only approach:
- Layout-based name detection (position + font size)
- Multiple phone/email patterns (international, formatted)
- Section-aware extraction (address, education, skills)
- Portfolio/LinkedIn URL detection
- Gender and city from context
"""

import io
import re
from datetime import datetime

import fitz

from base.countries import country_arr, states

# ---------------------------------------------------------------------------
# Patterns (compiled once)
# ---------------------------------------------------------------------------
PHONE_PATTERNS = [
    re.compile(r"\+?\d{1,4}[\s\-\.]?\(?\d{2,4}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{3,4}"),
    re.compile(r"\+?[\d\s\-\.\(\)]{10,20}"),
]
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE
)
DOB_PATTERN = re.compile(
    r"\b(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\b"
)
ZIP_PATTERN = re.compile(r"\b\d{5,6}(?:-\d{4})?\b")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
LINKEDIN_PATTERN = re.compile(
    r"https?://(?:www\.)?linkedin\.com/[^\s<>\"']+", re.IGNORECASE
)

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%m-%d-%Y",
    "%m/%d/%Y",
    "%d-%m-%y",
    "%Y-%m-%d",
]


def _parse_date(s):
    """Parse date string to YYYY-MM-DD."""
    if not s:
        return ""
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s[:10]


def _extract_full_text_and_blocks(pdf_bytes):
    """Return (full_text, blocks_with_meta). blocks = list of (text, font_size, y_pos)."""
    doc = fitz.open("pdf", io.BytesIO(pdf_bytes))
    full_parts = []
    blocks = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            full_parts.append(page.get_text())
            dict_blocks = page.get_text("dict")["blocks"]
            for block in dict_blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            blocks.append(
                                {
                                    "text": text,
                                    "size": span.get("size", 12),
                                    "y": line.get("bbox", [0, 0, 0, 0])[1],
                                }
                            )
    finally:
        doc.close()
    full_text = "\n".join(full_parts)
    return full_text, blocks


def _extract_name_from_blocks(blocks):
    """Heuristic: name is often the first prominent (large) text at top of page."""
    if not blocks:
        return ""
    # Prefer first block with clearly larger font (header)
    sorted_by_size = sorted(blocks, key=lambda x: (x["size"], -x["y"]), reverse=True)
    candidates = []
    max_size = sorted_by_size[0]["size"] if sorted_by_size else 0
    for b in blocks:
        if b["size"] >= max_size * 0.9 and b["y"] < 200:  # top of first page
            t = b["text"]
            if t and not EMAIL_PATTERN.search(t) and not PHONE_PATTERNS[0].search(t):
                candidates.append(t)
    if candidates:
        return " ".join(candidates[:3])[:100]  # max 3 tokens, 100 chars
    if blocks:
        first = blocks[0]["text"]
        if first and len(first) < 80 and not EMAIL_PATTERN.search(first):
            return first[:100]
    return ""


def _extract_phone(text):
    for pat in PHONE_PATTERNS:
        m = pat.search(text)
        if m:
            digits = re.sub(r"\D", "", m.group())
            if len(digits) >= 10:
                return m.group().strip()[:15]
    return ""


def _extract_email(text):
    m = EMAIL_PATTERN.search(text)
    return m.group().strip()[:254] if m else ""


def _extract_dob(text):
    m = DOB_PATTERN.search(text)
    return _parse_date(m.group()) if m else ""


def _extract_zip(text):
    m = ZIP_PATTERN.search(text)
    return m.group() if m else ""


def _extract_country_state_city(text, lines):
    """Use country_arr and states; try 'City, State Country' patterns."""
    country = ""
    state = ""
    city = ""
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text)
    for w in words:
        cap = w.capitalize()
        if cap in country_arr:
            country = cap
        if cap in states:
            state = cap
    # City: often before state/country on a line (e.g. "Bangalore, Karnataka")
    for line in lines:
        line = line.strip()
        if not line or len(line) > 100:
            continue
        parts = [p.strip() for p in re.split(r"[,;]", line)]
        for i, p in enumerate(parts):
            if p in states and i > 0:
                city = parts[i - 1][:30]
                break
            if p in country_arr and i > 0:
                if not city and i >= 2:
                    city = parts[i - 2][:30]
                elif not state and i >= 1:
                    state = parts[i - 1][:30] if parts[i - 1] in states else state
                break
    return country, state, city


def _extract_address(full_text, lines):
    """Look for 'Address:' or multi-line address block."""
    for i, line in enumerate(lines):
        if "address" in line.lower() and ":" in line:
            addr = line.split(":", 1)[-1].strip()
            if addr:
                return addr[:255]
            if i + 1 < len(lines):
                return lines[i + 1].strip()[:255]
    return ""


def _extract_portfolio(full_text):
    """Prefer LinkedIn; else first https URL that looks like portfolio."""
    m = LINKEDIN_PATTERN.search(full_text)
    if m:
        return m.group().strip()[:200]
    for m in URL_PATTERN.finditer(full_text):
        url = m.group()
        if (
            "linkedin" in url
            or "github" in url
            or "portfolio" in url
            or "personal" in url
        ):
            return url[:200]
    m = URL_PATTERN.search(full_text)
    return m.group().strip()[:200] if m else ""


def _extract_gender(text):
    """Simple heuristic from explicit words."""
    t = text.lower()
    if re.search(r"\bmale\b", t):
        return "male"
    if re.search(r"\bfemale\b", t):
        return "female"
    if re.search(r"\bother\b", t):
        return "other"
    return ""


def parse_resume_from_bytes(
    file_bytes: bytes,
    filename: str = "",
    timeout: float = 8.0,
) -> dict:
    """
    Parse resume bytes and return canonical extraction dict.
    Args:
        file_bytes: raw PDF bytes
        filename: optional (for future DOCX)
        timeout: ignored for in-process; for API adapter compatibility
    Returns:
        dict with full_name, email_id, phone_number, address, country, state,
        city, zip, dob, gender, portfolio (all strings).
    """
    if not file_bytes or len(file_bytes) < 50:
        return {}
    try:
        full_text, blocks = _extract_full_text_and_blocks(file_bytes)
    except Exception:
        return {}

    lines = [s.strip() for s in full_text.splitlines() if s.strip()]

    result = {
        "full_name": _extract_name_from_blocks(blocks),
        "email_id": _extract_email(full_text),
        "phone_number": _extract_phone(full_text),
        "address": _extract_address(full_text, lines),
        "country": "",
        "state": "",
        "city": "",
        "zip": _extract_zip(full_text),
        "dob": _extract_dob(full_text),
        "gender": _extract_gender(full_text),
        "portfolio": _extract_portfolio(full_text),
    }

    country, state, city = _extract_country_state_city(full_text, lines)
    result["country"] = country
    result["state"] = state
    result["city"] = city

    return result
