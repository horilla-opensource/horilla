# Hydra Person duplicate review and canonical merge

## Decision

TASK-012 is implemented as **EXTEND + WRAP** around the canonical
`hydra_people.Person`. Hydra stores privacy-minimising deterministic
fingerprints and review suggestions, but it never auto-merges people. A merge
is an explicit, privileged and reasoned operation with a conflict-checked
preview and one PostgreSQL transaction.

The source Person row is retained as an immutable inactive alias. Its UUID and
Hydra ID are never reassigned or deleted, direct source URLs redirect to the
canonical Person, and list search resolves both current and preserved Hydra
IDs. New operational work cannot be attached to an alias.

## Deterministic suggestions

The matcher normalizes text with Unicode NFKC, case folding and whitespace
collapse, normalizes email the same way, and compares phone/messenger values by
digits. SHA-256 fingerprints select candidates efficiently; normalized source
values are compared again before a suggestion is accepted.

| Reason | Score |
|---|---:|
| same first name, last name, date of birth and citizenship | 100 |
| same passport name and date of birth | 90 |
| same email | 65 |
| same phone or messenger number | 60 |

Multiple reasons add five points each after the strongest reason, capped at
100. There is deliberately no fuzzy transliteration, approximate name match or
passport-number heuristic. A Person save refreshes its deterministic pairs;
operators can also run:

```text
python manage.py refresh_person_duplicates
python manage.py refresh_person_duplicates --person-id <database-id>
```

Dismissed suggestions retain the operator and a required reason of at least ten
characters. Open suggestions become stale when the records stop matching and
may reopen if the same deterministic pair matches again. Detection never calls
the merge service.

## Authorization and scope

| Action | Required permissions |
|---|---|
| Review queue/comparison | `view_person`, `review_person_duplicates` and scope to both people |
| Dismiss | review permissions plus `dismiss_person_duplicate` |
| Preview/merge | review permissions plus `change_person`, `link_candidate`, `merge_person`, change scope to both people, all permissions and effective scope required by every dependent record |

Dependent-domain checks cover Recruitment, Arrivals, onboarding handoff,
organization assignments, Housing, Legalization and private/quarantined
documents. An operator cannot merge a pair merely because both Person rows are
visible: every record that would move must also be visible and editable through
its authoritative domain boundary. Out-of-scope direct URLs return 404; missing
action permissions return 403.

## Comparison and preview

The comparison requires an explicit canonical Person, a source choice for each
canonical Person field and a merge reason of at least ten characters. It shows
the exact match evidence, conflicting values and counts for every supported
dependent relation.

The server creates a signed preview that expires after 30 minutes. Its version
token covers both Person records and all controlled references. Commit locks
the suggestion, both people and references in deterministic order, rebuilds the
plan and refuses a stale token or any changed reference. The final confirmation
checkbox is mandatory.

The preview blocks a merge when:

- the suggestion is closed or either record is already an alias;
- the proposed source already has aliases;
- the pair no longer satisfies a deterministic match;
- the proposed source is Employee-backed or its application points to a
  conflicting Employee;
- both records have an application in the same Recruitment;
- active primary organization assignments overlap;
- active Housing periods overlap.

Lifecycle validation additionally prevents an application-backed Person from
remaining Prospect, an onboarding-backed Person from leaving Onboarding or
Employee, and an Employee-backed canonical Person from leaving Employee.

## Atomic merge and evidence

One transaction applies selected Person fields and reassigns these direct
references from the source to the canonical Person:

- recruitment applications;
- Arrival plans;
- onboarding handoffs;
- organization assignments;
- Housing assignments;
- Legalization cases;
- private documents;
- quarantined uploads.

`PersonMergeEvent` records the actor, reason, match evidence, field decisions,
counts and both preserved identifier sets. Each moved row receives one
append-only `PersonMergeReference`. The source becomes inactive with lifecycle
Inactive and `merged_into`, `merged_at` and `merged_by` populated. Other open
suggestions involving that source become stale. Any validation, authorization,
count or database failure rolls back the complete operation.

Candidate-import provenance (`created_person`) and Employee conversion evidence
remain historical provenance and are not rewritten. The event preserves the
identity relationship instead of making the original import or conversion
claim something that did not happen.

There is no automated undo. Correcting a reviewed merge requires a separately
designed, audited recovery procedure; operators must not edit the alias or
append-only evidence directly.

## Migration and operations

Migration `hydra_people.0005_person_duplicate_merge` adds fingerprints, alias
state, suggestions and append-only merge evidence. Its data step backfills
fingerprints and deterministic suggestions for existing active Person rows.
The reviewed migration manifest contains 63 sources after this migration.

The duplicate queue is available at `/hydra/people/duplicates/` and is linked
from the People list/detail for authorized operators. The Person timeline shows
a safe merge fact only when the operator can view merge events; preserved
source identifiers and the reason remain on the canonical Person detail under
the same scoped access boundary.

## Verification evidence

PostgreSQL coverage verifies exact and normalized suggestions, no auto-merge,
dismissal retention, all eight operational reference types, source alias
immutability, lifecycle and Employee conflicts, same-Recruitment rollback,
stale-preview rollback, missing permissions, cross-scope denial, signed
preview/commit, preserved-ID search and direct-source redirect.

The focused duplicate and shell regression passes 18/18 after the final UI
changes. The clean full regression passes 382/382. Browser verification on the
real local Django/PostgreSQL stack covered comparison, preview, confirmation,
canonical identity history, timeline evidence, source redirect and preserved-ID
search. At 1280 x 720 and 390 x 844 there was no horizontal overflow or
duplicate HTML id; the People navigation state and form labels were verified.

## Remaining boundary

TASK-012 deliberately implements deterministic review, not probabilistic data
quality scoring. Broader fuzzy/transliterated suggestions belong in the later
data-quality work and must still require human review. Merge chains and undo
remain blocked. Logical private-document types/version chains (TASK-011) and
fixed-field Legalization policy dictionaries (TASK-014) are now implemented.
The next dependency-safe work is universal tasks and notification integration
(TASK-017).
