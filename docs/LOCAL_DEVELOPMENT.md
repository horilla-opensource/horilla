# Local Hydra development — Phase 0

## Verified environment

The following setup was executed successfully on 2026-07-14:

- Windows x64;
- CPython 3.11.9;
- PostgreSQL 17.2 tools;
- Django 4.2.24;
- audited legacy HR platform branch/commit from `docs/UPSTREAM_AUDIT.md`.

The test used a private PostgreSQL cluster bound only to `127.0.0.1:55432`. It did not modify the existing system PostgreSQL cluster or require its administrator password.

## Prerequisites

1. Python 3.11 x64 available as `python`.
2. PostgreSQL 16 or 17 installed, including `initdb`, `pg_ctl`, `psql` and `createdb`.
3. PowerShell 5.1 or later.
4. Network access to PyPI for the first dependency install.

Docker is not required for the verified Windows path. The upstream Docker files remain available but contain development credentials and runtime migration/admin creation behavior described in the audit.

## One-command bootstrap

From the repository root:

```powershell
.\scripts\bootstrap-local.ps1
```

The bootstrap requires CPython 3.11 and verifies the interpreter before it
changes the environment. When Python is not on `PATH`, pass its absolute path:

```powershell
.\scripts\bootstrap-local.ps1 -Python "C:\Python311\python.exe"
```

If an existing `.venv` points to a removed interpreter or another Python
minor version, the script stops without deleting it. Recreate only that
derived environment explicitly after reviewing the message:

```powershell
.\scripts\bootstrap-local.ps1 -Python "C:\Python311\python.exe" -RecreateVenv
```

If the workstation policy blocks local PowerShell scripts, run the reviewed
file in a one-process bypass without changing the machine policy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap-local.ps1 -Python "C:\Python311\python.exe"
```

The script:

1. creates `.venv`;
2. installs the tested Windows/Python 3.11 dependency lock;
3. initializes `.local/postgres-data` with a local-only `hydra_local` role;
4. starts PostgreSQL on `127.0.0.1:55432`;
5. creates `hydra_phase0`;
6. generates a random Django key in ignored `.local/django-secret.txt`;
7. generates the upstream baseline migrations;
8. applies migrations and runs `manage.py check`.

The cluster uses PostgreSQL `trust` authentication but listens only on loopback. This is a workstation convenience and must never be copied to staging or production.

If PostgreSQL tools are in a non-standard location:

```powershell
.\scripts\bootstrap-local.ps1 -PostgresBin "D:\PostgreSQL\17\bin"
```

Useful optional arguments are `-DataDirectory`, `-Port` and `-Database`.

## Run the application

```powershell
.\scripts\run-local.ps1
```

Open `http://127.0.0.1:8000/`. The health endpoint is `http://127.0.0.1:8000/health/`.

The script starts the private PostgreSQL cluster if necessary, loads local environment values and starts Django without the auto-reloader. Stop Django with `Ctrl+C`.

## Stop the private database

```powershell
& "C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" `
  -D ".\.local\postgres-data" -w stop
```

Adjust the binary/data paths if custom arguments were used.

## Create an administrator

Phase 0 deliberately does not create a fixed default account. Use either legacy HR platform's initial database setup page with a locally supplied `DB_INIT_PASSWORD` or Django's command after setting the same environment as `run-local.ps1`:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Never use the `admin/admin` credentials from the upstream container entrypoint.

## Verification commands

With the local environment loaded by a PowerShell session, the core checks are:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py test
```

The historical Phase 0 bootstrap generated the missing upstream baseline. Task 045 now surfaces those generated files for review/version control; a staging checkout must contain the reviewed migrations and must never run `makemigrations` during deployment.

## Important upstream limitations

### Runtime-generated baseline migrations

Task 045 remediation: the ignore policy now surfaces every generated application migration, and the staging image supplies the pinned Django auth compatibility migration. Review and commit the surfaced baseline before a staging GO decision. The paragraphs below describe the original Phase 0 finding.

The repository ignores application migration files. `makemigrations` creates baseline files under app directories and a customized Django auth migration under `.venv`. These files are local and ignored. That is why the bootstrap must generate before migrate. See the audit and implementation decisions for the staging blocker.

All future `hydra_*` migrations must be versioned. Before Phase 1, update the ignore policy for Hydra apps or for the whole reviewed baseline.

### Management-command schedulers

Task 045 remediation: all legacy startup decisions now use `hydra.scheduling.should_start_schedulers`. Management commands never start jobs, and staging web workers must set `HYDRA_DISABLE_SCHEDULERS=True`. Re-enabling jobs requires a separately reviewed single-owner scheduler process. The paragraph below describes the original Phase 0 finding.

Some modules start APScheduler jobs whenever `sys.argv` is not one of a small excluded commands. `check` and `test` are not excluded. On an empty database this produces background “table does not exist” errors and makes commands slower; after migration, it can still run business jobs during checks. This must be separated into an explicit scheduler process before staging.

### Platform-specific dependency lock

Task 045 moves the staging image to Python 3.11 and installs the audited pinned set through `requirements.staging.lock`. Linux image build remains an explicit target-environment compatibility gate. The paragraph below describes the original Phase 0 constraint.

`requirements.phase0-windows-py311.lock` is the exact successful workstation set. The upstream Dockerfile uses Python 3.10 and must receive its own Linux/Python 3.10 lock rather than reusing this file blindly.

## Recorded Phase 0 result

```text
PostgreSQL: 17.2, hydra_phase0, hydra_local
manage.py check: System check identified no issues (0 silenced)
makemigrations --check: No changes detected (after baseline generation)
migrate --check: exit 0
GET /health/: 200 {"status":"ok"}
```

No Hydra business feature, migration or production deployment was created in this phase.
