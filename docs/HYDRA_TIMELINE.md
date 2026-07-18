# Hydra Person timeline and audit boundary

## Decision

TASK-008 is implemented as **REUSE + WRAP**, not as a second writable event
store.

- `django-auditlog` remains the technical model-change audit already supplied by
  legacy HR platform;
- explicit Hydra status histories, lifecycle events, authority events and access
  logs remain the authoritative immutable business facts;
- `hydra_people.timeline` composes a read-only, user-facing Person timeline from
  those sources.

Creating another table and dual-writing every domain event would add a new
failure mode: the business action could succeed while the duplicate timeline
row was missing, or a backfill could diverge from its source. The projection
therefore copies neither source payloads nor personal values and needs no data
migration or backfill.

## Sources

The timeline currently composes:

- safe create/update labels from `auditlog.LogEntry` for Person;
- Person-to-Candidate application links;
- controlled Candidate Stage transitions, without free-text reasons;
- immutable Employee conversion evidence;
- effective organization assignments and reasoned end/revoke events;
- Arrival status and controlled onboarding-handoff events;
- Housing reservation, assignment, move, cancellation and end events;
- Legalization status, responsibility/deputy, authority and renewal events;
- authorized private-document access/lifecycle actions.
- reviewed canonical Person merges, with the preserved source Hydra ID but no
  copied Person field values.

Automation delivery attempts and raw SMTP payloads are deliberately excluded
from the human timeline. They remain available in their scoped operational
evidence and maintenance health checks.

## Authorization and confidentiality

The aggregate first proves current `view_person` plus effective Person scope.
Every source then checks its own model permission and, where the domain is
narrower than Person scope, its own selector:

- Recruitment remains limited to visible application companies;
- organization assignment facts require Team and assignment access;
- Arrival remains limited to visible destination Locations;
- Housing remains limited to visible facilities/Locations;
- Legalization and document facts require their dedicated history/access-log
  permissions.

Out-of-scope Person access returns 404 in the view and the standalone aggregate
returns no items. The display object exposes only category, safe label,
non-sensitive transition/context, timestamp and actor. It never exposes
`LogEntry.changes`, serialized audit payloads, document numbers, references,
file names, document contents, email payloads or event snapshots.

## Performance

The response is capped at 200 newest items. Every source query is also bounded
before the in-memory merge, so event volume does not create an N+1 query path.
Organization scope resolution was reduced from five dimension queries to one
row projection. A test with every source permission enforces at most 20 queries
for the timeline selector, independent of the number of returned events.

## UI

The Person detail uses a semantic ordered list with an accessible heading and
timestamps. Long content wraps, and the timestamp/category header becomes a
vertical stack below 768 px. Source-specific detailed histories remain on their
existing authorized screens; the aggregate is an orientation layer, not an
editing surface.

## Automated verification

Focused PostgreSQL coverage contains seven tests for:

- composition and deterministic newest-first order;
- source permission composition;
- cross-scope empty/404 behavior;
- omission of raw audit payload values;
- the fail-safe 200-item limit;
- a source-count-independent query ceiling;
- responsive timeline markup on the Person detail.

The combined organization-scope and timeline run passes 20/20. No model or data
migration is required.

## Browser verification

The real local Django/PostgreSQL stack was verified with the scoped
`hydra-qa` operator. The Person detail composed 11 newest-first facts from
Recruitment, Person, Arrival, Employment, Organization and Housing. At both the
default 1280 x 720 viewport and 390 x 844, the timeline stayed inside the
document width with no horizontal overflow. The mobile card measured 350.4 px
inside a 380 px document viewport. Browser logs contained no warnings or
errors. A check scoped to the Timeline region confirmed that it contained no
email address, phone number, `changes` marker or `serialized_data` marker.

## Manual verification

1. Open one Person with application, organization, Arrival, Housing,
   Legalization and document history; compare each timeline fact with its source
   screen.
2. Remove one source-history permission and confirm only that category
   disappears.
3. Repeat with a user from another Team/Location and confirm the direct Person
   URL is 404.
4. Inspect at desktop width and 390 x 844; confirm timestamps and long labels
   wrap without horizontal overflow.
5. Confirm the page source contains no serialized audit changes, document
   number, original filename, SMTP payload or event snapshot.

## Next production dependency

Privileged duplicate comparison/merge is implemented and contributes an
append-only safe fact from `PersonMergeEvent`. Logical private-document
types/version chains and fixed-field Legalization policy dictionaries are also
complete. The next dependency-safe work is universal tasks and notification
integration (TASK-017).
