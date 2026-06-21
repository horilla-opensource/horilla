# Horilla HRMS — Quality Engineering Assessment

**Candidate:** Purabh Singh
**Assessment:** DeepThought Quality Engineer Fellowship
**Repository Branch:** `deepthought-qa-assessment`
**CI/CD Build Pipeline Status:** ![QA Status](https://github.com/sleeptoken7/horilla-hr/actions/workflows/qa.yml/badge.svg)

---

# Executive Summary

This repository contains my Quality Engineering assessment performed on the Horilla HRMS platform.

The objective was not merely to find bugs, but to understand how payroll data flows through the system, identify where failures could harm real stakeholders, and build automated safeguards to prevent those failures from recurring.

During this assessment I:

* Analyzed the payroll domain and construction workforce workflows
* Created a complete overtime-entry specification from an ambiguous product request
* Performed exploratory testing on live functionality
* Discovered and documented verified payroll defects
* Built automated regression and negative test coverage
* Implemented CI/CD quality gates through GitHub Actions
* Produced risk-focused documentation centered on stakeholder impact

---

# System Mind Map

As required by the DeepThought assessment, here is the hand-drawn Mind Map mapping the interactions between Psychology (team and user human dynamics), Business (financial risk and stakeholder impact), and Technology (the Django/SQLite platform & stubbed boundaries).

![Purabh's Quality & System Mind Map](dt_mindmap_purabh.jpeg)

---

# Understanding the System

After auditing the application, I concluded that every major module ultimately feeds a single output:

## The Payslip

The payslip is the final aggregation point for:

* Employee records
* Contracts
* Attendance
* Overtime
* Leave
* Allowances
* Deductions

Because salary is the final business outcome, defects in upstream systems directly affect employee compensation.

The most critical quality objective therefore became:

> Prevent silent payroll corruption.

---

# QA-301 — Product Specification

A vague overtime-entry requirement was transformed into a build-ready specification.

Deliverables include:

* Acceptance Criteria
* Edge Cases
* Pre-development Questions
* Given / When / Then Scenarios
* Launch Blockers
* Future (V2) Scope

Location:

```text
specs/overtime-entry-screen.md
```

---

# QA-302 — Exploratory Testing

Five payroll-related defects were identified and documented.

## Verified Defects

### HOR-PAY-001

Broken redirect after payslip creation.

**Impact:** Payroll operator cannot access newly created payslip.

### HOR-PAY-002

Bulk payslip generation mutates shared start date variable.

**Impact:** Employees can receive incorrect salary calculations.

### HOR-PAY-003

Missing contract triggers runtime crash.

**Impact:** Payslip generation fails unexpectedly.

### HOR-PAY-004

Half-day leave calculation helper is stubbed.

**Impact:** Leave deductions are silently incorrect.

### HOR-PAY-005

Direct GET submission silently fails.

**Impact:** Payroll operator believes action succeeded when no payslip was created.

Location:

```text
bug-reports/
```

---

# QA-303 — Negative Testing & Captured Evidence

Negative testing focused on breaking payroll workflows and validation boundaries.

Coverage includes:

* Invalid inputs
* Missing fields
* Boundary values
* Invalid workflow states
* Silent failure scenarios

Artifacts:

```text
docs/QA-303-negative-testing.md
tests/
```

### Verified Live End-to-End Execution Evidence:
The step-by-step verification below documents the payslip computation flow under test:

| Step 1: Allowance Details | Step 2: Attendance Details |
| --- | --- |
| ![Allowance Details Panel](screenshots/step1_allowance_details.png) | ![Biometric Attendance Matcher](screenshots/step2_attendance_details.png) |
| **Step 3: Payslip Form** | **Step 4: Computed Payslip Details** |
| ![Payslip Form Verification](screenshots/step3_payslip_form.png) | ![Payslip Calculated Totals](screenshots/step4_payslip_details.png) |

---

# QA-304 — Regression Protection

Regression suites were created around payroll-critical behavior.

Covered scenarios include:

* Bulk payslip date propagation
* Salary-to-payslip consistency
* Missing contract handling
* New employee edge cases
* Mid-period payroll calculations

Goal:

> Protect classes of failures, not individual bugs.

---

# QA-305 — Quality Gate

A CI pipeline was implemented using GitHub Actions.

Pipeline responsibilities:

* Install dependencies
* Run automated tests
* Execute regression suites
* Generate reports
* Block broken changes before merge

Workflow:

```text
.github/workflows/qa.yml
```

---

# Risk-Based Testing Strategy

Testing was prioritized based on stakeholder impact rather than technical complexity.

## Most Vulnerable Stakeholder

Hourly and daily wage workers.

A payroll failure for these employees can directly affect:

* Rent payments
* Food expenses
* Loan obligations
* Family finances

This understanding influenced bug severity classification throughout the assessment.

---

# Repository Structure

```text
specs/
├── overtime-entry-screen.md

bug-reports/
├── HOR-PAY-001-...
├── HOR-PAY-002-...
├── HOR-PAY-003-...
├── HOR-PAY-004-...
└── HOR-PAY-005-...

docs/
├── QA-301-domain-analysis.md
├── QA-303-negative-testing.md
├── quality-process.md
├── quality-reflection.md
└── summary-sheet.md

tests/
├── regression/
└── negative/

.github/
└── workflows/
    └── qa.yml
```

---

# Key Learning

The most important lesson from this assessment was:

> Payroll defects are rarely technical problems alone. They become financial problems for real people.

Quality engineering is not simply verifying software behavior. It is building systems that prevent human mistakes, surface hidden failures, and protect the people who depend on the software.

---

# Assessment Status

* QA-301 ✅
* QA-302 ✅
* QA-303 ✅
* QA-304 ✅
* QA-305 ✅

All deliverables completed and committed to the assessment branch.
