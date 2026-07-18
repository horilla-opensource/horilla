# Hydra recruitment extension — TASK-2

## Status and decision

Implemented on 2026-07-14.

The required audit decision is **EXTEND**. Hydra keeps legacy HR platform `Recruitment`, `Stage`, `Candidate`, automatic initial-stage creation, pipeline screens, history and downstream onboarding compatibility. The extension adds the required `Candidate` → `Person` ownership and uses a **WRAP** policy boundary for Hydra permissions and organization scope. No upstream recruitment model or migration is forked.

## Complete vertical slice

The server-rendered workspace at `/hydra/recruitment/` provides:

- a searchable list of linked Candidate applications;
- a scoped Candidate detail linked to canonical Person identity;
- creation of a standard legacy HR platform Candidate from a scoped Person;
- automatic use of legacy HR platform's active `initial` Stage;
- a reviewed backfill queue for legacy Candidates without a Person link;
- role-aware Hydra shell navigation on desktop and mobile.

`Person` remains the owner of passport name, date of birth, gender and citizenship. A Hydra intake snapshots the Candidate name, date of birth and gender from Person while Candidate continues to own campaign, position, stage, contact used for the application, source and recruitment outcome.

## Security boundary

Hydra reads use `hydra_people.recruitment_selectors`; writes use `hydra_people.services`. The selected-company session value is never an authorization decision.

Linked Candidate visibility is the intersection of:

1. `recruitment.view_candidate`;
2. `hydra_people.view_person`;
3. the Person's current effective assignment and the actor's active Hydra grant;
4. the Candidate recruitment's legal company and the actor's granted hierarchy.

Out-of-scope direct Candidate URLs return HTTP 404. Creating an application additionally requires `hydra_people.change_person`, `hydra_people.link_candidate`, `recruitment.add_candidate` and `recruitment.view_recruitment`. Services repeat these checks and lock the Person, Recruitment, Candidate/link rows involved in the transaction.

An unlinked legacy Candidate has no Person/team assignment. It is therefore not exposed using a team, section, location or department inference. Backfill requires an active direct company grant plus the change/link permissions. Superusers have the explicit administrative bypass used elsewhere in Hydra.

## Duplicate and backfill policy

- One Candidate can link to exactly one Person through the existing one-to-one database constraint.
- A service rejects a second application for the same Person and Recruitment.
- legacy HR platform's `(email, recruitment)` uniqueness remains in force and is checked case-insensitively before save.
- Linking the same Candidate to the same Person is idempotent.
- Linking it to another Person is rejected.
- `PersonApplication.link_source` records `manual`, `hydra_intake` or `backfill` for audit context.
- No automatic identity matching is performed. Existing applications require an operator to verify and select the Person.

## Migration

`hydra_people/migrations/0002_personapplication_link_source.py` adds the link-source field with `manual` as the backwards-compatible default. The upstream `recruitment` schema is unchanged.

## Automated verification

Focused tests cover:

- model permission denial;
- team-scoped list and cross-scope direct URL denial even when the session selects all companies;
- direct-company-only access to the legacy backfill queue;
- transactional Candidate creation and canonical identity snapshot;
- duplicate Person/Recruitment rollback;
- reviewed backfill source tracking;
- continued operation of the original legacy HR platform Candidate list;
- existing Person, organization-scope and shell regression suites.

Final PostgreSQL verification completed 40/40 tests. `manage.py check`, `makemigrations --check --dry-run`, `migrate --check`, Python compilation, `pip check` and `git diff --check` also passed.

Browser QA used the real local Django/PostgreSQL stack. At 1280 px the linked and backfill lists, scoped detail and create form rendered with one active navigation item and no horizontal overflow. At 390 × 844 px the list cards stacked correctly (`documentWidth` 380 px for a 390 px viewport), and the create form collapsed to one column with both recruitment and position choices available.

## Manual verification

1. Grant a recruiter `view_person`, `change_person`, `link_candidate`, `view_candidate`, `add_candidate` and `view_recruitment`, plus a current Hydra scope grant.
2. Open `/hydra/recruitment/` and confirm only linked applications in scope appear.
3. Open a scoped Person and select **Create application**; choose an open recruitment and one of its positions.
4. Confirm the created record appears both in Hydra and in the original legacy HR platform Candidate view with the automatic initial stage.
5. Try the direct URL of a Candidate assigned outside the role's scope and confirm HTTP 404.
6. For legacy backfill, use a role with a direct company grant, review an unlinked application and link it to a visible Person.
7. Repeat at a viewport no wider than 390 px and confirm there is no horizontal overflow.

## Known limitations

- Existing legacy Candidates are intentionally not auto-matched by email/name/date of birth.
- A direct company grant is required for backfill because an unlinked Candidate has no trustworthy team assignment.
- Hydra intake currently creates applications for an existing Person; creating a new Person remains the preceding People workflow.
- Candidate-to-Employee conversion is TASK-3/phase 3 work and is not changed here.
- Candidate/private document delivery remains unsafe in upstream legacy HR platform. The completed `hydra_documents` boundary now stores sensitive Hydra files separately and does not use that path.

## Completed security dependency

TASK-2 `021-private-documents.md` is implemented and documented in `docs/HYDRA_PRIVATE_DOCUMENTS.md`. The next numbered task is `022-legalization-mvp.md`.
