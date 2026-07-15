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
