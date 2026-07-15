# Hydra Person identity — TASK-1

## Status and reuse decision

Implemented after Phase 0 approval on 2026-07-14.

| Concern | Decision | Rationale |
|---|---|---|
| Canonical identity | **NEW** `hydra_people.Person` | Horilla Employee requires employment semantics and email; Candidate is an application, not a person. |
| Employee | **REUSE/LINK** | A nullable one-to-one link enables later conversion without copying work ownership into Person. |
| Recruitment Candidate | **WRAP** with `PersonApplication` | One Person can own many applications while each Candidate belongs to exactly one Person. The bridge avoids adding a new migration to the upstream recruitment app before its baseline-migration problem is remediated. |
| Authentication and authorization | **REUSE/EXTEND** Django/Horilla auth | Default model permissions plus explicit `link_candidate` permission protect every server endpoint. |
| Audit metadata | **REUSE** `HorillaModel` and global auditlog | Creation/modification actors and auditlog history remain consistent with Horilla. |

## Implemented vertical slice

`Person` owns:

- immutable UUID and generated readable `HYD-…` identifier;
- passport, first and last names;
- date of birth, gender and ISO two-letter citizenship code;
- one of the nine currently supported Hydra preferred languages;
- phone, WhatsApp/Viber and optional email;
- lifecycle state and active flag;
- optional one-to-one Employee link.

`PersonApplication` owns the explicit Person-to-Candidate link. The link service is transactional, row-locking and idempotent. It rejects a Candidate already linked to another Person and rejects conflicting Employee references. Linking the first application advances a prospect to candidate state. Django admin registrations are read-only so writes cannot bypass the service layer.

The server-rendered slice provides list/search, detail, create, edit and application-link screens at `/hydra/people/`. All record reads go through `hydra_people.selectors`; all writes go through `hydra_people.services`.

## Permissions

| Action | Required permission(s) |
|---|---|
| List/search/detail | `hydra_people.view_person` |
| Create | `hydra_people.add_person` |
| Edit | `hydra_people.change_person` |
| Link Candidate | `hydra_people.view_person`, `hydra_people.change_person`, `hydra_people.link_candidate`, `recruitment.view_candidate`, plus Candidate scope |

Anonymous requests are redirected to login. Authenticated users missing an action permission receive HTTP 403. `hydra_people.selectors.people_for_user()` now also applies effective organization scope; out-of-scope direct object URLs return HTTP 404. The rules and denial tests are documented in `docs/HYDRA_ORGANIZATION_SCOPE.md`.

## Migration

`hydra_people/migrations/0001_initial.py` is versioned even though upstream Horilla ignores most migration files. It depends on locally generated upstream `employee.0001_initial` and `recruitment.0001_initial`, matching the Phase 0 bootstrap strategy. TASK-2 adds `0002_personapplication_link_source.py`; no upstream schema was modified.

## Manual verification

1. Bootstrap and run the application as described in `docs/LOCAL_DEVELOPMENT.md`.
2. Grant a test role `view_person`, `add_person`, `change_person`, `link_candidate` and `recruitment.view_candidate`.
3. Open `/hydra/people/` on desktop and at a viewport no wider than 390 px.
4. Create a Person without an email and confirm a generated Hydra ID appears.
5. Search by Hydra ID and open the direct detail URL.
6. Link two different Candidate records and confirm both appear and lifecycle becomes Candidate.
7. Remove `view_person` and confirm both list and direct detail return 403.
8. Remove `recruitment.view_candidate` and confirm the link endpoint returns 403.

Automated in-app browser attachment was unavailable during TASK-1 verification. The responsive breakpoint and all page templates are covered by render/integration tests, but step 3 remains an explicit manual visual check before accepting the slice.

## Verification evidence

Verified on PostgreSQL 17.2 and CPython 3.11.9:

- `python manage.py test` discovered and passed all 14 tests, including model/service behavior, direct-URL denials and rendering every TASK-1 page;
- the test database was created and destroyed successfully with Horilla schedulers disabled for the test command;
- `python manage.py check` reported no issues;
- `python manage.py makemigrations --check --dry-run` reported no changes;
- `python manage.py migrate --check` succeeded;
- `pip check`, Python compilation and `git diff --check` succeeded;
- the local server returned HTTP 200 from `/health/`.

## Known limitations and next task

- Person visibility is organization-scoped. A newly created, never-assigned Person remains visible only to its creator until its first assignment.
- Duplicate detection and merge policy are not part of this smallest slice.
- Employee linking is stored but intentionally not exposed as a manual UI action; the later idempotent conversion service will own it.
- Existing Candidate records are not automatically backfilled. Operators may link them explicitly after the scope model is available.
- User-facing strings are translation-ready, but locale catalogs have not yet been populated.

Next: extend recruitment without weakening the shared Person and organization selectors.
