# Hydra onboarding content and automatic assignments

## Scope and reuse decision

TASK-024/025 use **EXTEND + WRAP + NEW MODULE**:

- Horilla remains authoritative for candidate onboarding stages, onboarding tasks,
  candidate-task state and its token portal;
- `hydra_arrivals.OnboardingHandoff` remains the controlled bridge from a confirmed
  arrival to Horilla onboarding;
- `hydra_onboarding` owns only versioned internal learning content, deterministic
  assignment rules and durable learning evidence.

There is no parallel candidate-onboarding workflow and no generic rule engine.

## Content invariants

`Course` is Company-scoped and may have many language-specific `CourseVersion`
rows. A version is editable only while it is a draft. Publication:

1. locks the version, its lessons, quiz, questions and options;
2. validates at least one lesson and, when a quiz exists, at least one question,
   at least two answers and exactly one correct answer per question;
3. records publisher and publication time;
4. stores a SHA-256 fingerprint of the normalized published payload.

Published content cannot be edited through services, direct model saves or the
read-only admin. Corrections require a new monotonically numbered version. An
assignment snapshots the exact published version and fingerprint; later drafts or
publications cannot change the assigned material.

## Assignment rules

`CourseAssignmentRule` is an explicit fixed-field rule. It is scoped to one
Company and course and may narrow by:

- Location;
- Department;
- Team;
- preferred language;
- Horilla worker/employee type.

Blank dimensions mean "any". Matching uses the current effective Person
assignment, with the confirmed handoff destination as the arrival-time Location
fallback. Rules are ordered deterministically by priority, specificity and stable
identifier. The selected version prefers the requested language and then the
course default language. Only a published version may be assigned.

Automatic application is idempotent through the Person/course uniqueness boundary
and database conflict handling. Manual assignment uses the same version snapshot,
scope validation and immutable event history. A confirmed arrival applies matching
rules after the existing Horilla handoff has been reconciled.

## Completion evidence

An assignment progresses through `assigned`, `in_progress` and `completed` using
locked services. Quiz attempts and the final confirmation are append-only. A quiz,
when configured, must be passed within its attempt limit before completion.
Confirmation preserves the content fingerprint and statement used at that time.

Every assignment has a monotonic append-only event stream covering assignment,
start, quiz submission and completion. The same safe, permission-filtered events
appear in the Person timeline. Assignment, attempt, confirmation and event rows are
not hard-deletable through the service-managed admin.

## Authorization and operations

All lists, forms and direct-object views intersect Django permissions with explicit
Company/Person scope. Content publication, rule configuration, assignment, start,
quiz and confirmation have separate permissions. A superuser does not weaken the
domain integrity rules.

Readiness verifies published fingerprints and quiz structure, active rule targets,
assignment snapshots and completion evidence. The onboarding migration is pinned
in the reviewed migration manifest. No recurring worker is required: rules run on
the confirmed-arrival handoff or an explicit scoped operator action.

## Verification

The focused PostgreSQL suite covers publication validation and immutability,
version numbering, all five rule dimensions, priority/specificity, language
fallback, idempotency, assignment lifecycle, attempt limits, confirmation,
scope/direct URLs, Person integration, handoff integration and readiness corruption.

Browser QA on 2026-07-17 created and published a Polish course through the UI,
created an automatic rule, manually assigned the exact published version, started
the course, passed its quiz, confirmed completion and verified the Person timeline.
The same fingerprint remained visible from publication through completion. Mobile
390 x 844 dashboard and assignment views were inspected and the browser console had
no errors.
