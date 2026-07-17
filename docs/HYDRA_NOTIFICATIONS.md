# Hydra notification center

Full Engineering Package TASK-018 is implemented. The decision is **REUSE +
WRAP**: Horilla's `notifications.Notification` remains the in-app transport,
while `hydra_notifications` owns Hydra scope, reviewed messages, read/archive
history, user delivery preferences and durable email-delivery evidence.

## Product contract

- In-app delivery is always enabled. A user sees only their own notifications
  whose target remains visible through their current permissions and
  organization scope.
- The center supports active/unread/read/archived state, category and severity
  filters, 30-row pagination, open, read, unread, archive, restore and bounded
  batch read actions.
- Every state mutation is POST-only, CSRF-protected, recipient-scoped and
  version-checked. State changes mirror the Horilla compatibility flags and
  append an immutable sequence event.
- Email is opt-in and has a configurable minimum severity. Email contains only
  a generic sign-in prompt and the notification-center URL; it never contains a
  Person, case, task, arrival, identifier or source message.
- Browser sound is independently opt-in. Native browser push is disabled by
  policy for this release; no authenticated payload is sent to a push service.
- Inactive recipients may retain an in-app organization lifecycle fact for
  later reactivation, but email delivery becomes `not_applicable`.

## Reviewed targets and payloads

Managed notifications use a closed kind-to-target registry for organization
access, arrivals, legalization, universal tasks and onboarding handoffs. The
service resolves the authoritative Company/Person relationship, checks the
recipient's current target visibility and accepts only a safe local redirect.

The underlying Horilla row stores a fixed, reviewed, PII-free message and only
the notification-center redirect, icon and Hydra label. Detailed target URLs
remain in the protected envelope and are rechecked before open. Producers use
stable idempotency keys, so retries do not create duplicate notifications.

Legacy Horilla notifications are wrapped as `legacy` envelopes. Existing rows
are backfilled by migration and future `notify` signal rows are wrapped at
creation. Legacy redirects are accepted only when they are safe local paths;
otherwise open returns to the center. Legacy content is not forwarded to the
email outbox.

## Durable state and email delivery

`HydraNotificationEnvelope` protects notification identity, target, recipient,
scope metadata and safe redirect. It cannot be hard-deleted or directly
retargeted. `HydraNotificationStateEvent` is append-only and preserves the
created/imported/read/unread/opened/archived/restored sequence.

`HydraNotificationEmailDelivery` is a one-row durable hook per managed
notification. The single-owner maintenance worker handles
`pending -> sending -> sent`, bounded exponential retry, lease recovery,
dead-letter state and policy-driven `not_applicable`. Immediately before send
it rechecks current scope, archive state, active account, email address and the
latest preference. Persisted failures contain only a bounded exception-class
code. A deterministic Message-ID narrows the unavoidable SMTP crash window.

## Legacy Horilla hardening

The shared tray, list, count and JSON endpoints now consume recipient-scoped
Hydra selectors. Read, clear, delete/archive and sound mutations require POST;
foreign identifiers return 404 and archival replaces destructive deletion.
Actor names and external avatar-service requests were removed from notification
partials. The common Horilla login decorator now preserves `Http404` and
`PermissionDenied`, renders debug failures as HTTP 500 and never retries a
failed view. The custom 404 and 405 pages now return their real status codes.

## Configuration and operations

```text
HYDRA_NOTIFICATION_BASE_URL=https://hydra.example.test/
HYDRA_NOTIFICATION_MAX_ATTEMPTS=10
HYDRA_NOTIFICATION_EMAIL_RETRY_BASE_SECONDS=60
HYDRA_NOTIFICATION_EMAIL_RETRY_MAX_SECONDS=3600
HYDRA_NOTIFICATION_EMAIL_LEASE_SECONDS=120
HYDRA_MAINTENANCE_NOTIFICATION_EMAIL_BATCH_SIZE=25
```

Staging/production readiness requires an absolute HTTPS base URL, bounded
retry/backoff, a lease at least twice the SMTP timeout and a 1-1000 worker
batch. Domain readiness checks envelope/Horilla state parity, event sequences,
target resolution, fixed minimal payloads, recipient consistency and exhausted
email delivery.

## Verification

Focused PostgreSQL tests cover idempotent scoped creation, invalid target and
redirect rejection, cross-scope denial, PII-free payloads, recipient-only POST
mutations, optimistic state history, hard-delete protection, bounded batch
state actions, legacy wrapping, generic email content, preference/scope loss,
retry and readiness. Producer regression covers organization access, arrivals,
onboarding, legalization, tasks and maintenance dispatch. The exact 70-file
migration manifest includes both notification migrations. On PostgreSQL 17 the
focused notification/manifest suite passes 14/14, producer/maintenance
regression passes 88/88 and the clean-database project regression passes
418/418.

## Browser QA

On 2026-07-17 the local PostgreSQL-backed center was exercised through the
in-app browser with a real authenticated administrator session and three
idempotent PII-free notifications. Severity filtering returned only the urgent
row; POST read, archive, archived filtering and restore updated the visible
state and unread tray count. Browser-sound preference remained selected after a
POST/redirect/reload cycle.

That preference journey initially exposed a view-to-service argument mismatch
which returned HTTP 500. The mapping was corrected and is now covered by a
positive and stale-version view regression test before the final 418/418 clean
run.

At 390 × 844 pixels the document client and scroll widths were both 380 pixels;
the 317-pixel notification cards stayed between x=30 and x=346. Filters, card
actions and preferences remained readable and operable, and the tested page
emitted no browser console warning or error. The temporary viewport override
and local server were reset after the journey.

Target staging still requires real SMTP/monitoring evidence as part of the
existing TASK-035/036 external release gates; that does not change the
implemented TASK-018 application contract.
