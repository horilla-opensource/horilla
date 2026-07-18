# Hydra public links

## Status

Task `043-hydra-links.md` is implemented as the `hydra_links` Django app. It keeps the audited public Hydra portal and training pages outside the authenticated application while exposing their controlled, scope-aware links in the Hydra workspace.

The supplied 043 brief duplicated the earlier arrivals task, so the implemented scope follows `TARGET_ARCHITECTURE.md`, `HYDRA_PORTAL_MIGRATION.md`, `IMPLEMENTATION_DECISIONS.md` and the numerical delivery order.

## Reuse decision

The solution is **WRAP**:

- the existing GitHub Pages portal and training sites stay independently deployed;
- the shared `Training / Hydra` shell link driven by `HYDRA_PORTAL_URL` remains available;
- Hydra adds database-owned global arrival guidance and Location-specific training records;
- no public portal HTML, audio, manifest or service worker is copied into Django.

The public service worker never controls an authenticated Hydra route and cannot cache private Hydra responses.

## Record contract

`PublicHydraLink` stores an immutable UUID, kind, optional Location, public label, base URL, display order and the normal Hydra active/authorship metadata.

There are two controlled kinds:

| Kind | Scope | Cardinality |
|---|---|---|
| Arrival guidance | Global; Location must be empty | At most one global arrival record |
| Location training | Exactly one Location | At most one training record per Location |

Database constraints enforce both the kind/scope relationship and uniqueness. The initial migration creates the audited global `Arrival to work` link. Location training records are configured by authorized operators rather than inferred from Person or employee data.

## Public URL boundary

Stored URLs must be absolute HTTPS URLs with a hostname. Credentials, fragments, custom ports and arbitrary query parameters are rejected. The only optional stored query parameter is a single `v` value containing 1-64 letters, digits, dots, underscores or hyphens.

At render time Hydra preserves `v`, maps the selected public language (including Django `uk` to portal `ua`) and appends only:

```text
lang=<public-language>&from=hydra
```

The fallback language is Russian. Person IDs, employee IDs, assignments, session values, authentication tokens and other private data are never appended. External anchors use `target="_blank"` together with `rel="noopener noreferrer external"` and a visible external-site label.

## Permission and scope model

Reading requires `hydra_links.view_publichydralink`. Creating and changing records require the matching Django model permission and an active Hydra scope that resolves to the selected Location. A separate `hydra_links.manage_global_publichydralink` permission is required to create or change a global record.

The form restricts Location choices, the object selector returns 404 for an out-of-scope direct URL, and the save service independently rechecks permission and scope. Selecting legacy HR platform company `all` does not widen Hydra access. Superuser remains the explicit bypass.

Deletion is intentionally absent from the operator UI. Records can instead be deactivated while preserving configuration history.

## Contextual integration

The directory at `/hydra/links/` lists the active global record plus training records within the actor's effective Hydra scope. Users with change permission also see inactive records for maintenance.

Public guidance is composed into existing screens without weakening their own authorization:

- Person detail: global arrival guidance plus training for the current visible assignment Location;
- arrival detail: global arrival guidance plus training for the destination Location;
- brigadier panel: training for the selected Team's Location;
- coordinator panel: training for the selected Location.

If the actor cannot see the parent Person, arrival, Team or Location, the contextual link does not create a second path to that record.

## Verification

Focused PostgreSQL coverage contains 12 tests for URL construction and rejection, model constraints, missing permissions, Location scope, global-management separation, direct URL denial, service-level rechecks, the company `all` denial rule and contextual rendering on Person, arrival, brigadier and coordinator screens.

The complete implemented regression passes:

```text
Ran 154 tests - OK
```

`manage.py check`, `makemigrations --check --dry-run hydra_links` and migration `hydra_links.0001_initial` pass on PostgreSQL.

Browser verification used the real PostgreSQL schema and the `hydra-qa` operator. At 390 x 844 pixels the directory and create form had no horizontal overflow: the document width was 380 pixels, the table and visible form controls were 316.8 pixels wide, the create action remained inside the viewport and `Public links` was the active navigation item. The rendered destination preserved `v`, added only `lang` and `from=hydra`, and exposed `target="_blank"` with `rel="noopener noreferrer external"`.

## Deliberate limits

- Hydra does not mirror, scrape or edit public portal/training content.
- Link availability is not treated as proof that an external destination is healthy.
- There is no personalized public worker portal, anonymous completion tracking or token handoff.
- Native-speaker review and public-site accessibility/offline verification remain owned by the external deployments.
- Migrating public content into anonymous Django routes remains a later, separately accepted project.

Task 044 scoped operational reports and task 045 hardened staging are now implemented; see `HYDRA_REPORTS.md` and `HYDRA_STAGING.md`.
