import os
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Count, F, Max
from django.utils import timezone


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
    onboarding_portal = urlparse(
        getattr(settings, "HYDRA_ONBOARDING_PORTAL_BASE_URL", "")
    )
    notification_base = urlparse(
        getattr(settings, "HYDRA_NOTIFICATION_BASE_URL", "")
    )
    public_media_root = Path(settings.MEDIA_ROOT).resolve()
    portal_email_root = Path(
        getattr(settings, "HYDRA_PORTAL_EMAIL_MEDIA_ROOT", "")
    ).resolve()
    email_host = getattr(settings, "EMAIL_HOST", "").strip()
    email_user = getattr(settings, "EMAIL_HOST_USER", "").strip()
    email_password = getattr(settings, "EMAIL_HOST_PASSWORD", "")
    default_from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "").strip()
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
                "onboarding_portal_url",
                onboarding_portal.scheme == "https" and bool(onboarding_portal.netloc),
                "onboarding portal URL uses HTTPS",
                "HYDRA_ONBOARDING_PORTAL_BASE_URL must be an absolute HTTPS URL",
            ),
            _result(
                "notification_base_url",
                notification_base.scheme == "https" and bool(notification_base.netloc),
                "notification email sign-in URL uses HTTPS",
                "HYDRA_NOTIFICATION_BASE_URL must be an absolute HTTPS URL",
            ),
            _result(
                "portal_email_storage",
                bool(str(portal_email_root))
                and portal_email_root != public_media_root
                and public_media_root not in portal_email_root.parents,
                "portal email payload storage is outside public media",
                "HYDRA_PORTAL_EMAIL_MEDIA_ROOT must be outside MEDIA_ROOT",
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
            _result(
                "document_scanner",
                getattr(settings, "HYDRA_DOCUMENT_SCANNER", "").lower() == "clamd",
                "ClamAV malware scanning is configured",
                "HYDRA_DOCUMENT_SCANNER must be set to clamd",
            ),
            _result(
                "document_retention",
                getattr(settings, "HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS", 0) > 0,
                "private-document retention is configured",
                "HYDRA_PRIVATE_DOCUMENT_RETENTION_DAYS must be greater than zero",
            ),
            _result(
                "candidate_import_retention",
                1
                <= getattr(settings, "HYDRA_IMPORT_APPLIED_RETENTION_HOURS", 0)
                <= getattr(settings, "HYDRA_IMPORT_PREVIEW_RETENTION_HOURS", 0)
                <= 720,
                "candidate import source-data retention is bounded",
                "candidate import retention must be 1 to 720 hours and applied retention cannot exceed preview retention",
            ),
            _result(
                "quarantine_retention",
                getattr(settings, "HYDRA_DOCUMENT_QUARANTINE_HOURS", 0) > 0,
                "document quarantine retention is configured",
                "HYDRA_DOCUMENT_QUARANTINE_HOURS must be greater than zero",
            ),
            _result(
                "notification_retry_limit",
                getattr(settings, "HYDRA_NOTIFICATION_MAX_ATTEMPTS", 0) > 0,
                "notification retry limit is configured",
                "HYDRA_NOTIFICATION_MAX_ATTEMPTS must be greater than zero",
            ),
            _result(
                "notification_email_policy",
                5
                <= getattr(settings, "HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS", 0)
                <= getattr(settings, "HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS", 0)
                <= 86400
                and getattr(settings, "HYDRA_NOTIFICATION_EMAIL_LEASE_SECONDS", 0)
                >= 2 * getattr(settings, "EMAIL_TIMEOUT", 0),
                "internal notification email retry and lease policy is bounded",
                "notification email retry or lease settings are invalid",
            ),
            _result(
                "portal_email_policy",
                1 <= getattr(settings, "EMAIL_TIMEOUT", 0) <= 120
                and 1 <= getattr(settings, "HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS", 0) <= 50
                and 5
                <= getattr(settings, "HYDRA_PORTAL_EMAIL_RETRY_BASE_SECONDS", 0)
                <= getattr(settings, "HYDRA_PORTAL_EMAIL_RETRY_MAX_SECONDS", 0)
                <= 86400
                and getattr(settings, "HYDRA_PORTAL_EMAIL_LEASE_SECONDS", 0)
                >= 2 * getattr(settings, "EMAIL_TIMEOUT", 0)
                and 1
                <= getattr(settings, "HYDRA_PORTAL_EMAIL_DEAD_RETENTION_HOURS", 0)
                <= 720
                and 1
                <= getattr(settings, "HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS", 0)
                <= 20
                and 1
                <= getattr(settings, "HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES", 0)
                <= 25 * 1024 * 1024
                and getattr(settings, "HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES", 0)
                >= getattr(settings, "HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES", 0)
                and getattr(settings, "HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES", 0)
                <= 100 * 1024 * 1024,
                "portal email delivery policy is bounded",
                "portal email timeout, retry, lease, retention, or attachment limits are invalid",
            ),
            _result(
                "smtp_configuration",
                bool(email_host)
                and "replace" not in email_host.lower()
                and 1 <= getattr(settings, "EMAIL_PORT", 0) <= 65535
                and bool(email_user)
                and "replace" not in email_user.lower()
                and bool(email_password)
                and "replace" not in email_password.lower()
                and "@" in default_from_email
                and "replace" not in default_from_email.lower()
                and bool(getattr(settings, "EMAIL_USE_TLS", False))
                != bool(getattr(settings, "EMAIL_USE_SSL", False))
                and not getattr(settings, "EMAIL_FAIL_SILENTLY", True),
                "SMTP fallback configuration is explicit and fail-closed",
                "SMTP host, credentials, sender, transport security, or failure policy is invalid",
            ),
            _result(
                "maintenance_policy",
                5 <= getattr(settings, "HYDRA_MAINTENANCE_INTERVAL_SECONDS", 0) <= 300
                and getattr(settings, "HYDRA_MAINTENANCE_STALE_SECONDS", 0)
                >= 2 * getattr(settings, "HYDRA_MAINTENANCE_INTERVAL_SECONDS", 0)
                and getattr(settings, "HYDRA_MAINTENANCE_PURGE_INTERVAL_SECONDS", 0)
                >= getattr(settings, "HYDRA_MAINTENANCE_INTERVAL_SECONDS", 0)
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_NOTIFICATION_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(
                    settings,
                    "HYDRA_MAINTENANCE_NOTIFICATION_EMAIL_BATCH_SIZE",
                    0,
                )
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_DOCUMENT_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_IMPORT_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_LEGALIZATION_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_ARRIVAL_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_HOUSING_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_ONBOARDING_BATCH_SIZE", 0)
                <= 1000
                and 1
                <= getattr(settings, "HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE", 0)
                <= 1000
                and getattr(settings, "HYDRA_MAINTENANCE_MAX_FAILURES", 0) > 0,
                "maintenance worker policy is bounded",
                "maintenance intervals, batch size, stale window, or failure limit are invalid",
            ),
            _result(
                "legalization_automation_policy",
                bool(
                    getattr(settings, "HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS", ())
                )
                and bool(
                    getattr(settings, "HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS", ())
                )
                and all(
                    1 <= day <= 365
                    for day in getattr(
                        settings, "HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS", ()
                    )
                )
                and all(
                    1 <= day <= 365
                    for day in getattr(
                        settings, "HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS", ()
                    )
                )
                and len(
                    set(
                        getattr(
                            settings,
                            "HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS",
                            (),
                        )
                    )
                )
                == len(
                    getattr(
                        settings, "HYDRA_LEGALIZATION_DEADLINE_REMINDER_DAYS", ()
                    )
                )
                and len(
                    set(
                        getattr(
                            settings,
                            "HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS",
                            (),
                        )
                    )
                )
                == len(
                    getattr(
                        settings, "HYDRA_LEGALIZATION_VALIDITY_REMINDER_DAYS", ()
                    )
                ),
                "legalization reminder policy is bounded",
                "legalization reminder days must be unique values from 1 to 365",
            ),
            _result(
                "arrival_automation_policy",
                bool(getattr(settings, "HYDRA_ARRIVAL_REMINDER_MINUTES", ()))
                and all(
                    1 <= minutes <= 10080
                    for minutes in getattr(
                        settings, "HYDRA_ARRIVAL_REMINDER_MINUTES", ()
                    )
                )
                and len(
                    set(getattr(settings, "HYDRA_ARRIVAL_REMINDER_MINUTES", ()))
                )
                == len(getattr(settings, "HYDRA_ARRIVAL_REMINDER_MINUTES", ())),
                "arrival reminder policy is bounded",
                "arrival reminder minutes must be unique values from 1 to 10080",
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


def domain_integrity_results():
    try:
        from hydra_legalization.models import (
            LegalizationCase,
            LegalizationCaseDelegation,
            LegalizationWorkEvent,
        )

        active_statuses = (
            LegalizationCase.Status.DRAFT,
            LegalizationCase.Status.COLLECTING_DOCUMENTS,
            LegalizationCase.Status.SUBMITTED,
            LegalizationCase.Status.ADDITIONAL_INFORMATION,
        )
        duplicate_groups = (
            LegalizationCase.objects.filter(status__in=active_statuses)
            .values("person_id", "company_id", "procedure_type_id")
            .annotate(case_count=Count("pk"))
            .filter(case_count__gt=1)
            .count()
        )
        overlap_count = 0
        previous_case_id = None
        covered_until = None
        for case_id, valid_from, valid_until in (
            LegalizationCaseDelegation.objects.filter(is_active=True)
            .order_by("case_id", "valid_from", "valid_until", "pk")
            .values_list("case_id", "valid_from", "valid_until")
            .iterator(chunk_size=1000)
        ):
            if case_id != previous_case_id:
                previous_case_id = case_id
                covered_until = valid_until
                continue
            if valid_from <= covered_until:
                overlap_count += 1
            if valid_until > covered_until:
                covered_until = valid_until
        stale_principal_count = LegalizationCaseDelegation.objects.filter(
            is_active=True,
            valid_until__gte=timezone.localdate(),
        ).exclude(principal_id=F("case__responsible_id")).count()
        missing_baseline_count = LegalizationCase.objects.exclude(
            work_events__action=LegalizationWorkEvent.Action.RESPONSIBILITY_ASSIGNED
        ).count()
        invalid_policy_snapshot_count = 0
        for company_id, procedure_uuid, status, snapshot in (
            LegalizationCase.objects.values_list(
                "company_id",
                "procedure_type__uuid",
                "status",
                "procedure_snapshot",
            ).iterator(chunk_size=1000)
        ):
            statuses = {
                row.get("status")
                for row in snapshot.get("statuses", [])
                if isinstance(row, dict)
            } if isinstance(snapshot, dict) else set()
            if (
                not isinstance(snapshot, dict)
                or snapshot.get("procedure_uuid") != str(procedure_uuid)
                or snapshot.get("case_company_id") != company_id
                or status not in statuses
                or (
                    snapshot.get("requires_authority")
                    and not snapshot.get("authorities")
                )
            ):
                invalid_policy_snapshot_count += 1
        from hydra_legalization.models import LegalizationAuthorityEvent

        invalid_authority_snapshot_count = 0
        for authority_uuid, authority, channel, snapshot in (
            LegalizationAuthorityEvent.objects.values_list(
                "authority_config__uuid",
                "authority",
                "channel",
                "authority_snapshot",
            ).iterator(chunk_size=1000)
        ):
            if (
                not isinstance(snapshot, dict)
                or snapshot.get("uuid") != str(authority_uuid)
                or snapshot.get("name") != authority
                or channel not in snapshot.get("allowed_channels", [])
            ):
                invalid_authority_snapshot_count += 1
    except Exception:
        return [
            ReadinessResult(
                "legalization_active_uniqueness",
                False,
                "legalization active-case integrity could not be verified",
            )
        ]
    legalization_results = [
        _result(
            "legalization_active_uniqueness",
            duplicate_groups == 0,
            "active legalization cases are unique per person, company and procedure",
            f"{duplicate_groups} active legalization person/company/procedure group(s) require review",
        ),
        _result(
            "legalization_delegation_windows",
            overlap_count == 0,
            "legalization delegation windows do not overlap",
            f"{overlap_count} overlapping legalization delegation window(s) require review",
        ),
        _result(
            "legalization_delegation_principals",
            stale_principal_count == 0,
            "current and scheduled deputies match the current case owner",
            f"{stale_principal_count} current or scheduled deputy assignment(s) have a stale principal",
        ),
        _result(
            "legalization_responsibility_baseline",
            missing_baseline_count == 0,
            "every legalization case has a responsibility baseline",
            f"{missing_baseline_count} legalization case(s) lack a responsibility baseline",
        ),
        _result(
            "legalization_policy_snapshots",
            invalid_policy_snapshot_count == 0,
            "every legalization case has a complete scoped procedure snapshot",
            f"{invalid_policy_snapshot_count} legalization case policy snapshot(s) require review",
        ),
        _result(
            "legalization_authority_snapshots",
            invalid_authority_snapshot_count == 0,
            "every authority fact preserves an approved authority snapshot",
            f"{invalid_authority_snapshot_count} authority event snapshot(s) require review",
        ),
    ]
    try:
        from hydra_housing.models import (
            HousingAssignment,
            HousingAssignmentEvent,
            HousingRoom,
        )

        def overlap_count_for(field_name):
            overlap_count = 0
            previous_owner = None
            covered_until = None
            for owner_id, valid_from, valid_until in (
                HousingAssignment._base_manager.filter(is_active=True)
                .order_by(field_name, "valid_from", "valid_until", "pk")
                .values_list(field_name, "valid_from", "valid_until")
                .iterator(chunk_size=1000)
            ):
                effective_until = valid_until or date.max
                if owner_id != previous_owner:
                    previous_owner = owner_id
                    covered_until = effective_until
                    continue
                if valid_from <= covered_until:
                    overlap_count += 1
                if effective_until > covered_until:
                    covered_until = effective_until
            return overlap_count

        bed_overlap_count = overlap_count_for("bed_id")
        person_overlap_count = overlap_count_for("person_id")
        missing_origin_count = HousingAssignment._base_manager.exclude(
            events__action__in=HousingAssignmentEvent.ORIGIN_ACTIONS
        ).count()
        inactive_without_terminal = HousingAssignment._base_manager.filter(
            is_active=False
        ).exclude(
            events__action__in=(
                HousingAssignmentEvent.Action.CANCELLED,
                HousingAssignmentEvent.Action.EXPIRED,
                HousingAssignmentEvent.Action.MOVED_OUT,
            )
        ).count()
        active_cancelled_count = HousingAssignment._base_manager.filter(
            is_active=True,
            events__action__in=(
                HousingAssignmentEvent.Action.CANCELLED,
                HousingAssignmentEvent.Action.EXPIRED,
            ),
        ).count()
        overdue_temporary_count = HousingAssignment._base_manager.filter(
            is_active=True,
            reservation_expires_at__isnull=False,
            reservation_expires_at__lte=timezone.now(),
        ).count()
        confirmed_with_expiry_count = HousingAssignment._base_manager.filter(
            events__action=HousingAssignmentEvent.Action.CONFIRMED,
            reservation_expires_at__isnull=False,
        ).count()
        hierarchy_mismatch_count = HousingRoom._base_manager.filter(
            floor_unit__isnull=False,
        ).exclude(
            facility_id=F("floor_unit__building__facility_id")
        ).count()
        moved_shape_issues = 0
        for is_active, valid_from, valid_until, effective_on in (
            HousingAssignmentEvent.objects.filter(
                action=HousingAssignmentEvent.Action.MOVED_OUT
            )
            .values_list(
                "assignment__is_active",
                "assignment__valid_from",
                "assignment__valid_until",
                "effective_on",
            )
            .iterator(chunk_size=1000)
        ):
            if is_active:
                if valid_until != effective_on - timedelta(days=1):
                    moved_shape_issues += 1
            elif valid_from != effective_on:
                moved_shape_issues += 1
        lifecycle_issue_count = (
            inactive_without_terminal + active_cancelled_count + moved_shape_issues
            + confirmed_with_expiry_count
        )
    except Exception:
        return legalization_results + [
            ReadinessResult(
                "housing_assignment_integrity",
                False,
                "housing assignment integrity could not be verified",
            )
        ]
    housing_results = [
        _result(
            "housing_bed_periods",
            bed_overlap_count == 0,
            "active housing periods do not overlap per bed",
            f"{bed_overlap_count} overlapping bed period(s) require review",
        ),
        _result(
            "housing_person_periods",
            person_overlap_count == 0,
            "active housing periods do not overlap per person",
            f"{person_overlap_count} overlapping Person housing period(s) require review",
        ),
        _result(
            "housing_assignment_baseline",
            missing_origin_count == 0,
            "every housing assignment has an origin event",
            f"{missing_origin_count} housing assignment(s) lack an origin event",
        ),
        _result(
            "housing_assignment_lifecycle",
            lifecycle_issue_count == 0,
            "housing assignment active state matches terminal events",
            f"{lifecycle_issue_count} housing assignment lifecycle issue(s) require review",
        ),
        _result(
            "housing_hierarchy",
            hierarchy_mismatch_count == 0,
            "every structured room floor belongs to its facility",
            f"{hierarchy_mismatch_count} room hierarchy link(s) cross facilities",
        ),
        _result(
            "housing_temporary_reservations",
            overdue_temporary_count == 0,
            "temporary housing reservations are processed before expiry",
            f"{overdue_temporary_count} temporary reservation(s) await expiry processing",
        ),
    ]
    try:
        from hydra_documents.models import PrivateDocument

        current_conflict_count = (
            PrivateDocument._base_manager.filter(
                deleted_at__isnull=True,
                replaced_by__isnull=True,
                document_type__single_current=True,
            )
            .values("candidate_id", "document_type_id")
            .annotate(version_count=Count("pk"))
            .filter(version_count__gt=1)
            .count()
        )
        replacement_count = PrivateDocument._base_manager.filter(
            replaces__isnull=False
        ).count()
        valid_replacement_count = PrivateDocument._base_manager.filter(
            replaces__isnull=False,
            candidate_id=F("replaces__candidate_id"),
            person_id=F("replaces__person_id"),
            document_type_id=F("replaces__document_type_id"),
            lineage_uuid=F("replaces__lineage_uuid"),
            version_number=F("replaces__version_number") + 1,
        ).count()
        broken_chain_count = replacement_count - valid_replacement_count

        required_snapshot_keys = {
            "type_uuid",
            "code",
            "name",
            "category",
            "company_id",
            "allowed_content_types",
            "max_size_bytes",
            "retention_days",
            "requires_expiry_date",
            "single_current",
        }
        invalid_snapshot_count = 0
        for type_uuid, snapshot in (
            PrivateDocument._base_manager.values_list(
                "document_type__uuid", "type_rules_snapshot"
            ).iterator(chunk_size=1000)
        ):
            if (
                not isinstance(snapshot, dict)
                or not required_snapshot_keys.issubset(snapshot)
                or snapshot.get("type_uuid") != str(type_uuid)
            ):
                invalid_snapshot_count += 1
    except Exception:
        return legalization_results + housing_results + [
            ReadinessResult(
                "private_document_integrity",
                False,
                "private-document version integrity could not be verified",
            )
        ]
    document_results = [
        _result(
            "private_document_current_versions",
            current_conflict_count == 0,
            "single-current document types have one current version per application",
            f"{current_conflict_count} application/type group(s) have multiple current documents",
        ),
        _result(
            "private_document_version_chains",
            broken_chain_count == 0,
            "private-document replacement chains preserve identity and sequence",
            f"{broken_chain_count} private-document replacement link(s) are inconsistent",
        ),
        _result(
            "private_document_rule_snapshots",
            invalid_snapshot_count == 0,
            "every private-document version has a complete type-rule snapshot",
            f"{invalid_snapshot_count} private-document version(s) have an invalid rule snapshot",
        ),
    ]
    try:
        from hydra_tasks.models import HydraTask, HydraTaskNotificationDelivery
        from hydra_tasks.selectors import user_is_eligible_task_assignee
        from hydra_tasks.targets import stored_target_is_valid

        invalid_target_count = 0
        stale_assignee_count = 0
        active_statuses = (HydraTask.Status.OPEN, HydraTask.Status.IN_PROGRESS)
        for task in HydraTask._base_manager.select_related(
            "person",
            "person__employee",
            "company",
            "assignee",
        ).iterator(chunk_size=500):
            if not stored_target_is_valid(task):
                invalid_target_count += 1
            if task.status in active_statuses and not user_is_eligible_task_assignee(
                user=task.assignee,
                person=task.person,
                company=task.company,
            ):
                stale_assignee_count += 1
        event_shape_count = (
            HydraTask._base_manager.annotate(
                event_count=Count("events"),
                latest_sequence=Max("events__sequence"),
            )
            .exclude(event_count=F("version"), latest_sequence=F("version"))
            .count()
        )
        delivery_shape_count = HydraTaskNotificationDelivery.objects.exclude(
            task_id=F("event__task_id")
        ).count()
    except Exception:
        return legalization_results + housing_results + document_results + [
            ReadinessResult(
                "task_integrity",
                False,
                "Hydra task integrity could not be verified",
            )
        ]
    task_results = [
        _result(
            "task_targets",
            invalid_target_count == 0,
            "every Hydra task target matches its Person and Company",
            f"{invalid_target_count} Hydra task target(s) require review",
        ),
        _result(
            "task_assignees",
            stale_assignee_count == 0,
            "every active Hydra task has an eligible scoped assignee",
            f"{stale_assignee_count} active Hydra task assignee(s) lost permission or scope",
        ),
        _result(
            "task_event_sequences",
            event_shape_count == 0 and delivery_shape_count == 0,
            "every Hydra task version and notification delivery has a consistent event sequence",
            f"{event_shape_count + delivery_shape_count} Hydra task event or delivery sequence(s) require review",
        ),
    ]
    try:
        from hydra_onboarding.models import (
            CourseAssignment,
            CourseAssignmentRule,
            CourseVersion,
            Quiz,
        )
        from hydra_onboarding.services import version_content_fingerprint

        published_content_issue_count = 0
        for version in CourseVersion._base_manager.filter(
            status=CourseVersion.Status.PUBLISHED
        ).iterator(chunk_size=200):
            if (
                not version.lessons.exists()
                or len(version.content_fingerprint) != 64
                or version_content_fingerprint(version) != version.content_fingerprint
            ):
                published_content_issue_count += 1
                continue
            try:
                quiz = version.quiz
            except Quiz.DoesNotExist:
                continue
            questions = list(quiz.questions.prefetch_related("options"))
            if not questions:
                published_content_issue_count += 1
                continue
            for question in questions:
                options = list(question.options.all())
                if len(options) < 2 or sum(option.is_correct for option in options) != 1:
                    published_content_issue_count += 1
                    break

        rule_issue_count = 0
        for rule in CourseAssignmentRule._base_manager.filter(
            is_active=True,
            course__is_active=True,
        ).iterator(chunk_size=500):
            versions = CourseVersion._base_manager.filter(
                course=rule.course,
                status=CourseVersion.Status.PUBLISHED,
                is_active=True,
            )
            if rule.language:
                versions = versions.filter(language=rule.language)
            if not versions.exists():
                rule_issue_count += 1

        assignment_snapshot_issue_count = 0
        completed_issue_count = 0
        for assignment in CourseAssignment._base_manager.select_related(
            "course",
            "course_version",
        ).iterator(chunk_size=500):
            snapshot = assignment.assignment_snapshot
            if (
                assignment.company_id != assignment.course.company_id
                or assignment.course_version.course_id != assignment.course_id
                or not isinstance(snapshot, dict)
                or snapshot.get("course_uuid") != str(assignment.course.uuid)
                or snapshot.get("course_version_uuid")
                != str(assignment.course_version.uuid)
                or snapshot.get("content_fingerprint")
                != assignment.course_version.content_fingerprint
            ):
                assignment_snapshot_issue_count += 1
            if assignment.status == CourseAssignment.Status.COMPLETED:
                try:
                    assignment.confirmation
                except Exception:
                    completed_issue_count += 1
                    continue
                try:
                    quiz = assignment.course_version.quiz
                except Quiz.DoesNotExist:
                    quiz = None
                if quiz is not None and not assignment.quiz_attempts.filter(
                    quiz=quiz,
                    passed=True,
                ).exists():
                    completed_issue_count += 1

        onboarding_event_issue_count = (
            CourseAssignment._base_manager.annotate(
                event_count=Count("events"),
                latest_sequence=Max("events__sequence"),
            )
            .exclude(event_count=F("version"), latest_sequence=F("version"))
            .count()
        )
    except Exception:
        return (
            legalization_results
            + housing_results
            + document_results
            + task_results
            + [
                ReadinessResult(
                    "onboarding_content_integrity",
                    False,
                    "onboarding content and assignment integrity could not be verified",
                )
            ]
        )
    onboarding_results = [
        _result(
            "onboarding_published_content",
            published_content_issue_count == 0,
            "published onboarding versions are complete and fingerprint-consistent",
            f"{published_content_issue_count} published onboarding version(s) require review",
        ),
        _result(
            "onboarding_assignment_rules",
            rule_issue_count == 0,
            "every active onboarding rule has an assignable published version",
            f"{rule_issue_count} active onboarding rule(s) lack a published version",
        ),
        _result(
            "onboarding_assignment_snapshots",
            assignment_snapshot_issue_count == 0,
            "onboarding assignments preserve their exact published version snapshot",
            f"{assignment_snapshot_issue_count} onboarding assignment snapshot(s) require review",
        ),
        _result(
            "onboarding_completion_evidence",
            completed_issue_count == 0 and onboarding_event_issue_count == 0,
            "onboarding completion and append-only event sequences are consistent",
            f"{completed_issue_count + onboarding_event_issue_count} onboarding completion or event record(s) require review",
        ),
    ]
    try:
        from django.db.models import Q

        from hydra_notifications.models import (
            HydraNotificationEmailDelivery,
            HydraNotificationEnvelope,
            NotificationKind,
        )
        from hydra_notifications.policy import policy_for
        from hydra_notifications.services import _target_contract

        state_mismatch_count = HydraNotificationEnvelope._base_manager.filter(
            Q(read_at__isnull=True, notification__unread=False)
            | Q(read_at__isnull=False, notification__unread=True)
            | Q(archived_at__isnull=True, notification__deleted=True)
            | Q(archived_at__isnull=False, notification__deleted=False)
            | ~Q(recipient_id=F("notification__recipient_id"))
        ).count()
        event_mismatch_count = (
            HydraNotificationEnvelope._base_manager.annotate(
                event_count=Count("state_events"),
                latest_sequence=Max("state_events__sequence"),
            )
            .exclude(event_count=F("version"), latest_sequence=F("version"))
            .count()
        )
        target_mismatch_count = 0
        payload_mismatch_count = 0
        allowed_data_keys = {"redirect", "verb_en", "icon", "label"}
        for envelope in HydraNotificationEnvelope._base_manager.select_related(
            "notification"
        ).iterator(chunk_size=500):
            if envelope.kind == NotificationKind.LEGACY:
                continue
            try:
                _target, company, person = _target_contract(
                    target_kind=envelope.target_kind,
                    target_uuid=envelope.target_uuid,
                )
            except Exception:
                target_mismatch_count += 1
            else:
                if (
                    envelope.company_id != getattr(company, "pk", None)
                    or envelope.person_id != getattr(person, "pk", None)
                ):
                    target_mismatch_count += 1
            data = envelope.notification.data
            try:
                policy = policy_for(envelope.kind)
            except ValueError:
                payload_mismatch_count += 1
                continue
            if (
                envelope.notification.verb != policy.message
                or not isinstance(data, dict)
                or not set(data).issubset(allowed_data_keys)
                or data.get("verb_en") != policy.message
            ):
                payload_mismatch_count += 1
        delivery_mismatch_count = HydraNotificationEmailDelivery._base_manager.exclude(
            recipient_id=F("envelope__recipient_id")
        ).count()
        dead_delivery_count = HydraNotificationEmailDelivery._base_manager.filter(
            status=HydraNotificationEmailDelivery.Status.DEAD
        ).count()
    except Exception:
        return legalization_results + housing_results + document_results + task_results + onboarding_results + [
            ReadinessResult(
                "notification_integrity",
                False,
                "Hydra notification integrity could not be verified",
            )
        ]
    notification_results = [
        _result(
            "notification_read_state",
            state_mismatch_count == 0 and event_mismatch_count == 0,
            "notification read/archive state and append-only sequences are consistent",
            f"{state_mismatch_count + event_mismatch_count} notification state record(s) require review",
        ),
        _result(
            "notification_targets",
            target_mismatch_count == 0,
            "managed notification targets match their Person and Company",
            f"{target_mismatch_count} managed notification target(s) require review",
        ),
        _result(
            "notification_payloads",
            payload_mismatch_count == 0,
            "managed in-app notification payloads use reviewed PII-free messages",
            f"{payload_mismatch_count} managed notification payload(s) require review",
        ),
        _result(
            "notification_email_deliveries",
            delivery_mismatch_count == 0 and dead_delivery_count == 0,
            "notification email deliveries match recipients and have no exhausted retries",
            f"{delivery_mismatch_count} mismatched and {dead_delivery_count} exhausted email delivery record(s) require review",
        ),
    ]
    return (
        legalization_results
        + housing_results
        + document_results
        + task_results
        + onboarding_results
        + notification_results
    )


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
    quarantine_root = Path(settings.HYDRA_DOCUMENT_QUARANTINE_ROOT)
    portal_email_root = Path(settings.HYDRA_PORTAL_EMAIL_MEDIA_ROOT)
    results = [
        _result(
            "storage_separation",
            not _paths_overlap(media_root, private_root),
            "public and private media roots are separated",
            "MEDIA_ROOT and HYDRA_PRIVATE_MEDIA_ROOT must not overlap",
        ),
        _result(
            "quarantine_separation",
            not _paths_overlap(media_root, quarantine_root)
            and not _paths_overlap(private_root, quarantine_root),
            "document quarantine is separated from public and private media",
            "HYDRA_DOCUMENT_QUARANTINE_ROOT must not overlap other media roots",
        ),
        _result(
            "portal_email_storage_separation",
            not _paths_overlap(media_root, portal_email_root)
            and not _paths_overlap(private_root, portal_email_root)
            and not _paths_overlap(quarantine_root, portal_email_root),
            "portal email storage is separated from other media roots",
            "HYDRA_PORTAL_EMAIL_MEDIA_ROOT must not overlap other media roots",
        ),
    ]
    for name, path in (
        ("media_root", media_root),
        ("private_media_root", private_root),
        ("document_quarantine_root", quarantine_root),
        ("portal_email_media_root", portal_email_root),
    ):
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


def scanner_results():
    if getattr(settings, "HYDRA_ENVIRONMENT", "development") not in DEPLOYMENT_ENVIRONMENTS:
        return []
    from hydra_documents.scanning import scanner_health

    ok, detail = scanner_health()
    return [ReadinessResult("document_scanner_health", ok, detail)]


def collect_readiness(*, include_filesystem=True, include_migrations=True):
    results = configuration_results()
    results.extend(database_results(include_migrations=include_migrations))
    results.extend(domain_integrity_results())
    if include_filesystem:
        results.extend(filesystem_results())
    results.extend(scanner_results())
    return results


def readiness_payload(results):
    return {
        "status": "ready" if all(result.ok for result in results) else "not_ready",
        "environment": getattr(settings, "HYDRA_ENVIRONMENT", "development"),
        "checks": [result.as_dict() for result in results],
    }
