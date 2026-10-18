"""Reading an uploaded sheet and matching its columns to a dataset's fields."""

import re
from difflib import get_close_matches

import numpy as np
import pandas as pd

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")
MAX_BYTES = 10 * 1024 * 1024


class UploadError(Exception):
    """The file cannot be read as a sheet; the message says why."""


def read_upload(file):
    """Any CSV or Excel sheet as a DataFrame of text-or-None, headers trimmed."""
    name = (getattr(file, "name", "") or "").lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise UploadError("Upload a CSV or Excel file (.csv, .xlsx, .xls).")
    if getattr(file, "size", 0) > MAX_BYTES:
        raise UploadError("The file is larger than 10 MB.")
    try:
        file.seek(0)
        # As text, so an account number 000123 or a phone 0123 keeps its leading zeros.
        reader = pd.read_csv if name.endswith(".csv") else pd.read_excel
        frame = reader(file, dtype=str)
    except Exception as exc:  # noqa: BLE001 - reported to the user
        raise UploadError(f"The file could not be read: {exc}") from exc
    frame = frame.dropna(how="all")
    frame.columns = [str(c).strip() for c in frame.columns]
    # A trailing unnamed column from a spreadsheet is noise, not data.
    frame = frame.loc[:, [not c.startswith("Unnamed:") for c in frame.columns]]
    if frame.empty or not len(frame.columns):
        raise UploadError("The file has no records.")
    return frame.astype(object).replace({np.nan: None})


def normalise(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def suggest_mapping(columns, fields):
    """{field key: column} for what can be matched by name; unmatched fields are ''."""
    by_norm = {normalise(c): c for c in columns}
    mapping, taken = {}, set()
    for spec in fields:
        names = [spec.key, spec.label, *spec.aliases]
        found = next(
            (by_norm[normalise(n)] for n in names if normalise(n) in by_norm), ""
        )
        if not found:
            close = get_close_matches(
                normalise(spec.key),
                [n for n in by_norm if by_norm[n] not in taken],
                n=1,
                cutoff=0.85,
            )
            found = by_norm[close[0]] if close else ""
        if found in taken:
            found = ""
        if found:
            taken.add(found)
        mapping[spec.key] = found
    return mapping


def apply_mapping(frame, mapping, fields):
    """Rows keyed by field, from the columns the mapping points at. Numbered from 2 like the sheet."""
    keys = [f.key for f in fields]
    rows = []
    for index, record in enumerate(frame.to_dict("records"), start=2):
        row = {"__row": index}
        for key in keys:
            column = mapping.get(key) or ""
            value = record.get(column) if column else None
            if isinstance(value, str):
                value = value.strip() or None
            row[key] = value
        rows.append(row)
    return rows


def sample_values(frame, column, count=3):
    if not column or column not in frame.columns:
        return []
    return [str(v) for v in frame[column].dropna().head(count).tolist()]
