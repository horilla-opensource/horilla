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

The baseline emitted a missing `staticfiles` directory warning and one expected
test-path log message (`Onboarding portal queue validation failed`). Neither
caused a failed test. They remain candidates for deployment/smoke validation.

## Rebranding execution evidence

### Django project package

- renamed the main Django project package from `horilla` to `hydra`;
- renamed its six branded helper modules to `hydra_*` names;
- changed the settings, URLConf, WSGI/ASGI, management, entrypoint, runtime and
  migration import paths to the new namespace;
- renamed the ignored local database to `TestDB_Hydra.sqlite3`;
- preserved a pre-change database backup under ignored `.local/backups`, with
  matching SHA-256 and `PRAGMA integrity_check = ok`;
- updated 12 historical migration files only where their executable import path
  must follow the moved project package: 42 added and 42 removed lines;
- regenerated and verified the manifest for 74 reviewed migration files;
- verified zero remaining `horilla.` project-module imports and zero remaining
  `from horilla` / `import horilla` imports;
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

## Load-test evidence

No Windows-native, authenticated multi-role load stage has been measured yet.
Anonymous endpoint throughput and earlier WSL/Agent Lab experiments are not
accepted as evidence for this objective.

| Stage | Duration | Result | Evidence |
|---|---:|---|---|
| 20 users | 15 min | NOT RUN | Generator and Windows runtime pending |
| 50 users | 30 min | NOT RUN | Generator and Windows runtime pending |
| 100 users | 60 min | NOT RUN | Generator and Windows runtime pending |
| 150 users | 60 min | NOT RUN | Generator and Windows runtime pending |
| 200 users | 120 min | NOT RUN | Generator, monitoring, safety gates, and capable runtime pending |
| spike 50 -> 200 | 60 s | NOT RUN | Generator and runtime pending |
| one-replica restart at 200 | during 200-user stage | NOT RUN | Production-like runtime pending |

## Acceptance status

| Requirement | Status | Current evidence |
|---|---|---|
| Complete Horilla -> Hydra rebranding | FAIL | 6,761 old-brand matches remain; allowlist not yet produced |
| 200 authenticated active users for 2 hours | FAIL | Not run |
| Warm error rate below 1% | FAIL | Not measured |
| Login/read p95 below 2 s | FAIL | Not measured |
| List/filter p95 below 3 s | FAIL | Not measured |
| Business-write p95 below 4 s | FAIL | Not measured |
| Core-scenario p99 below 10 s | FAIL | Not measured |
| No OOM/readiness/restart/connection leak | FAIL | Not measured at required load |
| Data integrity and organization isolation | PARTIAL | Regression tests pass; concurrent-load evidence missing |
| Replica restart preserves service and sessions | FAIL | Not run |
| Regression suite passes | PASS | 448 passed, 1 skipped on Windows baseline |
| Changes committed and pushed to user remote | FAIL | Worktree remains uncommitted and unpushed |

## Git delivery evidence

Commits created so far:

- `e9e6bcc4` - `feat: preserve completed Hydra business workflows`.

Push is intentionally pending until the remaining implementation, regression
tests and final secret scan are complete. This section will also list the final
remote, any PR, and intentionally omitted files.
