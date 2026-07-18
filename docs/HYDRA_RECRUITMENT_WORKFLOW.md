# Hydra controlled recruitment workflow

## Decision

TASK-010 is implemented as **REUSE + EXTEND + WRAP**. legacy HR platform continues to own
`Recruitment`, configurable `Stage`, `Candidate`, the pipeline UI, interviews,
ratings and simple-history records. Hydra adds one directed transition contract
and one immutable business-history model around linked Candidate applications;
it does not create a second recruitment pipeline.

## Configurable transition contract

`RecruitmentStageTransitionRule` links one source Stage to one target Stage in
the same Recruitment. An active rule can require:

- a reason;
- a schedule date;
- a joining date;
- or an explicitly authorized override.

Migration `hydra_people.0004_recruitmentstagetransitionrule_and_more` seeds
directed rules between every existing pair of active stages. Adjacent forward
moves preserve the current legacy HR platform flow. Cancellation, backward and skipped
moves require a reason; entering a hired stage requires a joining date. New
Stages receive equivalent defaults through a post-save integration hook.
Configuration is editable in Django admin without deleting historical events.

## Controlled write service

`hydra_people.recruitment_workflow.transition_candidate` is the only supported
stage mutation for a Candidate linked to Person. In one PostgreSQL transaction
it:

1. locks the Candidate, target Stage and active rule;
2. requires `view_person`, `view_candidate` and `change_candidate`;
3. intersects those permissions with current Person/company/team scope;
4. rejects closed/inactive Recruitments, cross-Recruitment targets, same-stage
   moves and disabled rules;
5. validates reason/schedule/joining-date requirements and override authority;
6. updates the legacy HR platform Candidate flags and dates;
7. appends `CandidateStageTransition` with actor, source, reason, rule and a
   non-PII requirements snapshot.

An override never bypasses the reason requirement. The separate
`override_recruitment_transition` permission and the rule's `allow_override`
flag must both pass.

## Legacy-route closure

The main legacy HR platform list/kanban stage-change endpoints now route linked
applications through the same service. Unlinked legacy Candidates retain the
upstream behavior until reviewed and linked. Two defense-in-depth guards close
future bypasses for linked applications:

- direct `Candidate.save()` rejects an uncontrolled stage change;
- legacy HR platform's bulk-update signal rejects `QuerySet.update(stage_id=...)`.

Changing the legacy `canceled` checkbox is also rejected for a linked
application; the operator uses the reasoned transition form instead. Reordering
within the same Stage remains a sequence-only operation and is not fabricated
as a business transition.

## History, timeline and confidentiality

`CandidateStageTransition` is append-only: instance/queryset update and delete
raise before touching the database, while all foreign keys use `PROTECT`. The
Hydra application detail shows at most 50 newest events to users with
`view_candidatestagetransition`.

The Person timeline consumes the same history only when that source permission
and Candidate/Person scope pass. It exposes the safe from/to Stage labels,
timestamp and actor. It deliberately excludes the reason and requirements JSON,
so free-text decisions cannot leak into the aggregate.

## UI

The scoped application detail exposes `Change stage` only to Candidate editors
with an active rule. The server-rendered form lists only enabled targets for the
current Stage and accepts the configured evidence. History reuses the semantic,
wrapping Hydra timeline component, including its sub-768 px vertical metadata
layout. Direct URLs for applications outside Person scope return 404.

## Automated verification

Eleven PostgreSQL tests cover:

- seeded adjacent/cancellation/hiring defaults;
- a successful atomic transition and immutable event;
- rejected missing requirements without a partial write;
- authorized override plus reason redaction from Person timeline;
- missing permission and cross-scope denial;
- cross-Recruitment and disabled-rule denial;
- direct-save and bulk-update bypass prevention;
- a reasoned cancellation to the exact configured target;
- scoped transition form/history rendering;
- the existing legacy HR platform kanban route using the same service;
- ordinary hired transition with a joining date.

The focused workflow run passes 11/11, the affected onboarding-handoff and
portal-email regression passes 35/35, and the full clean PostgreSQL regression
passes 369/369. A manual browser journey for this new form has not yet been
recorded; server-rendered scope, form, error and responsive-history markup are
covered automatically.

## Known boundary

This task controls recruitment Stage mutations for applications already linked
to canonical Person. An unlinked legacy HR platform Candidate stays in the explicit
backfill queue and is not silently pulled into Hydra scope. TASK-012 duplicate
review/merge is now implemented separately; no recruitment transition attempts
to merge identities, and application moves occur only inside the reviewed
canonical merge transaction.
