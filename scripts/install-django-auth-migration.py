"""Install Hydra's pinned dynamic-User compatibility migration.

Hydra adds ``is_new_employee`` directly to Django's built-in User model, so
the migration autodetector places the migration in Django's package. Clean CI
runners need the reviewed migration installed before loading the migration
graph. The staging image performs the equivalent copy in its Dockerfile.
"""

import argparse
import os
import shutil
import tempfile
from importlib.metadata import version
from pathlib import Path


EXPECTED_DJANGO_VERSION = "4.2.24"
MIGRATION_NAME = "0013_user_is_new_employee.py"


def django_auth_migration_directory():
    import django.contrib.auth.migrations

    return Path(django.contrib.auth.migrations.__file__).resolve().parent


def install(source, target_directory):
    source = Path(source).resolve()
    target_directory = Path(target_directory).resolve()
    if not source.is_file():
        raise RuntimeError(f"Missing compatibility migration: {source}")
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / MIGRATION_NAME

    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{MIGRATION_NAME}.", dir=target_directory
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="deployment/django_auth_migrations/0013_user_is_new_employee.py",
    )
    parser.add_argument("--target-directory")
    arguments = parser.parse_args()

    installed_django = version("Django")
    if installed_django != EXPECTED_DJANGO_VERSION:
        raise SystemExit(
            f"Refusing compatibility migration install for Django {installed_django}; "
            f"expected {EXPECTED_DJANGO_VERSION}."
        )

    target_directory = (
        Path(arguments.target_directory)
        if arguments.target_directory
        else django_auth_migration_directory()
    )
    target = install(arguments.source, target_directory)
    print(target)


if __name__ == "__main__":
    main()
