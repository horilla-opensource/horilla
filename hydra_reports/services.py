import csv
import hashlib
from io import StringIO

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from hydra_coordination.selectors import locations_for_user, teams_for_user
from hydra_reports.models import OperationalReportExport
from hydra_reports.selectors import (
    REPORT_VIEW_PERMISSIONS,
    operational_people_for_user,
    operational_report_rows,
)


EXPORT_PERMISSIONS = REPORT_VIEW_PERMISSIONS + (
    "hydra_reports.export_operational_report",
)
MAX_EXPORT_ROWS = 10000
CSV_HEADERS = (
    "HYDRA_ID",
    "PASSPORT_NAME",
    "LIFECYCLE_STATE",
    "COMPANY",
    "LOCATION",
    "SECTION",
    "TEAM",
    "ARRIVAL_STATUS",
    "PLANNED_AT",
    "LEGALIZATION_TYPE",
    "LEGALIZATION_STATUS",
    "LEGALIZATION_DEADLINE",
    "LEGALIZATION_VALID_UNTIL",
    "HOUSING_FACILITY",
    "HOUSING_ROOM",
    "HOUSING_BED",
    "HOUSING_VALID_FROM",
    "HOUSING_VALID_UNTIL",
    "ATTENTION_FLAGS",
)


def serialized_report_filters(filters):
    return {
        "q": (filters.get("q") or "").strip(),
        "lifecycle": filters.get("lifecycle") or "",
        "location_id": getattr(filters.get("location"), "pk", None),
        "team_id": getattr(filters.get("team"), "pk", None),
        "arrival_status": filters.get("arrival_status") or "",
        "legalization_status": filters.get("legalization_status") or "",
        "attention": filters.get("attention") or "",
    }


def _validate_filter_scope(*, actor, filters):
    scoped_location_ids = set(
        locations_for_user(user=actor).values_list("pk", flat=True)
    )
    scoped_team_ids = set(teams_for_user(user=actor).values_list("pk", flat=True))
    location = filters.get("location")
    team = filters.get("team")
    if location and location.pk not in scoped_location_ids:
        raise PermissionDenied
    if team and team.pk not in scoped_team_ids:
        raise PermissionDenied
    if location and team and team.section.location_id != location.pk:
        raise PermissionDenied
    return sorted(scoped_location_ids), sorted(scoped_team_ids)


def _safe_csv_text(value):
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@"):
        text = "'" + text
    return text


def _iso_datetime(value):
    if value is None:
        return ""
    return timezone.localtime(value).isoformat(timespec="minutes")


def _report_row_values(row):
    assignment = row.assignment
    arrival = row.arrival
    legalization = row.legalization
    housing = row.housing
    if assignment:
        team = assignment.team
        section = team.section
        location = section.location
        company = location.company
    else:
        team = section = location = company = None
    return (
        row.person.hydra_id,
        row.person.passport_name,
        row.person.lifecycle_state,
        company.company if company else "",
        location.name if location else "",
        section.name if section else "",
        team.name if team else "",
        arrival.status if arrival else "",
        _iso_datetime(arrival.planned_at) if arrival else "",
        legalization.case_type if legalization else "",
        legalization.status if legalization else "",
        legalization.deadline.isoformat()
        if legalization and legalization.deadline
        else "",
        legalization.valid_until.isoformat()
        if legalization and legalization.valid_until
        else "",
        housing.bed.room.facility.name if housing else "",
        housing.bed.room.name if housing else "",
        housing.bed.label if housing else "",
        housing.valid_from.isoformat() if housing else "",
        housing.valid_until.isoformat() if housing and housing.valid_until else "",
        ";".join(row.attention_flags),
    )


def build_operational_report_csv(*, rows):
    output = StringIO(newline="")
    output.write("\ufeff")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CSV_HEADERS)
    for row in rows:
        writer.writerow([_safe_csv_text(value) for value in _report_row_values(row)])
    return output.getvalue().encode("utf-8")


def create_operational_report_export(*, actor, filters):
    if not actor.has_perms(EXPORT_PERMISSIONS):
        raise PermissionDenied
    scope_location_ids, scope_team_ids = _validate_filter_scope(
        actor=actor,
        filters=filters,
    )
    people = list(
        operational_people_for_user(user=actor, filters=filters)[: MAX_EXPORT_ROWS + 1]
    )
    if len(people) > MAX_EXPORT_ROWS:
        raise ValidationError(
            _("Export exceeds the %(limit)s-row safety limit.")
            % {"limit": MAX_EXPORT_ROWS}
        )
    rows = operational_report_rows(user=actor, people=people, filters=filters)
    payload = build_operational_report_csv(rows=rows)
    digest = hashlib.sha256(payload).hexdigest()
    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    filename = f"Hydra_Operational_Report_{timestamp}.csv"
    audit = OperationalReportExport.objects.create(
        actor=actor,
        format=OperationalReportExport.Format.CSV,
        filename=filename,
        row_count=len(rows),
        sha256=digest,
        filters=serialized_report_filters(filters),
        scope_location_ids=scope_location_ids,
        scope_team_ids=scope_team_ids,
    )
    return payload, audit
