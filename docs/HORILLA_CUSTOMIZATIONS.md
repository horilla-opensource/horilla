# Horilla customizations

This file records intentional deviations from audited Horilla branch `1.0`.

## Phase 0

- `dynamic_fields` signal registration moved from `migrations/__init__.py` to `DynamicFieldsConfig.ready()` so standard Django test discovery does not import models for an uninstalled optional app.
- Windows/PostgreSQL bootstrap scripts and an audited dependency lock were added without changing Horilla business behavior.

## TASK-1 Person identity

- `hydra_people.apps.HydraPeopleConfig` was added to `INSTALLED_APPS` and the Hydra sidebar.
- The app is registered in Horilla settings/sidebar and its `/hydra/people/` routes are included explicitly in the root URL configuration.
- No Horilla Employee, Candidate or Recruitment database field was modified. Integration uses foreign keys owned entirely by `hydra_people`.
- `.gitignore` explicitly allows versioned `hydra_people` migrations while leaving generated upstream baseline migrations ignored.
- Horilla background schedulers now exclude the Django `test` command. Previously scheduler connections prevented PostgreSQL from destroying the test database and could run production jobs against test data.
- The malformed template-library declaration in upstream `templates/403.html` was corrected so permission denials return an actual HTTP 403 page instead of raising `TemplateSyntaxError`.

## TASK-1 Organization scope

- `hydra_coordination.apps.HydraCoordinationConfig` and `/hydra/coordination/` routes were registered explicitly; the existing Hydra sidebar gained an Organization entry rather than adding a duplicate root menu.
- `hydra_people` reads and write services were extended with effective organization scope. Horilla's `selected_company` session filter remains available for its UI but is not used as Hydra authorization.
- `.gitignore` explicitly allows the versioned `hydra_coordination` migration.
- `ThreadLocalMiddleware` now restores or clears request context in `finally`. The upstream implementation retained the previous request/user indefinitely on reused worker threads, which could misattribute later model writes.
- The malformed template-library declaration in upstream `templates/404.html` was corrected so out-of-scope direct URLs return an actual HTTP 404 page.

## TASK-1 Hydra shell

- `hydra_shell.apps.HydraShellConfig` was registered as a template/static-only app with no database models.
- Current Hydra screens wrap Horilla's existing `index.html` rather than replacing the outer navbar, sidebar, notifications or account controls.
- Hydra's former inline page CSS moved into a scoped static stylesheet; a small mobile script initializes the inherited sidebar as collapsed on Hydra pages and preserves the existing toggle.
- `HYDRA_PORTAL_URL` adds a configurable HTTPS-only public training/start portal. Template tags emit only mapped language and `from=hydra`, with no authenticated identifiers.

## TASK-2 private candidate documents

- `hydra_documents.apps.HydraDocumentsConfig` and `/hydra/documents/` were registered explicitly.
- Hydra-private files use `HYDRA_PRIVATE_MEDIA_ROOT`, which a system check requires to be disjoint from public `MEDIA_ROOT`; the storage deliberately has no URL method.
- Candidate and Person remain upstream/Hydra identity owners. The new app owns only the protected file metadata and append-only access events.
- Existing Horilla candidate/employee document screens and `/media/` remain operational for upstream compatibility, but Hydra-private files never use that path.
- `.gitignore` explicitly allows versioned `hydra_documents` migrations and excludes the local `.private_media/` directory.

## TASK-2 legalization MVP

- `hydra_legalization.apps.HydraLegalizationConfig` and `/hydra/legalization/` were registered explicitly, with one new permission-aware Hydra navigation item.
- Legalization cases link to `hydra_people.Person` and `hydra_documents.PrivateDocument`; no upstream Horilla Employee, Candidate or document schema was changed.
- All case reads use current Person organization scope. Status changes, responsibility changes and document links use transactional services with independent permission checks.
- Existing Horilla document-request screens remain operational and are covered by a regression test.
- `.gitignore` explicitly allows the versioned `hydra_legalization` migration.

## Full engineering TASK-008 audit and Person timeline

- Horilla's existing `django-auditlog` registration remains the technical model-change audit; no upstream audit table or signal was replaced.
- `hydra_people.timeline` wraps safe action labels from auditlog and authoritative append-only Hydra domain histories. It does not read or render `LogEntry.changes`/serialized payloads.
- `hydra_coordination.selectors._scope_ids` now resolves all five scope dimensions from one values query instead of five independent queries. Deeper `select_related` paths preserve the existing company resolution semantics for narrow grants.
- The Person page gained a read-only responsive timeline. Every source retains its own permission and narrower Location/Team/application checks.
- No database migration or upstream Horilla model change was required.

## Full engineering TASK-010 recruitment workflow

- Horilla `Recruitment`, `Stage`, `Candidate`, simple history and pipeline views remain the owned upstream implementation.
- The main Horilla list/kanban stage-change paths call the controlled Hydra service only when a Candidate has a canonical Person link; unlinked legacy rows keep their reviewed boundary.
- `Candidate.save()` now rejects uncontrolled stage changes for linked rows, and the existing Horilla bulk-update signal blocks linked `stage_id` updates. Same-stage sequence reordering is unchanged.
- The legacy Candidate edit form rejects cancellation-checkbox changes for linked rows so cancellation must carry the configured reason through Hydra.
- `hydra_people.0004_recruitmentstagetransitionrule_and_more` adds directed configurable rules and append-only transition evidence without adding fields to Horilla tables.

## Full engineering TASK-017 universal tasks

- `hydra_tasks.apps.HydraTasksConfig` and `/hydra/tasks/` are registered explicitly; the Hydra shell gains one permission-aware Tasks entry.
- Horilla project, onboarding and helpdesk task models are not changed. Their incompatible domain ownership remains intact while `hydra_tasks` owns the canonical Person/approved-domain operational task contract.
- Horilla's `notifications.Notification` and `notify` signal are reused behind a durable task-delivery row, post-commit dispatch, current-recipient scope recheck and PII-free payload.
- Person detail/timeline and the coordinator exception panel consume scoped task selectors; no task state is copied into those modules.
- `hydra_tasks.0001_initial` is versioned in the exact migration manifest. No upstream Horilla table gains a task field.

## Full engineering TASK-018 notifications

- `hydra_notifications` and `/hydra/notifications/` wrap the existing Horilla notification table with immutable recipient/target envelopes, append-only state, user preferences and durable generic-email delivery; no upstream table field was added.
- All Hydra producers now call the fixed-kind PII-free service. Existing legacy rows are data-migrated into envelopes and future `notify` signal output is wrapped without forwarding legacy content to email.
- Horilla tray/list/count paths use current-recipient scoped selectors. Read, clear and archive mutations are POST-only; external avatar requests and actor-name rendering were removed from notification partials.
- `hydra.decorators.login_required` re-raises 404/403, never executes a failed view twice and uses HTTP 500 for the development error page. The custom 404/405 templates return correct statuses.
- `hydra_notifications.0001_notification_center` and `0002_backfill_legacy_notifications` are pinned in the exact 70-file migration manifest.
