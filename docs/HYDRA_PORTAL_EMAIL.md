# Hydra onboarding portal email outbox

## Decision and delivery contract

The onboarding portal keeps legacy HR platform's token portal and configured email backend,
but Hydra **WRAPS** delivery in a durable, domain-specific outbox. A web request
never waits for SMTP and never starts onboarding merely because an operator
clicked Send. It commits the current portal token, exact payload, verified
attachments and a `queued` audit event in one database transaction. The
single-owner maintenance process performs delivery.

SMTP has no transaction that can atomically commit both the remote send and the
Hydra database acknowledgement. Delivery is therefore **at least once**. A
process failure after the remote server accepts a message but before Hydra
records `sent` can cause the same payload and token to be retried. One
maintenance owner, row leasing and stable payload identity minimize that
window; it cannot honestly be described as exactly once without provider-side
idempotency.

## State and invariants

`hydra_arrivals.OnboardingPortalDelivery` uses these states:

```text
pending -> sending -> sent
                   -> retry -> sending
                            -> dead
pending/retry/dead -> cancelled
```

- a partial unique database constraint permits only one
  `pending`/`retry`/`sending` delivery per Candidate;
- Candidate, portal, requesting user and selected email configuration are
  protected references;
- the exact recipient, token, HTML and attachment metadata produce a SHA-256
  payload identity;
- `sending` requires a lease token and expiry; all other states forbid them;
- `sent` requires a send timestamp, while unsent states forbid it;
- duplicate web submissions reuse the active delivery and do not rotate the
  token or create another message;
- a new operator request supersedes an exhausted delivery under lock;
- a changed recipient, ineligible Candidate, used/superseded token or missing
  payload cancels delivery before SMTP and atomically revokes the current
  portal token. A successfully sent token remains valid for the portal flow.

Every transition creates an append-only `OnboardingPortalDeliveryEvent` with
opaque identifiers, state, attempt number, attachment totals and payload hash.
It never stores the Candidate name, address, token, message body or backend
exception detail. Model and queryset update/delete are rejected for events.

## Retry, recovery and onboarding

The worker claims due rows with a bounded lease, sends outside the database
transaction, and records only the exception class on failure. Retry uses capped
exponential backoff. An expired lease becomes `retry`; this is the crash
recovery path and deliberately reuses the same payload/token.

After confirmed SMTP delivery Hydra calls the existing locked
`ensure_candidate_onboarding` service. A temporary onboarding-data conflict is
recorded independently from email delivery and is reconciled in later cycles
without sending the email again. `Candidate.start_onboard`, CandidateStage and
CandidateTask therefore remain absent while SMTP is failing.

An exhausted row becomes `dead` and keeps its payload for the configured
operator-recovery window. A user with
`hydra_arrivals.retry_onboardingportaldelivery`, all queue permissions and
current Candidate scope may reset the same token/payload through the protected
admin action. Expired dead payloads become cancelled and cannot be retried; the
operator must queue a new portal link. Any unresolved `dead` row is a
maintenance error.

## Authorization and data protection

Queueing requires all of:

- `recruitment.view_recruitment`;
- `hydra_people.view_person`;
- `recruitment.view_candidate` and `recruitment.change_candidate`;
- OnboardingPortal view/add/change permissions;
- current Hydra Person/company/location/team visibility from the canonical
  linked-Candidate selector.

The hired-Candidate portal list uses the same selector. A broad legacy HR platform company
manager or `selected_company=all` does not widen Hydra scope. An unauthorized
Candidate selection is not queued.

Uploaded attachments are limited by count, per-file size and total size. Only
signature-verified PDF, JPEG and PNG are accepted, and every user upload is
scanned fail-closed through ClamAV before persistence. Generated template PDFs
are size/signature checked. A company-owned mail template can be attached only
to a Candidate application in that company; explicitly global templates remain
available. Persisted objects have opaque names in
`HYDRA_PORTAL_EMAIL_MEDIA_ROOT`, whose storage has no URL and must be outside
public `MEDIA_ROOT`. Hash and size are rechecked before every send.

Sent and cancelled payloads/files are purged immediately while metadata, hashes
and events remain. Dead payloads use bounded retention. The standard legacy HR platform
`EmailLog` is retained for compatibility but sensitive Hydra messages replace
recipient, subject and body with a non-sensitive Hydra delivery reference, so
the portal token is not copied into the legacy log.

The public link is built only from
`HYDRA_ONBOARDING_PORTAL_BASE_URL`; the HTTP Host header cannot alter it.
Staging and production readiness require an absolute HTTPS URL.

## Operations and configuration

The outbox is dispatched by every bounded maintenance cycle and updates
`MaintenanceState.last_portal_email_dispatch_at`. Worker output exposes counts,
not recipients or content. Relevant settings are:

```text
HYDRA_ONBOARDING_PORTAL_BASE_URL=https://staging.example.com/
HYDRA_PORTAL_EMAIL_MEDIA_ROOT=/var/lib/hydra/outbox
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=<secret-managed user>
EMAIL_HOST_PASSWORD=<secret-managed password>
DEFAULT_FROM_EMAIL=noreply@example.com
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_FAIL_SILENTLY=False
EMAIL_TIMEOUT=30
HYDRA_PORTAL_EMAIL_MAX_ATTEMPTS=8
HYDRA_PORTAL_EMAIL_RETRY_BASE_SECONDS=60
HYDRA_PORTAL_EMAIL_RETRY_MAX_SECONDS=3600
HYDRA_PORTAL_EMAIL_LEASE_SECONDS=120
HYDRA_PORTAL_EMAIL_DEAD_RETENTION_HOURS=72
HYDRA_PORTAL_EMAIL_MAX_ATTACHMENTS=8
HYDRA_PORTAL_EMAIL_ATTACHMENT_MAX_BYTES=10485760
HYDRA_PORTAL_EMAIL_ATTACHMENTS_TOTAL_BYTES=26214400
HYDRA_MAINTENANCE_PORTAL_EMAIL_BATCH_SIZE=25
```

Readiness bounds timeout, attempts, backoff, lease, retention, attachment
limits and batch size. The lease must be at least twice the SMTP timeout.

The web and maintenance containers share the private outbox volume. Cold
backup includes its archive; restore verification checks every retained
attachment against the database SHA-256. Quarantine remains intentionally
excluded.

## Migrations and verification

- `hydra_arrivals/0006` creates delivery, attachment and append-only event
  models, indexes and state/concurrency constraints;
- `hydra_arrivals/0007` persists the exact sender and reply-to snapshot used by
  the asynchronous worker;
- `hydra_ops/0005` records the last outbox dispatch timestamp.

Automated PostgreSQL coverage includes queue idempotency, the active-row
constraint, successful delivery, SMTP backoff, exhausted attempts, manual
retry, stale-lease recovery, scope denial, recipient change, attachment
tampering, fail-closed malware scanning, event immutability, legacy-log
redaction and onboarding reconciliation without a duplicate email. The
2026-07-16 focused outbox suite passed 21/21 and the complete Django PostgreSQL
regression passed 296/296.

## Manual staging acceptance

1. Use a non-production Candidate and the real staging SMTP account; confirm
   the request returns immediately as queued and the worker changes it to sent.
2. Confirm the received link uses the configured HTTPS origin and works once.
3. Force authentication rejection, timeout and connection refusal; verify
   capped retries, generic operator status and no onboarding rows.
4. Restore SMTP, retry an exhausted row as an in-scope authorized operator and
   confirm the same token is delivered once in the normal path.
5. Repeat as another Location's operator and confirm list, queue and retry
   denial.
6. Upload an inert PDF and the approved antivirus test artifact; confirm only
   the clean file enters private outbox storage.
7. Kill the worker after SMTP acceptance in a controlled environment and
   verify the documented at-least-once recovery behavior is understood by the
   support owner.
