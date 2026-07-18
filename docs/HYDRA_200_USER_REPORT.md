# Hydra 200-user engineering report

This report records measured evidence for the Windows-native Hydra rebranding,
scalability, and load-test objective. A statement is not marked **PASS** until
the evidence required by the acceptance contract has actually been collected.

## Scope and execution boundary

- Authoritative repository: `C:\Users\FF\Documents\Codex\2026-07-14\re\outputs\hydra-project`
- Windows-native execution only; WSL and the experimental Agent Lab are outside
  this objective.
- Existing user changes are preserved. No clone, worktree, reset, clean, or
  destructive checkout is used.

## Initial repository evidence

Captured at `2026-07-18T00:10:31.5931230+02:00`, before changes made for this
objective in the authoritative repository:

- branch: `codex/hydra-staging`;
- HEAD: `41c60b7d8f4bbc789ea687875ad91a7887a5697c` (`Fix unprivileged restore verification`);
- user remote: `fork` -> `https://github.com/OleksandrKiris/horilla-hr.git`;
- external upstream: `origin` -> `https://github.com/horilla/horilla-hr.git`;
- worktree: 223 status entries: 134 modified and 89 untracked paths;
- untracked files represented by those paths: 191;
- staged files: 0;
- `git diff --check`: PASS;
- Python: 3.11.9 from the repository `.venv`;
- Docker Desktop/Windows Docker CLI: not installed or not discoverable;
- case-insensitive old-brand scan, excluding `.git`, `.venv`, and
  `node_modules`: 6,761 matches in 564 files.

The dirty worktree is treated as intentional project state, not disposable
output. Detailed file-level state remains available from `git status --short`;
it is intentionally not duplicated here because it contains more than two
hundred paths and will continue to change during implementation.

## Baseline automated tests

Windows command:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --keepdb --verbosity 1
```

Measured result:

- Django system check: PASS, no issues;
- migration drift check: PASS, no changes detected;
- tests discovered: 448;
- tests passed: 448;
- skipped: 1 environment-dependent test;
- test runtime: 370.761 seconds;
- result: `OK (skipped=1)`.

### Owned application packages

- renamed the eight remaining legacy-named API, audit, automations, backup,
  breadcrumbs, LDAP, generic-view, and widget packages to `hydra_*` packages;
- renamed the legacy document-request package to `hydra_legacy_documents` to
  avoid collision with Hydra's private-document application;
- renamed the corresponding template directories, template filenames, widget
  module, imports, URL includes, middleware/auth paths, and AppConfig classes;
- retained six historical Django app labels only where existing database table
  names, migration dependencies, content types, and permission codenames require
  them; no stale executable import or include path uses the old packages;
- `manage.py check`: PASS;
- `makemigrations --check --dry-run`: PASS, no schema drift;
- reviewed migration manifest: PASS, 74 source files;
- tests discovered/passed: 448/448;
- skipped: 1;
- test execution time: 307.697 seconds (528.333 seconds total process time);
- result: `OK (skipped=1)`;
- checkpoint old-brand scan: 2,358 matches in 411 files. Remaining work was owned
  identifiers/UI/fixtures/translations plus an explicit technical/legal
  allowlist; those items were completed in the next phase.

The baseline emitted a missing `staticfiles` directory warning and one expected
test-path log message (`Onboarding portal queue validation failed`). Neither
caused a failed test. They remain candidates for deployment/smoke validation.

## Rebranding execution evidence

### Django project package

- renamed the legacy Django project package to `hydra`;
- renamed its six branded helper modules to `hydra_*` names;
- changed the settings, URLConf, WSGI/ASGI, management, entrypoint, runtime and
  migration import paths to the new namespace;
- renamed the ignored local database to `TestDB_Hydra.sqlite3`;
- preserved a pre-change database backup under ignored `.local/backups`, with
  matching SHA-256 and `PRAGMA integrity_check = ok`;
- updated 12 historical migration files only where their executable import path
  must follow the moved project package: 42 added and 42 removed lines;
- regenerated and verified the manifest for 74 reviewed migration files;
- verified zero remaining imports from the legacy project namespace;
- reduced the old-brand scan from 6,761 matches in 564 files to 2,776 matches
  in 470 files; the remaining application packages, identifiers, UI content,
  fixtures, translations and justified upstream references are still in work.

Post-rename Windows regression:

- Django system check: PASS;
- migration drift check: PASS;
- tests discovered/passed: 448/448;
- skipped: 1;
- test runtime: 325.581 seconds;
- result: `OK (skipped=1)`.

### Identifiers, UI, fixtures, translations, and compatibility

- renamed owned classes, functions, constants, fields, commands, template tags,
  route names, files, and user-facing strings to Hydra terminology;
- renamed `HydraMailTemplate` in migration state while pinning its existing
  physical table, updating content type and permission codenames in place, and
  preserving assigned authorization rows;
- added a dedicated upgrade proof that starts from the pre-rename state, inserts
  data and a permission, applies the complete graph, and verifies the record,
  permission, content type, and physical table are preserved: PASS;
- changed stored recruitment/onboarding source values through a reversible data
  migration;
- removed the two inherited branded raster logos and replaced default login and
  email branding with accessible Hydra text while retaining company white-label
  images;
- rebranded all ten gettext source catalogs and all shipped demo fixtures;
- reviewed migration manifest: PASS, 80 exact source files;
- executable rebrand allowlist: PASS, 175 approved technical/legal/upstream
  occurrences and 0 violations;
- Python compilation, Django check, and migration drift check: PASS;
- tests discovered/passed: 448/448;
- skipped: 1;
- test execution time: 309.528 seconds (520.868 seconds total process time);
- result: `OK (skipped=1)`.

## Load-test evidence

No Windows-native, authenticated multi-role load stage has been measured yet.
Anonymous endpoint throughput and earlier WSL/Agent Lab experiments are not
accepted as evidence for this objective.

The repository now contains the production-like execution boundary required
before measurement: an Nginx load balancer, two web replicas by default, a
one-shot release/migration container, PostgreSQL, persistent Redis shared
cache and `cached_db` sessions, separate maintenance work, ClamAV, health
checks, graceful worker recycling, request IDs, resource limits, and
loopback-only publication. Its focused readiness/staging tests pass 20/20.
The authenticated Locust harness is also implemented. It creates 200 isolated
accounts with deterministic role allocation, performs normal CSRF login into a
separate session per user, exercises real scoped selectors and six real domain
write services, verifies integrity every minute, records resource/latency
evidence, applies every mandatory safety stop, and performs the controlled
single-replica restart during the 200-user stage. Its focused contract tests
pass 12/12. The complete clean-database regression now passes 464/464 with one
intentional environment-dependent skip; test execution took 324.868 seconds
and the complete process took 541.8 seconds. Docker Desktop is still
unavailable on this workstation, so this
topology has not yet produced timed runtime capacity evidence.

| Stage | Duration | Result | Evidence |
|---|---:|---|---|
| 20 users | 15 min | NOT RUN | Complete runner available; Docker Desktop unavailable |
| 50 users | 30 min | NOT RUN | Complete runner available; Docker Desktop unavailable |
| 100 users | 60 min | NOT RUN | Complete runner available; Docker Desktop unavailable |
| 150 users | 60 min | NOT RUN | Complete runner available; Docker Desktop unavailable |
| 200 users | 120 min | NOT RUN | Safety monitor and restart proof implemented; Docker Desktop unavailable |
| spike 50 -> 200 | 5 s baseline + 60 s ramp + 300 s hold | NOT RUN | Spike shape implemented; Docker Desktop unavailable |
| one-replica restart at 200 | minute 15 of 200-user stage | NOT RUN | Automated proof implemented; runtime unavailable |

The same honest NOT RUN state is published for automation in
`HYDRA_LOAD_RESULTS.json` and `HYDRA_LOAD_RESULTS.csv`; missing measurements
are `null`/empty rather than forecasts. Successful runner artifacts replace
these rows only after review.

## Profiling and optimization evidence

- The previous public readiness path executed the complete cross-domain
  integrity audit on every Docker health probe. The high-frequency path is now
  bounded to configuration, PostgreSQL, and Redis; the full audit still runs at
  release and through the operator command.
- Every load read selector has a regression budget of at most 20 ORM queries
  after permission-map warm-up, independent of the number of sampled rows. All
  seven role budgets pass.
- Recruiter writes are partitioned by the authenticated creator account, so
  concurrent users do not contend on one shared candidate. Candidate seeding
  now emits a real controlled stage event, and every later stage is checked
  against the immutable latest event.
- The stage runner captures per-role query counts and PostgreSQL `EXPLAIN
  (ANALYZE, BUFFERS)` before and after load, while storing only SQL hashes and
  plans. It also records database connections and Redis memory every 10
  seconds.
- No speculative database index or organization-sensitive application cache
  was added without a PostgreSQL plan or timed load result. Any further query,
  index, or cache change is deliberately gated on the generated profiles.

## Acceptance status

| Requirement | Status | Current evidence |
|---|---|---|
| Complete old-brand removal / Hydra rebranding | PASS | 175 approved compatibility/legal/upstream occurrences; 0 allowlist violations |
| 200 authenticated active users for 2 hours | FAIL | Not run |
| Warm error rate below 1% | FAIL | Not measured |
| Login/read p95 below 2 s | FAIL | Not measured |
| List/filter p95 below 3 s | FAIL | Not measured |
| Business-write p95 below 4 s | FAIL | Not measured |
| Core-scenario p99 below 10 s | FAIL | Not measured |
| No OOM/readiness/restart/connection leak | FAIL | Not measured at required load |
| Data integrity and organization isolation | PARTIAL | Regression tests pass; concurrent-load evidence missing |
| Replica restart preserves service and sessions | FAIL | Not run |
| Regression suite passes | PASS | 464 passed, 1 skipped after the authenticated load harness and full rebrand proof |
| Changes committed and pushed to user remote | FAIL | Rebrand is committed locally; infrastructure/load work and push remain pending |

## Git delivery evidence

Commits created so far:

- `e9e6bcc4` - `feat: preserve completed Hydra business workflows`.
- `a973d09b` - `refactor: rename Django project package to Hydra`.
- `d3928a73` - `refactor: rename owned applications to Hydra`.
- `6a50689f` - `refactor: complete Hydra brand migration`.
- `9f02d233` - `feat: add scaled Hydra staging runtime`.

Push is intentionally pending until the remaining implementation, regression
tests and final secret scan are complete. This section will also list the final
remote, any PR, and intentionally omitted files.
