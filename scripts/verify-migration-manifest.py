"""Verify the exact reviewed first-party Django migration source set."""

import argparse
import hashlib
import re
import sys
from pathlib import Path, PurePosixPath


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "deployment" / "migration-manifest.sha256"
MIGRATION_NAME = re.compile(r"^[0-9][A-Za-z0-9_]*\.py$")
MANIFEST_LINE = re.compile(
    r"^(?P<digest>[0-9a-f]{64})  (?P<path>[A-Za-z0-9_./-]+)$"
)
IGNORED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "site-packages",
    "staticfiles",
    "venv",
}


class ManifestError(RuntimeError):
    pass


def normalized_sha256(path):
    content = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def is_reviewed_migration_path(relative):
    relative = PurePosixPath(relative)
    if any(part in IGNORED_PARTS for part in relative.parts):
        return False
    if not MIGRATION_NAME.fullmatch(relative.name):
        return False
    return (
        relative.parent.name == "migrations"
        or relative.parent.as_posix() == "deployment/django_auth_migrations"
    )


def discover_migrations(root=REPOSITORY_ROOT):
    root = Path(root).resolve()
    entries = {}
    for path in root.rglob("*.py"):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if is_reviewed_migration_path(relative):
            entries[relative.as_posix()] = normalized_sha256(path)
    return dict(sorted(entries.items()))


def load_manifest(path=MANIFEST_PATH):
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"Missing migration manifest: {path}")
    entries = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="ascii").splitlines(), start=1
    ):
        match = MANIFEST_LINE.fullmatch(raw_line)
        if not match:
            raise ManifestError(
                f"Invalid migration manifest line {line_number}."
            )
        relative = PurePosixPath(match.group("path"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ManifestError(
                f"Unsafe migration manifest path on line {line_number}."
            )
        name = relative.as_posix()
        if not is_reviewed_migration_path(relative):
            raise ManifestError(
                f"Unsupported migration manifest path on line {line_number}: {name}"
            )
        if name in entries:
            raise ManifestError(f"Duplicate migration manifest path: {name}")
        entries[name] = match.group("digest")
    if not entries:
        raise ManifestError("Migration manifest is empty.")
    return entries


def comparison_errors(manifest_entries, current_entries):
    errors = []
    manifest_paths = set(manifest_entries)
    current_paths = set(current_entries)
    for name in sorted(manifest_paths - current_paths):
        errors.append(f"reviewed migration is missing: {name}")
    for name in sorted(current_paths - manifest_paths):
        errors.append(f"migration is absent from the reviewed manifest: {name}")
    for name in sorted(manifest_paths & current_paths):
        if manifest_entries[name] != current_entries[name]:
            errors.append(f"reviewed migration content changed: {name}")
    return errors


def render_entries(entries):
    return "\n".join(f"{digest}  {name}" for name, digest in entries.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--print-current",
        action="store_true",
        help="Print the normalized current manifest without writing files.",
    )
    arguments = parser.parse_args()

    current_entries = discover_migrations()
    if arguments.print_current:
        print(render_entries(current_entries))
        return 0

    try:
        manifest_entries = load_manifest()
    except ManifestError as error:
        print(error, file=sys.stderr)
        return 1

    errors = comparison_errors(manifest_entries, current_entries)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(
            "Review the migration change, then regenerate with "
            "--print-current and update deployment/migration-manifest.sha256.",
            file=sys.stderr,
        )
        return 1

    print(f"Verified {len(current_entries)} reviewed migration source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
