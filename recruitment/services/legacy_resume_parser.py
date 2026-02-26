"""
Legacy resume parser using PyMuPDF and regex.

Used as fallback when AI parsing is disabled or fails.
Preserves original extraction behavior for backward compatibility.
"""

import io
import re
from datetime import datetime

import fitz

from base.countries import country_arr, states


def extract_text_with_font_info(pdf):
    """
    Extract text from PDF with font/size info for layout-based heuristics.
    Args:
        pdf: file-like object (e.g. BytesIO) with PDF bytes
    """
    if hasattr(pdf, "read"):
        pdf_bytes = pdf.read()
    else:
        pdf_bytes = pdf
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("utf-8")
    pdf_doc = io.BytesIO(pdf_bytes)
    doc = fitz.open("pdf", pdf_doc)
    text_info = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                try:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span.get("text", "")
                            size = span.get("size", 12)
                            length = len(text) or 1
                            capitalization = (
                                sum(1 for c in text if c.isupper()) / length
                            )
                            text_info.append(
                                {
                                    "text": text,
                                    "font_size": size,
                                    "capitalization": capitalization,
                                }
                            )
                except (KeyError, TypeError):
                    pass
    finally:
        doc.close()
    return text_info


def rank_text(text_info):
    """Rank text spans by font size and capitalization (for name heuristic)."""
    if not text_info:
        return []
    return sorted(
        text_info,
        key=lambda x: (x["font_size"], x["capitalization"]),
        reverse=True,
    )


def dob_matching(dob):
    """Normalize date string to YYYY-MM-DD."""
    if not dob or not isinstance(dob, str):
        return ""
    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y.%m.%d",
        "%d.%m.%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
    ]
    dob = dob.strip()
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(dob, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return dob


def extract_info(pdf):
    """
    Legacy extraction: contact info from PDF using layout + regex.
    Args:
        pdf: file-like object (e.g. BytesIO or UploadedFile) with PDF bytes
    Returns:
        dict with keys: full_name, email_id, phone_number, address,
        country, state, zip, dob (and optionally city, gender, portfolio as empty).
    """
    text_info = extract_text_with_font_info(pdf)
    ranked_text = rank_text(text_info)

    phone_pattern = re.compile(r"\b\+?[\d\s\-\.\(\)]{10,20}\b")  # relaxed for intl
    dob_pattern = re.compile(
        r"\b(?:\d{1,2}|\d{4})[-/.,]\d{1,2}[-/.,](?:\d{1,2}|\d{4})\b"
    )
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    zip_code_pattern = re.compile(r"\b\d{5,6}(?:-\d{4})?\b")

    extracted_info = {
        "full_name": "",
        "address": "",
        "country": "",
        "state": "",
        "city": "",
        "phone_number": "",
        "dob": "",
        "email_id": "",
        "zip": "",
        "gender": "",
        "portfolio": "",
    }

    if not ranked_text:
        return extracted_info

    # Name: largest font size (typical for resume headers)
    max_font = max(item["font_size"] for item in ranked_text)
    name_candidates = [
        item["text"].strip()
        for item in ranked_text
        if item["font_size"] == max_font and item["text"].strip()
    ]
    if name_candidates:
        extracted_info["full_name"] = " ".join(name_candidates)[:100]

    for item in ranked_text:
        text = item["text"]
        if not text:
            continue

        if not extracted_info["phone_number"]:
            phone_match = phone_pattern.search(text)
            if phone_match and sum(c.isdigit() for c in phone_match.group()) >= 10:
                extracted_info["phone_number"] = phone_match.group().strip()[:15]

        if not extracted_info["dob"]:
            dob_match = dob_pattern.search(text)
            if dob_match:
                extracted_info["dob"] = dob_matching(dob_match.group())

        if not extracted_info["zip"]:
            zip_match = zip_code_pattern.search(text)
            if zip_match:
                extracted_info["zip"] = zip_match.group()

        if not extracted_info["email_id"]:
            email_match = email_pattern.search(text)
            if email_match:
                extracted_info["email_id"] = email_match.group()

        if "address" in text.lower() and not extracted_info["address"]:
            extracted_info["address"] = (
                text.replace("Address:", "").replace("address:", "").strip()[:255]
            )

        for word in text.split():
            w = word.strip(".,;:")
            if w.capitalize() in country_arr:
                extracted_info["country"] = w.capitalize()
            if w.capitalize() in states:
                extracted_info["state"] = w.capitalize()

    return extracted_info


def extract_words_from_pdf(pdf_file):
    """
    Extract all words from PDF (for skill matching in matching_resumes).
    Args:
        pdf_file: Django FileField with .path (e.g. Resume.file)
    """
    if getattr(pdf_file, "path", None):
        pdf_document = fitz.open(pdf_file.path)
    else:
        data = pdf_file.read() if hasattr(pdf_file, "read") else pdf_file
        pdf_document = fitz.open("pdf", io.BytesIO(data))
    words = []
    try:
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text()
            page_words = re.findall(r"\b\w+\b", page_text.lower())
            words.extend(page_words)
    finally:
        pdf_document.close()
    return words
