"""Fail when the legacy brand appears outside reviewed compatibility rules."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = ROOT / "deployment" / "rebrand-allowlist.json"
LEGACY_BRAND = "hori" + "lla"
BRAND_PATTERN = re.compile(LEGACY_BRAND, re.IGNORECASE)


def tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    ]


def load_rules() -> list[tuple[re.Pattern[str], re.Pattern[str], str]]:
    raw_rules = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return [
        (
            re.compile(rule["path_pattern"]),
            re.compile(rule["line_pattern"]),
            rule["reason"],
        )
        for rule in raw_rules
    ]


def main() -> int:
    rules = load_rules()
    allowed = 0
    violations: list[str] = []

    for relative_path in tracked_files():
        path = ROOT / relative_path
        data = path.read_bytes()
        if LEGACY_BRAND.encode("ascii") not in data.lower():
            continue
        if b"\0" in data:
            violations.append(f"{relative_path}: binary file contains legacy brand")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            violations.append(f"{relative_path}: non-UTF-8 file contains legacy brand")
            continue

        normalized_path = relative_path.replace("\\", "/")
        for line_number, line in enumerate(text.splitlines(), start=1):
            matches = list(BRAND_PATTERN.finditer(line))
            if not matches:
                continue
            if any(
                path_pattern.search(normalized_path) and line_pattern.search(line)
                for path_pattern, line_pattern, _reason in rules
            ):
                allowed += len(matches)
            else:
                violations.append(
                    f"{normalized_path}:{line_number}: unapproved legacy-brand occurrence"
                )

    if violations:
        print("Rebrand verification failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print(f"Verified rebrand allowlist: {allowed} approved occurrence(s), 0 violations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
