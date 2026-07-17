# Hydra operational reports

## Status

Task `044-reports.md` is implemented as the `hydra_reports` Django app. It provides one complete operational reporting slice across scoped Hydra people, current assignments, arrivals, housing and legalization cases, with server-generated CSV and append-only export audit.

The supplied 044 brief duplicated the earlier housing task. The implemented scope follows the numerical architecture, `HORILLA_AUDIT.md`, `REUSE_MATRIX.md`, `IMPLEMENTATION_DECISIONS.md` and the completed coordinator/report dependencies.

## Reuse decision

The solution is **EXTEND + WRAP**:

- Horilla's report navigation, filter/table conventions and existing business reports remain unchanged;
- Hydra adds its own authenticated report route and responsive table within the shared shell;
- all records originate from Hydra permission-and-scope selectors;
- export is generated and authorized on the server rather than from browser DOM data.

The audited Horilla pivot endpoints start from broad managers such as `Employee.objects.all()` and `Candidate.objects.all()`, then rely mainly on model permissions and the selected Company session. Their client-side Excel export is not reused for Hydra data because it cannot be the authorization boundary.

## Permission boundary

The report requires all of the following permissions:

- `hydra_reports.view_operational_report`;
- `hydra_people.view_person`;
- `hydra_coordination.view_personassignment`;
- `hydra_coordination.view_location`;
- `hydra_coordination.view_team`;
- `hydra_arrivals.view_arrivalplan`;
- `recruitment.view_candidate`;
- `hydra_legalization.view_legalizationcase`.
- `hydra_housing.view_housingfacility`, `view_housingroom`, `view_housingbed` and `view_housingassignment`.

CSV additionally requires `hydra_reports.export_operational_report`. Audit visibility requires `hydra_reports.view_operationalreportexport`; ordinary users see only their own ten latest entries, while superuser is the explicit all-actor view.

The report starts from `people_for_user`. Current assignments are re-intersected with that visible Person set, arrivals come from `arrival_plans_for_user`, and legalization cases come from `legalization_cases_for_user`. A Team grant can expose its assigned people but does not silently grant arrival access; the arrival selector's existing Company/Location requirement remains authoritative.

Location and Team filter choices are limited to active scope. A forged filter is invalid, exports nothing and creates no audit row. The save/export service independently rechecks scope, so bypassing the HTML form does not widen access. Horilla session value `selected_company=all` has no effect on Hydra scope.

## Report contract

The route `/hydra/reports/` provides:

- search by Hydra ID or name;
- lifecycle, Location and Team filters;
- arrival and legalization status filters;
- attention filters for overdue/no-show arrivals, missing housing after a confirmed arrival, legalization attention and missing current assignment;
- five full-query summary counts;
- a 50-row responsive page with links to already-authorized source records;
- the latest relevant assignment, arrival and legalization record plus current Housing assignment for each Person.

When a domain status or attention filter is active, the displayed and exported domain record is the newest record satisfying that filter, not an unrelated later record belonging to the same Person.

## Authorized CSV export

The POST-only export applies the exact validated report filters and has a 10,000-row safety limit. It emits UTF-8 with BOM and the following stable columns:

```text
HYDRA_ID
PASSPORT_NAME
LIFECYCLE_STATE
COMPANY
LOCATION
SECTION
TEAM
ARRIVAL_STATUS
PLANNED_AT
LEGALIZATION_TYPE
LEGALIZATION_STATUS
LEGALIZATION_DEADLINE
LEGALIZATION_VALID_UNTIL
HOUSING_FACILITY
HOUSING_ROOM
HOUSING_BED
HOUSING_VALID_FROM
HOUSING_VALID_UNTIL
ATTENTION_FLAGS
```

No phone, email, date of birth, document metadata or private file URL is included. Text beginning with `=`, `+`, `-` or `@` is prefixed with an apostrophe to prevent spreadsheet formula execution. The response is `no-store, private`, `no-cache` and `nosniff`; it is not written to public media.

Every successful response creates one `OperationalReportExport` row containing actor, time, format, filename, row count, SHA-256, normalized filters and effective Location/Team IDs. Instance and queryset update/delete operations are rejected after creation.

## Verification

Focused PostgreSQL coverage contains 14 tests for report and domain permissions, Team scope, forged Location filters, the Company `all` denial rule, arrival and Housing attention filtering, missing export permission, exact scoped CSV rows, formula neutralization, private response headers, service-level scope rechecks, append-only audit, actor-only audit visibility and an existing Horilla employee view.

The complete implemented regression passes:

```text
Ran 190 tests - OK
```

`manage.py check`, `makemigrations --check --dry-run hydra_reports` and migration `hydra_reports.0001_initial` pass on PostgreSQL.

Browser verification used the real PostgreSQL schema and `hydra-qa`. At 390 x 844 pixels the document width was 380 pixels; table and controls were 316.8 pixels wide; all four KPI cards fit in a two-column grid; no element crossed the viewport. Applying `Arrival attention` reduced 4 visible records to 1. The CSV download started, and the refreshed audit showed actor `hydra-qa`, one row and a SHA-256 digest. `Reports` was the active navigation item and browser error/warning logs were empty.

## Deliberate limits

- The MVP has one operational Person-centred report, not a generic report designer.
- CSV is the authorized interchange format; browser-generated XLSX and arbitrary pivot configuration are not security boundaries.
- Large asynchronous exports, scheduled reports and email delivery are deferred.
- Report rows use current assignments and the latest record relevant to active filters; they are not historical time-series analytics.
- Historical time-series housing analytics and occupancy forecasting remain outside this single current-state report.

Task 045 hardened staging, recovery, and pilot gates are implemented in `HYDRA_STAGING.md`.
