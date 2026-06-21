# Quality Process Guide
**Project:** Horilla HRMS  
**Author:** Purabh Singh — QA Engineer  
**Date:** 2026-06-21

---

## Overview

This document describes the quality gates, branch strategy, and CI/CD process for the `deepthought-qa-assessment` branch of the Horilla HRMS fork. Every change to the codebase must pass through these checkpoints before it is accepted.

---

## Branch Protection Rules

| Branch | Rule |
|--------|------|
| `main` | No direct pushes. All changes via Pull Request. |
| `develop` | No direct pushes. All changes via Pull Request. |
| `deepthought-qa-assessment` | QA deliverables branch — PR required for merge to main. |

**Enforcement:**  
- At least **1 reviewer approval** required before merge.  
- CI pipeline must **pass** (green) before merge is allowed.  
- Branch must be **up to date** with the base branch before merge.  
- No force-push on protected branches.

---

## CI/CD Pipeline (GitHub Actions)

Defined in: `.github/workflows/qa.yml`

Every push and pull request to `main` or `develop` triggers the pipeline automatically.

### Pipeline Steps

```
1. Checkout repository
2. Set up Python 3.11 (with pip cache)
3. Install requirements.txt + pytest + pytest-django
4. Set up environment (.env with test SECRET_KEY)
5. Run database migrations (--noinput)
6. Run regression tests (tests/regression/)
7. Run full test suite (manage.py test)
8. Upload test artifacts (logs, results)
```

### Pass/Fail Criteria

| Step | Behaviour on Failure |
|------|---------------------|
| Install dependencies | Pipeline fails — no further steps run |
| Migrations | Pipeline fails — environment is broken |
| Regression tests | Pipeline fails — a previously fixed bug has re-emerged |
| Full test suite | `continue-on-error: true` — logged but does not block (existing upstream failures tolerated) |

---

## Regression Suite

Location: `tests/regression/`

All regression tests must:
- Run without a live database (pure-logic, no Django ORM calls)
- Pass in under 10 seconds
- Document the defect they protect against in the module docstring
- Include both a "buggy behaviour demo" and a "fixed behaviour guard" test case

Current regression tests:

| File | Defect Protected |
|------|-----------------|
| `test_bulk_payslip_start_date.py` | QA-302 Defect B — bulk payslip `start_date` mutation |

---

## Smoke Tests

Before merging any change that touches `payroll/`, `attendance/`, or `contracts/`, a manual smoke test must be performed and noted in the PR description:

1. Start the development server (`python manage.py runserver`)
2. Log in as an HR Admin
3. Navigate to `Payroll → Payslip`
4. Create a payslip for one employee via the HTMX modal (POST — not direct GET)
5. Confirm the payslip appears in the list with correct date range and status

---

## What Is Never Allowed

- ❌ Direct push to `main` or `develop`
- ❌ Merging with a failing regression suite
- ❌ Committing `.env`, `.venv`, `*.sqlite3`, or `node_modules`
- ❌ Committing with a commit message that does not describe what changed
- ❌ Disabling CI checks to force a merge

---

## Commit Message Convention

```
type(scope): short description

Examples:
feat(payroll): add overtime cap validation
fix(attendance): prevent negative overtime_second values
docs(qa-301): add domain analysis and grounding questions
test(regression): add bulk payslip start_date mutation test
```
