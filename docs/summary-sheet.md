# DeepThought QA Fellowship — 8-Question Summary Sheet
**Candidate:** Purabh Singh  
**Project:** Horilla HRMS (Forked Repository)  
**Date:** 2026-06-21

---

## 1. What is your forked repository link and development branch?
*   **Repository Link:** [sleeptoken7/horilla-hr](https://github.com/sleeptoken7/horilla-hr)
*   **Branch:** `deepthought-qa-assessment`
*   **Latest Commit SHA:** `1a858f7f468a45c9a4831c5918711afaa3be2b95`

---

## 2. Where is the manual Overtime Entry Screen specification (QA-301)?
*   **File Path:** [overtime-entry-screen.md](file:///C:/purabh/horilla-hr/specs/overtime-entry-screen.md)
*   **Summary of Contents:** This spec translates a vague Slack message into a production-ready feature definition. It outlines:
    *   Detailed acceptance criteria and input constraints (`HH:MM` time-format validation).
    *   10 pre-development clarifying questions for the PM/dev lead (addressing monthly caps, dual-supervisor conflicts, offline synchronization, etc.).
    *   9 Given/When/Then scenarios covering happy paths, boundary conditions, and negative/failure paths.
    *   A launch blocker vs. v2 categorization table.

---

## 3. Where are your 5 verified payroll bug reports (QA-302)?
*   **Bug Reports Location:** [bug-reports/](file:///C:/purabh/horilla-hr/bug-reports/)
*   **Individual Bug Report Files:**
    1.  [HOR-PAY-001-payslip-redirect-crash.md](file:///C:/purabh/horilla-hr/bug-reports/HOR-PAY-001-payslip-redirect-crash.md) (Severity: Blocker/Critical) — Django `NoReverseMatch` redirect crash.
    2.  [HOR-PAY-002-bulk-payslip-startdate-mutation.md](file:///C:/purabh/horilla-hr/bug-reports/HOR-PAY-002-bulk-payslip-startdate-mutation.md) (Severity: Critical) — Scope pollution mutates start date for bulk payslips underpaying workers.
    3.  [HOR-PAY-003-missing-contract-typeerror.md](file:///C:/purabh/horilla-hr/bug-reports/HOR-PAY-003-missing-contract-typeerror.md) (Severity: High) — `TypeError` crash when employee has no active contract.
    4.  [HOR-PAY-004-stubbed-halfday-leaves.md](file:///C:/purabh/horilla-hr/bug-reports/HOR-PAY-004-stubbed-halfday-leaves.md) (Severity: Medium) — Stubbed function returns zero, leading to silent overpayments.
    5.  [HOR-PAY-005-get-submission-silent-failure.md](file:///C:/purabh/horilla-hr/bug-reports/HOR-PAY-005-get-submission-silent-failure.md) (Severity: Medium) — Direct URL GET access leads to silent submission failure.

---

## 4. Where is your negative testing report and what failure cases did you automate (QA-303)?
*   **Report Path:** [QA-303-negative-testing.md](file:///C:/purabh/horilla-hr/docs/QA-303-negative-testing.md)
*   **Automated Tests:** [test_create_payslip_get_method.py](file:///C:/purabh/horilla-hr/tests/negative/test_create_payslip_get_method.py)
*   **Report Summary:** The report details 5 negative testing scenarios (input validation, HTTP methods, boundary conditions) based on verified behaviors in the codebase. The automated tests verify that the system blocks incorrect HTTP request styles (GET submissions of the create-payslip form) that would otherwise lead to silent failures.

---

## 5. Where is your automated regression test suite (QA-304)?
*   **Regression Files:**
    *   [test_bulk_payslip_start_date.py](file:///C:/purabh/horilla-hr/tests/regression/test_bulk_payslip_start_date.py)
    *   [test_salary_propagation.py](file:///C:/purabh/horilla-hr/tests/regression/test_salary_propagation.py)
*   **Summary of Scenarios Covered:**
    *   Verification that bulk payslip generation does not mutate the requested start date across multiple employee records.
    *   Wage propagation validations: contract status check (no contract raises ValidationError), proration of salary for mid-month hires, double contract updates in the same period, zero-attendance proration, and full-month controls.
    *   *Rigor Check:* The regression suite runs purely in-memory (mocked DB layer) to ensure speed (runs in under 1 second in CI).

---

## 6. Where is your CI/CD configuration and Quality Gate documentation (QA-305)?
*   **CI Configuration:** [.github/workflows/qa.yml](file:///C:/purabh/horilla-hr/.github/workflows/qa.yml)
*   **Quality Process Path:** [quality-process.md](file:///C:/purabh/horilla-hr/docs/quality-process.md)
*   **Process Summary:** The workflow automates repository checkout, Python installation, dependency setup, and the test suite execution on every push or pull request to the main branch. The quality process document outlines branch protection strategies, PR merge requirements, and manual/automated regression gates.

---

## 7. How did you verify the hand-drawn Mind Map requirement?
*   **Status:** A physical, hand-drawn mind map has been sketched on paper (not digital, not AI-generated) per DeepThought rules.
*   **Structure of the Mind Map:**
    *   *Center:* Payslip (the ultimate output of the entire HRMS).
    *   *Branches:* Employee details, active contracts, biometric attendance logs, overtime adjustments, and leaves.
    *   *Defect Markers:* Indicates the 5 verified defects mapped to the exact node they corrupt (e.g., `start_date` loop mutation under the contract-payslip link).
*   **Submission Details:** A photo scan of the map is prepared to be sent alongside this summary on the Internshala application thread.

---

## 8. What is your honest self-rating and key learning from this assessment?
*   **Self-Rating:** **8.5 / 10**
    *   *Justification:* The codebase was audited meticulously, uncovering 5 real defects (2 reproduced locally, 3 verified through code inspection). Every deliverable is repository-specific and avoids generic boilerplate. The automated test suite is fast, robust, and cleanly integrated with CI. The remaining 1.5 points represent E2E Playwright coverage which was excluded due to execution time constraints.
*   **Key Learning:** Quality engineering is not just about writing tests to check if the code runs; it is about protecting the stakeholders. In construction payroll, a minor bug like a `start_date` loop mutation directly underpays a worker, affecting their family's survival this month. Rigorous testing is a moral responsibility.
