# 🛠️ Horilla HRMS — Quality Engineering & Payroll Audit
**Candidate:** Purabh Singh | **Branch:** `deepthought-qa-assessment` | **CI Status:** ![QA Status](https://github.com/sleeptoken7/horilla-hr/actions/workflows/qa.yml/badge.svg)

This repository holds the quality engineering pipeline, domain analysis, regression suites, and verified defect logs for the **Horilla HRMS** as part of the **DeepThought Quality Engineer Fellowship** application.

---

## 🗺️ The Quality & System Map (Mind Map Guide)
*For a fellowship candidate, the mind map is the single artifact showing if you understand the payroll engine as a living system.* 

Use the guide below to draw your physical paper diagram. Connect these concepts using arrows to make the interdependencies visible.

```
                  [ 👤 PM: Wants Speed & mobile overtime entry screen ]
                                      │ (feature request)
                                      ▼
                        [ 📝 OVERTIME SCREEN SPEC ] (QA-301)
                                      │
 ┌────────────────────────────────────┼────────────────────────────────────┐
 │ (Psychology: Human Factors)        │ (Business: Consequence)            │ (Technology: The Code)
 ▼                                    ▼                                    ▼
[🧑‍💻 Supervisor / Site Manager]      [💰 The Payslip: Ultimate Output]     [🔌 API / SQLite Database]
 - Dusty screen, fat-finger errors    - Overtime hours added to base pay   - Multi-App dependencies
 - Direct GET history navigation      - Pro-rated for mid-month joins      - Absent clean() constraints
 - Offline drop half-submission       - Deducted for LOP (Loss of Pay)     - Stubbed out logic
 │                                    │                                    │
 └─────────────────┬──────────────────┴──────────────────┬─────────────────┘
                   │                                     │
                   ▼                                     ▼
        [⚠️ SILENT WAGE CORRUPTION]               [🧪 AUTOMATED SAFETY NET]
         - Defect B: Bulk dates bleed            - tests/regression: Loop boundary
         - Defect D: Leaves stubbed to 0         - tests/negative: Method-blockers
         - Defect E: GET request silently drops  - GitHub Actions: Pre-merge gate
```

### How to draw this on paper:
1. **Central Node:** Draw a large circle named **"💰 The Payslip (The Ultimate Output)"**.
2. **Branch 1 (Psychology - Who is using it?):** 
   - Draw **Site Managers** entering data on mobile under hot/dusty site conditions (leads to double-clicks and empty submissions).
   - Draw **Developers (Senior Dev)** who fixes bugs from memory and thinks testing is slow overhead, and **New Devs** who are afraid to touch the payroll module.
3. **Branch 2 (Business - What happens if it breaks?):**
   - Draw the **Hourly Worker** who gets underpaid and can't pay rent because dates mutated in bulk runs.
   - Draw the **Company** losing cash because half-day leaves are stubbed out and never deducted.
4. **Branch 3 (Technology - The actual gaps):**
   - Connect **`generate_payslip` loop** to the mutated `start_date` bug.
   - Connect **GET request view** to the silent form submission bug.
   - Draw the **GitHub Action Workflow** wrapping around the code as a shield.
5. **Draw Interconnections:** Run red ink lines connecting the **Senior Dev's psychology** to the **Stubbed code**, and the **GET request view** to the **Vulnerable Operator** who assumes a payslip was saved when it wasn't.

---

## 📂 Deliverables Directory Structure

All audit files are structured cleanly in the project directory:
*   **Root Level:**
    *   [`test-strategy.md`](/test-strategy.md) — The risk-mitigation testing strategy tailored for construction payroll.
*   **`specs/`**
    *   [`overtime-entry-screen.md`](/specs/overtime-entry-screen.md) — Detailed spec with input parameters, pre-dev questions, Given/When/Then scenarios, and Blocker vs. v2 release mapping.
*   **`bug-reports/`** (5 separate verified tickets with steps, impacts, and root causes):
    *   [`HOR-PAY-001-payslip-redirect-crash.md`](/bug-reports/HOR-PAY-001-payslip-redirect-crash.md) (Blocker)
    *   [`HOR-PAY-002-bulk-payslip-startdate-mutation.md`](/bug-reports/HOR-PAY-002-bulk-payslip-startdate-mutation.md) (Critical)
    *   [`HOR-PAY-003-missing-contract-typeerror.md`](/bug-reports/HOR-PAY-003-missing-contract-typeerror.md) (High)
    *   [`HOR-PAY-004-stubbed-halfday-leaves.md`](/bug-reports/HOR-PAY-004-stubbed-halfday-leaves.md) (Medium)
    *   [`HOR-PAY-005-get-submission-silent-failure.md`](/bug-reports/HOR-PAY-005-get-submission-silent-failure.md) (Medium)
*   **`docs/`**
    *   [`QA-301-domain-analysis.md`](/docs/QA-301-domain-analysis.md) — Deep answers to the three domain-grounding questions.
    *   [`QA-303-negative-testing.md`](/docs/QA-303-negative-testing.md) — The negative testing matrix with actual HTTP capture logs.
    *   [`quality-process.md`](/docs/quality-process.md) — Quality Gate definition, branch protection strategies, and smoke tests.
    *   [`quality-reflection.md`](/docs/quality-reflection.md) — Honest reflection on engineering systems, dev-advocacy, and testing habits.
    *   [`summary-sheet.md`](/docs/summary-sheet.md) — The 8-Question Summary sheet.

---

## 🧪 Running the Audit Test Suite

### 1. In-Memory Logic Tests (Fast, 0.2s runtime)
To check the negative validation logic and bulk proration calculations without locking databases:
```powershell
$env:PYTHONPATH="."; pytest -k "test_bulk_payslip_start_date or test_salary_propagation or test_create_payslip_get_method"
```

### 2. Full Regression Run
To run Django tests including DB migrations:
```powershell
python manage.py test tests.smoke.test_smoke
```

---

## 🛡️ CI/CD Quality Gate Status
The workflow in [`.github/workflows/qa.yml`](/.github/workflows/qa.yml) is activated. On every pull request and push to the `deepthought-qa-assessment` branch, the gate automatically:
1. Provisions python virtual environments.
2. Installs workspace dependencies.
3. Automatically executes database migrations (utilizing checked-in app migrations).
4. Runs the smoke suite, regression checks, and negative validators.
5. Fails and blocks merges if a single assertion turns red.
