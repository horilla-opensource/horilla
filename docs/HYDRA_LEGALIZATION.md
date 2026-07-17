# Hydra legalization MVP — TASK-2

## Status and audit decision

Implemented on 2026-07-14 as the smallest complete legalization vertical slice, hardened on 2026-07-15 with durable reminders, scoped escalation, retryable delivery and automatic expiry, extended on 2026-07-16 with evidence-backed authority correspondence, explicit renewal lineage, a scoped workload queue, audited permanent responsibility transfer and time-bounded case deputies, and completed for TASK-014 on 2026-07-17 with scoped fixed-field configuration, immutable case policy snapshots and fail-closed legacy adoption.

The required Horilla inspection found employee and candidate document-request models with simple request/approve/reject states, issue/expiry dates and generic media delivery. Horilla has no pre-employment legalization case, responsible operator, controlled workflow or Person-scoped deadline view.

The implementation decision is:

- **NEW MODULE** for `hydra_legalization` and its domain workflow;
- **REUSE** `hydra_people.Person`, Django users/permissions and current organization scope;
- **WRAP** `hydra_documents.PrivateDocument` through an authorized case link;
- **EXTEND + WRAP** the existing closed legalization graph with Company/global procedure, normalized status, document-requirement and approved-authority configuration;
- snapshot selected rules per case instead of adding a generic workflow engine;
- do not extend Horilla employee/candidate document status into a legalization workflow;
- leave the existing Horilla document-request screens and schema operational.

## Complete vertical slice

The server-rendered workspace at `/hydra/legalization/` provides:

- a searchable and status-filterable list of cases in the actor's current Person scope;
- creation from a scoped Person profile;
- Company, configured procedure, case classifier, responsible operator, reference, deadline, validity period and notes;
- scoped configuration screens for procedures, enabled core statuses, document requirements and approved authority/channel dictionaries;
- explicit status transitions with append-only history;
- linking existing Person-owned private documents without copying files or exposing storage keys;
- append-only recording of submission, assigned reference, information request/response and approval/rejection, each backed by a scanned private document;
- creation of a clean successor case from an approved or previously approved case and explicit, append-only linking of verified historical renewals;
- a permissioned active-workload queue filtered by responsible user, status and attention state;
- dedicated permanent responsibility transfer with a mandatory reason and append-only audit;
- explicit case deputies with bounded effective dates, current Person scope and revocation history;
- authorized download through the existing audited private-document endpoint;
- desktop and mobile Hydra navigation.

No generic workflow framework, SPA or microservice was added. The production-safe manual authority register is implemented; no unsupported immigration-office API connector is claimed.

## Domain model

`LegalizationCase` belongs to exactly one canonical Person, Company, configured procedure and responsible Django user. Work permit, temporary residence, visa and other remain stable classifiers used by the reviewed core graph; the operator selects an active global or case-Company procedure.

The status graph is intentionally closed:

```text
Draft -> Collecting documents -> Submitted -> Approved -> Expired -> Closed
   |              |                 |  \-> Rejected -> Closed
   |              |                 \-> Additional information -> Submitted/Rejected
   \--------------\-----------------------------------------------> Closed
```

Direct status field editing is excluded from forms. Internal Draft/Collecting/Closed/Expired changes use `transition_legalization_case()`. External transitions are no longer accepted through that generic service: they must use `record_legalization_authority_event()` with documentary evidence. Both services lock the case, verify the requested edge, validate domain dates and write the case plus `LegalizationStatusHistory` in one transaction. Closed transitions require a reason. Approved cases require both validity dates; expired cases require a reached validity end date.

## Configurable policy and immutable snapshots

`LegalizationProcedureType`, `LegalizationProcedureStatus`, `LegalizationProcedureRequirement` and `LegalizationAuthority` are explicit fixed-field dictionaries. A `NULL` Company denotes a superuser-maintained global row; Company rows are visible and mutable only inside the actor's current organization scope. Procedures define their stable classifier, deadline defaults, renewal lead time, enabled normalized core statuses, approved authorities and required private-document types at exact target statuses. Mandatory graph statuses cannot be disabled, cross-Company authorities/document types are rejected, and configuration is deactivated rather than hard-deleted.

Creating a case locks the Person, procedure, status, requirement and authority rows, rechecks the selected Company against the Person's effective assignments/applications, and stores the complete policy in `procedure_snapshot`. The snapshot includes the case Company, procedure identity/name/classifier, enabled status labels, requirements and exact authority names/channels. Company, procedure, classifier and snapshot cannot later be changed through model or queryset updates. Configuration changes append `LegalizationConfigurationEvent` and affect future cases only.

The core graph remains code-reviewed rather than data-programmable. Configuration may label and enable its supported normalized states, declare evidence requirements and approved authorities, but it cannot create arbitrary executable rules or bypass the service transition map.

## Authority correspondence and evidence

`LegalizationAuthorityEvent` is an append-only fact for:

- submission to the authority;
- later assignment or correction of an authority reference;
- a request for additional information and its response deadline;
- the submitted response;
- an approving or rejecting decision.

Every event records its external date, approved authority identity, the exact authority name/channel policy from the case snapshot, channel, optional reference, responsible actor, entry time, exact evidence-document SHA-256 snapshot and an idempotency key. A later authority rename or channel change cannot rewrite or change the policy of an existing case. Approval stores the validity snapshot; an information request stores its response deadline; rejection requires details. Database constraints enforce these shapes.

The service locks the case before the evidence row, rechecks current permissions and Person/Candidate scope, requires the actor to be the current responsible operator, a currently effective explicitly notified deputy, or an explicit superuser, rejects future or out-of-order facts and accepts only an already scanned, non-deleted private document. A manager who is neither owner nor deputy must use the audited permanent transfer before taking over correspondence. A repeated identical idempotency key returns the existing event; reuse with changed data is rejected. The event, case status/deadline/validity, status history and case-document link commit or roll back together.

After submission, case type, reference, deadline and validity can no longer be silently edited through the ordinary case form. Reference/deadline/validity changes must be represented by an authority event. If the underlying evidence file later becomes unavailable under retention policy, the event and its digest remain visible in the scoped audit timeline while no download link is rendered.

History rows are append-only through model/queryset APIs, read-only in admin and protect their case/actor foreign keys. Creation itself records an initial transition into Draft.

## Renewal lineage and legacy data

`LegalizationRenewalLink` represents one directed predecessor-to-successor edge. Both ends are one-to-one, protected foreign keys, so a case has at most one direct predecessor and one direct successor and an established chain cannot be silently rewritten or deleted. The pair must belong to the same Person and Company and use the same configured procedure; the predecessor must be older and must be approved, expired or have an append-only approval fact in its status history.

Starting a renewal locks the Person and predecessor, rechecks current scope and ownership, rejects another active case of the same Person/Company/procedure and creates a new Draft case plus its initial history and lineage edge in one transaction. The successor is assigned to the actor and receives a fresh snapshot of that same procedure. Authority reference, validity, evidence and old notes are deliberately not copied as if they were current facts. A repeated request returns the existing successor.

Existing historical cases are never linked by a heuristic migration. An authorized operator may select an older eligible predecessor for a successor they currently own and must record a normalized backfill reason. The service locks the Person and both cases in deterministic order, checks both scopes and all lineage rules, and makes an identical retry idempotent. Created and manually verified links are append-only and retain their actor, source, reason and creation time.

Active-case uniqueness is enforced by the supported creation services under the Person row lock and by a conditional database constraint for Person/Company/procedure. Deployment readiness also detects duplicate active groups, malformed procedure snapshots and authority events whose immutable snapshots do not match their configured identity or channel policy.

## Responsibility and deadlines

The responsible operator must be active, have both legalization and Person read permissions, and currently see the Person through Hydra scope. Assigning a new case to someone other than oneself requires `assign_legalizationcase`. Responsibility is removed from the ordinary edit form: a later owner change can only use `reassign_legalization_case()`, requires `change_legalizationcase` plus `assign_legalizationcase`, a normalized reason, the target's current Person scope, a Person/case lock and one atomic update plus `LegalizationWorkEvent`. An identical retry is a no-op. The transfer immediately invalidates every current or scheduled deputy for that case and records a separate revocation fact for each.

`LegalizationCaseDelegation` is case-specific so it can never grant access to unrelated cases. The current owner (or explicit superuser) may appoint one fully permissioned operator for a future/current inclusive date range of at most 90 calendar days. The service locks Person, case and existing windows, rejects overlap, self-delegation, past starts, excessive duration, insufficient permissions and missing deputy Person scope. A deputy never inherits the owner's scope: every read and write still passes through the deputy's own `people_for_user()` result. Expired rows remain as history; explicit revocation is narrowing-only, reasoned and audited. Horilla leave is not used to infer or silently create access.

Owner-or-current-deputy authority is now rechecked inside case edit, status transition, document linking, authority correspondence and renewal services. Managers retain the dedicated audited transfer path. The server-rendered `/hydra/legalization/workload/` queue is separately gated by `view_legalizationworkload`, contains only the actor's current Person scope, defaults to active work and exposes owner, deputy, overdue/due-soon/no-deadline filters without automatic load balancing.

A deadline may be in the past because overdue work must remain representable. Non-terminal cases with a past deadline are marked **Overdue** in list/detail views. Validity is separate from the operational deadline.

The single-owner maintenance worker generates deadline reminders at the nearest crossed configured threshold (defaults: 30, 7, and 1 day) and approved-validity reminders at 90, 30, and 7 days. A missed cycle catches up at the nearest applicable threshold without replaying older reminders. The unique event key includes the case, event type, date snapshot, threshold, and recipient, so reruns are idempotent and a changed deadline or responsible operator creates the correct new fact.

The validity end date is inclusive. An approved case becomes Expired only when `valid_until` is earlier than the worker's current date. Automatic expiry locks the case, changes its status, and writes one append-only history row with `source=system` and no human actor. Notification failure cannot roll back the expiry.

## Durable notifications and scoped escalation

`LegalizationAutomationEvent` is the durable notification outbox and audit fact for deadline reminders, overdue escalation, validity reminders, and automatic expiry. Its case/date/type/recipient facts are append-only; only bounded delivery metadata can change. Failed delivery stores only an exception-class code and is retried up to `HYDRA_NOTIFICATION_MAX_ATTEMPTS`.

`LegalizationWorkEvent` is the separate append-only fact/outbox for initial assignment, permanent transfer, deputy creation and deputy revocation. Migration backfill records a system baseline for pre-existing cases without fabricating a historical human actor and sends no retrospective notification. New events notify the new owner or deputy with a PII-free verb after commit; delivery rechecks active account, Person scope and current responsibility/delegation. A stale create/transfer event becomes `not_applicable`; failures retain only a bounded exception-class code and are retried by the single-owner maintenance worker.

Routine reminders go only to the current responsible operator. Overdue and automatic-expiry events also go to active users with `receive_legalization_escalations`, `view_legalizationcase`, `view_person`, and current Person scope. Django superusers remain the explicit administrative bypass. Delivery rechecks current permission, Person scope, and responsibility; stale recipients become `not_applicable` and receive no notification. Verbs contain no Person name, reference number, document data, or other personal data.

Automatic delivery is owned by `run_hydra_maintenance`. Operators can run one bounded diagnostic/backfill cycle for today or a past date and can recover one exhausted event after fixing the backend:

```text
python manage.py run_legalization_automation --limit 100
python manage.py run_legalization_automation --date 2026-07-15 --limit 100
python manage.py dispatch_legalization_notifications --event-uuid <event-uuid>
python manage.py dispatch_legalization_work_notifications --event-uuid <event-uuid>
```

Future diagnostic dates are rejected.

## Authorization boundary

Every list/detail query passes through `legalization_cases_for_user()`, which intersects `view_legalizationcase` with `people_for_user()`. The selected-company session value is not used. Out-of-scope direct UUIDs return HTTP 404.

Writes repeat authorization inside transactional services:

- configuration read: view permissions for procedure, authority and requirement plus current Company scope; global rows are read-only outside superuser;
- configuration write: matching add/change permissions, locked service validation, current Company scope and an append-only configuration event; global writes require superuser;
- create: `add_legalizationcase`, case/procedure/authority view permissions, `view_person`, current Person scope and an explicit Company shared by the actor and Person;
- edit: `change_legalizationcase`, case view/scope and current owner/deputy authority; the owner field cannot be changed here;
- permanent transfer: `change_legalizationcase`, `assign_legalizationcase`, case/Person view, current actor scope, valid target scope and a mandatory reason;
- deputy create/revoke: `view_legalizationcasedelegation`, `manage_legalizationdelegation`, current owner authority, bounded dates, valid deputy permission set and both users' current Person scope;
- workload queue: `view_legalizationworkload`, case view and current actor Person scope;
- status: `transition_legalizationcase`, case view/scope and current owner/deputy authority;
- authority correspondence: current owner/deputy authority (or superuser), `record_legalizationauthorityevent`, authority/event/case views, private-document view, current case/document scope, an authority UUID present in the immutable case policy with an allowed snapshotted channel, and a downloadable scanned evidence file;
- start renewal: current owner/deputy authority (or superuser), `add_legalizationcase`, `view_legalizationrenewallink`, `create_legalizationrenewallink`, case/Person view and current Person scope;
- link an existing renewal: current successor owner/deputy authority (or superuser), both renewal-link permissions, case view and current scope for both cases;
- document link: `link_privatedocument`, `view_privatedocument`, case view, current owner/deputy authority, Person match and current Candidate/Person scope.

Superuser remains Django's explicit administrative bypass. Admin registrations are read-only and their querysets/object views apply the same Person scope, so staff access cannot bypass services or reveal another team's case through a direct admin URL.

## Private documents

`LegalizationCaseDocument` links a case to one existing `PrivateDocument` with a role: identity evidence, application, decision or other. A database uniqueness constraint prevents duplicate links.

The service requires the document Person to match the case Person, requires its Candidate application to remain visible to the actor, and excludes deleted, unscanned or purged files. Detail templates show only the authorized download route; they never render `.url`, `/media/` or the opaque storage key. Linking the same document twice is idempotent.

## Migration and tests

`hydra_legalization/migrations/0001_initial.py` creates:

- `LegalizationCase` and query indexes for Person/status, responsible/status and deadline;
- append-only `LegalizationStatusHistory` with a case/time index;
- `LegalizationCaseDocument` with a unique case/document constraint;
- action permissions for assignment, transitions and private-document linking.

`0002_legalizationautomationevent_and_more.py` adds the durable automation event, scoped escalation permission, system/user history source, notification indexes, uniqueness, delivery consistency, threshold consistency, and history actor/source constraints. `hydra_ops.0002` adds the worker's last successful legalization-run timestamp.

`0003_legalizationauthorityevent_and_more.py` adds the append-only authority-event table, scoped view/record permissions, case/date index, per-case idempotency uniqueness and database constraints for response-deadline, validity and reference shapes. Before rollout, the legalization-operator role must receive `view_legalizationauthorityevent` and `record_legalizationauthorityevent`; external status changes intentionally stop using the generic transition permission.

`0004_legalizationrenewallink_and_more.py` adds the append-only one-predecessor/one-successor lineage table, protected relationships, source/reason shape constraints and `view_legalizationrenewallink` plus `create_legalizationrenewallink`. The legalization-operator role must receive both permissions before renewal actions are exposed. There is intentionally no automatic backfill; historical edges require operator verification and a reason after the active-case readiness check is clean.

`0005_alter_legalizationcase_options_and_more.py` adds case-specific delegation, its bounded-date/revocation constraints and indexes, the append-only responsibility/delegation event outbox, delivery constraints and permissions `view_legalizationworkload`, `view_legalizationcasedelegation`, `manage_legalizationdelegation`, and `view_legalizationworkevent`. Its data migration creates one non-notifying system responsibility baseline for every existing case. `0006` narrows the delivery constraint correctly so a previously eligible recipient may become `not_applicable` without erasing the immutable recipient fact. Before rollout, the responsibility manager and operator roles must receive only the new permissions approved in the signed matrix.

`0007_legalization_configuration_stage.py` creates the fixed-field dictionaries, configuration audit, nullable case/event foreign keys and snapshots. It seeds the four global classifier procedures and normalized status rows, derives authorities only from existing recorded authority facts, infers exactly one Company from effective assignment/application evidence, and aborts rather than guessing an ambiguous Company. `0008` makes case Company/procedure and event authority configuration non-null after backfill. `0009` adds the reasoned legacy-policy adoption audit shape and marks only active legacy cases whose authority cannot be inferred as `legacy_authority_policy_pending`; terminal cases do not require an invented authority.

After deploying the migrations, configure a real global or matching Company authority before opening new cases. Readiness intentionally remains red for every pending active legacy case. Resolve each one only after source verification:

```powershell
python manage.py adopt_legacy_legalization_policy `
  --case <case-uuid> `
  --authority <authority-uuid> `
  --actor <superuser-username> `
  --reason "Verified against the legacy case register"
```

The command locks the case and authority, accepts only active global/same-Company authorities, changes only a migration-marked empty authority policy once, and appends an immutable before/after event with the mandatory reason. It cannot be used to rewrite ordinary case snapshots.

Focused tests cover:

- HTTP 403 without the model permission;
- list/search and direct-UUID denial across team scope;
- normalized creation and initial history;
- rejection of an inaccessible responsible operator;
- valid and invalid status paths, required reasons and transactional rollback;
- approval validity requirements;
- append-only history;
- assignment permission enforcement;
- same-Person/scoped/idempotent private-document linking;
- absence of storage/media paths in case detail;
- continued operation of Horilla's original document-request view.
- atomic/idempotent deputy creation, window overlap and 90-day limit rejection;
- full operator permission and independent Person-scope validation for deputies;
- delegated write authority only during the effective window and immediate loss after revocation;
- permanent transfer, automatic revocation of deputy windows and old-owner write denial;
- append-only work facts, durable failure/retry and stale-recipient suppression;
- permissioned/scoped workload filters and cross-case delegation-ID denial;
- readiness checks for overlapping windows, stale principals and missing responsibility baselines.
- Company-scoped configuration UI, direct cross-Company denial and append-only configuration evidence;
- complete future-only case policy snapshots across procedure/authority changes;
- target-status document requirements and authority-channel enforcement;
- one-time superuser-only legacy policy adoption and post-adoption operation;
- rejection of configuration hard delete and malformed policy/status snapshots.

The 2026-07-15 focused PostgreSQL 17 automation/worker run passed 40/40 tests, followed by a 231/231 full Django regression. The 2026-07-16 authority workflow suite passed 24/24, the renewal-expanded legalization suite passed 33/33, the responsibility-continuity additions passed 11/11 and the maintenance/readiness set passed 24/24. On 2026-07-17 the configurable legalization module passed 56/56, the affected coordinator panel passed 10/10 on a fresh database, and the complete clean-database PostgreSQL 17 regression passed 394/394. Coverage includes scoped fixed-field configuration and audit, future-only procedure/authority snapshots, requirements, legacy adoption, idempotent atomic submission and renewal creation, the closed request/response/decision graph, evidence digests, duplicate-active prevention/readiness, delegation, responsibility delivery, database constraints, rollback, append-only protection, direct-scope denial, admin scoping and continued visibility of audit facts when a file becomes unavailable.

Browser QA used the real local Django/PostgreSQL stack and scoped `hydra-qa` account. The operator opened a Person profile, created `QA-LEG-2026-001`, linked the existing audited private PDF and performed Draft -> Collecting documents with reason `Documents requested`. Database inspection confirmed two ordered history events and the identity-document link. The detail rendered one active Legalization navigation item, no `/media/` link and no storage key.

At the default 762 px browser surface the detail had no horizontal overflow. At 390 x 844 px the document measured 380 px, details collapsed to one 316.8 px column, navigation used two columns, the private-document download and transition form remained available, and there was no horizontal overflow. The mobile list converted its case row to block/card layout and retained one active navigation item.

TASK-014 browser QA then used the real local Django/PostgreSQL stack and the superuser-only `hydra-browser-admin` fixture to inspect the Company-scoped configuration register plus the create-authority and create-procedure forms. The register rendered the local approved authority, all four global procedures and their eight fixed status rows; the procedure form kept all eight safe-core statuses enabled. At 1440 x 900 and 390 x 844 there was no document or element-level horizontal overflow. The checked pages also had no browser warning/error logs, duplicate DOM identifiers or labels targeting missing controls.

## Manual verification

1. Grant an operator `view_person`, case/procedure/authority views, `add_legalizationcase`, `change_legalizationcase`, `transition_legalizationcase`, authority-event, renewal-link and private-document permissions plus a current Hydra scope grant. Grant approved continuity managers `assign_legalizationcase`, workload/delegation/work-event permissions as required by the signed matrix. Grant Company policy maintainers only the approved procedure/authority/requirement add/change permissions plus private-document-type view.
2. Open `/hydra/legalization/configuration/`. Create a Company authority, procedure and identity-document requirement before Submitted. Confirm another Company's rows are absent and direct edit returns 404.
3. Create a case with that procedure, then rename the authority/change its channels and requirement. Confirm the existing case and authority event retain the original snapshots while a new case receives the revised policy. Confirm wrong evidence type/channel is rejected atomically.
4. If readiness reports a migration-marked legacy authority policy, verify the source register and run the documented adoption command as a superuser. Confirm a second adoption is rejected and the immutable event contains before/after snapshots and reason.
5. Open a visible Person and choose **Start legalization**.
6. Create a work-permit case and progress it to Collecting documents.
7. Upload and scan a submission receipt, then record **Submitted to authority**. Confirm the event, digest-backed evidence link, status history and case status appear together.
8. Record an information request with a response deadline, its response, and an approval. Attempt approval without validity dates and confirm validation blocks the whole operation.
9. Repeat the same POST/idempotency key and confirm no duplicate event or status history is created.
10. Start a renewal from the approved case. Confirm a new Draft owned by the actor, the same Company/procedure with a fresh policy snapshot, an explicit forward/back link, no copied reference/validity/evidence, and an idempotent repeated request.
11. On two pre-existing test cases, create a historical link with a reason. Confirm wrong Person/Company/procedure/order, another active same-procedure case and an out-of-scope predecessor are rejected.
12. Link an existing private document and confirm the page contains only the authorized download link.
13. Try a case, evidence document, renewal link and read-only admin object belonging to another team using direct identifiers and confirm no record is rendered.
14. Appoint a same-scope fully permissioned deputy for 14 days. Confirm the deputy can operate the case but sees no case outside their own Person scope. Try overlap, a past start, 91 days and an incomplete deputy role; confirm each is rejected.
15. Revoke the deputy and confirm immediate write denial plus the immutable revocation event. Create another delegation, transfer responsibility permanently, and confirm the transfer atomically revokes it and the old owner can no longer write.
16. Open `/hydra/legalization/workload/`; verify owner/status/overdue/due-soon/no-deadline filters and direct cross-team URL denial at desktop and 390 px.
17. Run `python manage.py hydra_readiness --json`; confirm active uniqueness, delegation windows/principals, responsibility baseline, `legalization_policy_snapshots` and `legalization_authority_snapshots` pass. Correct source data explicitly if any fail.
18. Run one maintenance cycle on non-production cases at the 7-day, overdue, last-valid-day, and day-after-validity boundaries. Confirm unique events, scoped recipients, system history, responsibility notification counters, and retry behavior.
19. Remove a recipient's scope, responsibility or delegation before delivery and confirm the event becomes `not_applicable` without a notification.
20. Repeat configuration, list, workload, detail, transfer, delegation, renewal and authority form checks at a viewport no wider than 390 px.

## Known limitations and next task

- Workload assignment remains an explicit accountable decision; Hydra does not silently rebalance cases or infer deputies from Horilla leave. Bulk transfer across multiple cases is not exposed in this slice.
- Renewal lineage is explicit and safe for new work; legacy chains remain unlinked until an operator verifies each edge and records a reason.
- Legacy authority policy adoption is deliberately a one-time superuser deployment action, not an ordinary case-edit capability; source verification remains an accountable operational step.
- The audited manual authority workflow is complete. Automatic synchronization remains unavailable until a specific authority exposes an approved API, authentication method, rate/error contract and data-processing agreement; no screen-scraping or fabricated connector is used.
- Malware scanning/quarantine and retention/legal hold are implemented in `HYDRA_PRIVATE_DOCUMENTS.md`; encrypted target-host storage, signature-freshness monitoring, and scheduled purge evidence remain deployment gates.
- Attendance reconciliation, arrival-deadline automation and the controlled onboarding handoff are implemented; TASK-017 universal tasks/notification integration is the next dependency-safe product task. Target-host, external-email, encrypted-storage, malware-scanner and restore-evidence gates remain tracked in the staging/onboarding documents.
