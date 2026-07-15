import os
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


INSECURE_SECRET_MARKERS = ("django-insecure-", "change-me", "replace-me")
DEPLOYMENT_ENVIRONMENTS = {"staging", "production"}


@dataclass(frozen=True)
class ReadinessResult:
    name: str
    ok: bool
    detail: str

    def as_dict(self):
        return asdict(self)


def _result(name, ok, success, failure):
    return ReadinessResult(name=name, ok=bool(ok), detail=success if ok else failure)


def configuration_results():
    environment = getattr(settings, "HYDRA_ENVIRONMENT", "development")
    strict = environment in DEPLOYMENT_ENVIRONMENTS
    results = [
        _result(
            "environment",
            environment in {"development", "test", "staging", "production"},
            f"environment is {environment}",
            "HYDRA_ENVIRONMENT must be development, test, staging, or production",
        )
    ]
    if not strict:
        return results

    secret = settings.SECRET_KEY
    secret_ok = len(secret) >= 50 and not any(
        marker in secret.lower() for marker in INSECURE_SECRET_MARKERS
    )
    allowed_hosts = [host.strip() for host in settings.ALLOWED_HOSTS if host.strip()]
    csrf_origins = [origin.strip() for origin in settings.CSRF_TRUSTED_ORIGINS if origin.strip()]
    database_engine = settings.DATABASES["default"].get("ENGINE", "")
    portal = urlparse(getattr(settings, "HYDRA_PORTAL_URL", ""))
    results.extend(
        [
            _result("debug", not settings.DEBUG, "DEBUG is disabled", "DEBUG must be False"),
            _result(
                "secret_key",
                secret_ok,
                "SECRET_KEY passes the deployment policy",
                "SECRET_KEY is missing, short, or uses a known insecure marker",
            ),
            _result(
                "allowed_hosts",
                bool(allowed_hosts) and "*" not in allowed_hosts,
                "ALLOWED_HOSTS is explicit",
                "ALLOWED_HOSTS must be non-empty and must not contain '*'",
            ),
            _result(
                "csrf_origins",
                bool(csrf_origins)
                and all(urlparse(origin).scheme == "https" for origin in csrf_origins),
                "CSRF trusted origins use HTTPS",
                "CSRF_TRUSTED_ORIGINS must contain only explicit HTTPS origins",
            ),
            _result(
                "postgresql",
                database_engine in {
                    "django.db.backends.postgresql",
                    "django.db.backends.postgresql_psycopg2",
                },
                "PostgreSQL is configured",
                "staging and production require PostgreSQL",
            ),
            _result(
                "legacy_schedulers",
                getattr(settings, "HYDRA_DISABLE_SCHEDULERS", False),
                "legacy in-process schedulers are disabled",
                "HYDRA_DISABLE_SCHEDULERS must be enabled for multi-worker deployment",
            ),
            _result(
                "web_database_initialization",
                not getattr(settings, "HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION", True),
                "web database initialization is disabled",
                "HYDRA_ALLOW_WEB_DATABASE_INITIALIZATION must be disabled",
            ),
            _result(
                "deployment_revision",
                bool(getattr(settings, "HYDRA_DEPLOYMENT_REVISION", ""))
                and "replace" not in settings.HYDRA_DEPLOYMENT_REVISION.lower(),
                "deployment revision is recorded",
                "HYDRA_DEPLOYMENT_REVISION must identify the deployed build",
            ),
            _result(
                "portal_url",
                portal.scheme == "https" and bool(portal.netloc),
                "Hydra portal URL uses HTTPS",
                "HYDRA_PORTAL_URL must be an absolute HTTPS URL",
            ),
            _result(
                "ssl_redirect",
                getattr(settings, "SECURE_SSL_REDIRECT", False),
                "HTTPS redirect is enabled",
                "SECURE_SSL_REDIRECT must be enabled",
            ),
            _result(
                "secure_cookies",
                getattr(settings, "SESSION_COOKIE_SECURE", False)
                and getattr(settings, "CSRF_COOKIE_SECURE", False),
                "secure session and CSRF cookies are enabled",
                "secure session and CSRF cookies must be enabled",
            ),
            _result(
                "hsts",
                getattr(settings, "SECURE_HSTS_SECONDS", 0) > 0,
                "HSTS is enabled",
                "SECURE_HSTS_SECONDS must be greater than zero",
            ),
        ]
    )
    return results


def database_results(include_migrations=True):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            database_ok = cursor.fetchone() == (1,)
            role_is_superuser = False
            if getattr(settings, "HYDRA_ENVIRONMENT", "development") in DEPLOYMENT_ENVIRONMENTS:
                cursor.execute(
                    "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
                )
                role_row = cursor.fetchone()
                role_is_superuser = not role_row or bool(role_row[0])
    except Exception:
        return [
            ReadinessResult(
                "database", False, "database connection or query failed"
            )
        ]

    results = [
        _result("database", database_ok, "database query succeeded", "database query failed")
    ]
    if getattr(settings, "HYDRA_ENVIRONMENT", "development") in DEPLOYMENT_ENVIRONMENTS:
        results.append(
            _result(
                "database_role",
                not role_is_superuser,
                "application database role is not a superuser",
                "application database role must not be a PostgreSQL superuser",
            )
        )
    if include_migrations:
        try:
            executor = MigrationExecutor(connection)
            pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
            results.append(
                _result(
                    "migrations",
                    not pending,
                    "all known migrations are applied",
                    f"{len(pending)} migration step(s) are pending",
                )
            )
        except Exception:
            results.append(
                ReadinessResult("migrations", False, "migration state could not be read")
            )
    return results


def _paths_overlap(first, second):
    first = Path(first).resolve()
    second = Path(second).resolve()
    try:
        first.relative_to(second)
        return True
    except ValueError:
        pass
    try:
        second.relative_to(first)
        return True
    except ValueError:
        return False


def filesystem_results():
    media_root = Path(settings.MEDIA_ROOT)
    private_root = Path(settings.HYDRA_PRIVATE_MEDIA_ROOT)
    results = [
        _result(
            "storage_separation",
            not _paths_overlap(media_root, private_root),
            "public and private media roots are separated",
            "MEDIA_ROOT and HYDRA_PRIVATE_MEDIA_ROOT must not overlap",
        )
    ]
    for name, path in (("media_root", media_root), ("private_media_root", private_root)):
        ok = path.is_dir() and os.access(path, os.R_OK | os.W_OK)
        results.append(
            _result(
                name,
                ok,
                f"{name} exists and is readable/writable",
                f"{name} must exist and be readable/writable by the application identity",
            )
        )
    if getattr(settings, "HYDRA_READINESS_REQUIRE_STATIC", False):
        static_root = Path(settings.STATIC_ROOT)
        static_ok = static_root.is_dir() and any(static_root.iterdir())
        results.append(
            _result(
                "static_root",
                static_ok,
                "collected static files are present",
                "STATIC_ROOT must contain collected static files",
            )
        )
    return results


def collect_readiness(*, include_filesystem=True, include_migrations=True):
    results = configuration_results()
    results.extend(database_results(include_migrations=include_migrations))
    if include_filesystem:
        results.extend(filesystem_results())
    return results


def readiness_payload(results):
    return {
        "status": "ready" if all(result.ok for result in results) else "not_ready",
        "environment": getattr(settings, "HYDRA_ENVIRONMENT", "development"),
        "checks": [result.as_dict() for result in results],
    }
