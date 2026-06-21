# QA Test Strategy: Horilla HRMS

This document outlines the focused QA test strategy for verifying the core modules of the Horilla HRMS, specifically targeting the integration between Attendance, Leave, Contracts, and the Payroll calculation engine.

---

## 1. Scope of Testing

The testing suite focuses on the local Horilla HRMS installation, auditing the following apps and integration points:
*   **Payroll App:** Contract management, variable/fixed allowance setups, statutory deductions, filing statuses, and payslip generation.
*   **Attendance App:** Work-hour tracking, daily overtime computation, validation parameters, and manager approval gates.
*   **Leave App:** Leave requests (paid vs. unpaid) and their impact on Loss of Pay (LOP) computations.
*   **Employee App:** Employee work information, profile states, and status transitions (active/inactive).

Testing will be conducted on the local development environment running at `http://127.0.0.1:8000` with the SQLite database.

---

## 2. Critical Business Workflows

The testing strategy prioritizes the end-to-end (E2E) verification of the following calculation and data pipelines:

```
[ Shift Definition & Shift Day ]
               │
               ▼
[ Attendance Clock: In/Out ] ──► [ Daily Overtime Seconds ]
                                            │
                                            ▼
[ Payroll Run ] ◄────────────── [ Manager Validation & Approval ]
       │
       ├─► [ Contract Wage & Shift lookup ]
       ├─► [ Overtime Allowance: approved_seconds * rate / 3600 ]
       ├─► [ Leave Deduction: unpaid_leaves * daily_computed_wage ]
       │
       ▼
[ Saved Payslip (ID & Data) ]
```

1.  **Attendance-to-Overtime Logging:** Verifying that checking-in/out computes the raw overtime seconds and translates it into the `"HH:MM"` format under `Attendance.attendance_overtime` relative to shift minimum hours.
2.  **Manager Overtime Approval:** Verifying that approving overtime updates the monthly accumulator `AttendanceOverTime` and locks the approved duration for payslip runs.
3.  **Variable Payroll Payout:** Verifying that generating payslips correctly calls the hourly conversion math for overtime-based allowances and links the final payout to the payslip.
4.  **Absence Deduction (Loss of Pay):** Verifying that unpaid leaves are counted and subtracted from basic wages according to the employee's contract configurations.

---

## 3. Technical Risk Assessment

Based on the code analysis and verification, the following critical defects are identified as high-risk points:

*   **Risk 1: Bulk Payslip Scope Pollution (Critical Calculation Bug):** The variable `start_date` is mutated inside the loop in `generate_payslip()` at [payroll/views/component_views.py](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L771). This causes subsequent employees in a batch run to inherit the modified start date of earlier employees, leading to incorrect calculations and missing pay.
*   **Risk 2: Save Redirect Exception (Broken Redirect):** The create-payslip POST handler redirects to a mismatched URL name `view-slip` passing keyword arguments, causing a `NoReverseMatch` server crash at [payroll/views/component_views.py#L939](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L939).
*   **Risk 3: Inactive Contract Subscript Crash (Execution Bug):** Running a payslip for an employee without an active contract returns `None` from the wage calculations, which immediately triggers a crash in the calculation orchestrator at [payroll/views/component_views.py#L124](file:///C:/purabh/horilla-hr/payroll/views/component_views.py#L124).
*   **Risk 4: Stubbed Leave calculations:** The function `find_half_day_leaves()` in [payroll/methods/methods.py:L199](file:///C:/purabh/horilla-hr/payroll/methods/methods.py#L199) is stubbed and returns zero values, leading to incorrect calculations of half-day unpaid leaves.
*   **Risk 5: Direct URL GET Fallback (UI Mismatch):** Direct navigation to `/payroll/create-payslip` bypasses HTMX loading, causing form submissions to fall back to `GET` requests that fail to write records.

---

## 4. Testing Approach

To address these risks, the testing suite combines three distinct validation methodologies:

1.  **Integration Testing (Django Test Client):** Verify the calculation models (`calculate_based_on_overtime()`, `compute_salary_on_period()`) programmatically. This ensures that calculations are checked without frontend dependencies.
2.  **E2E Browser Automation (Playwright):** Verify UI flows, login validation, and tab transitions (e.g. unchecking *Is Fixed* dynamically displaying *Based On* in allowances). It captures screenshots and validates form states.
3.  **Programmatic API Verification (Python Request Client):** Submit direct API payloads directly to `/payroll/create-payslip` to bypass client-side modal dependencies and verify backend data creation.

---

## 5. Functional Testing

*   **Employee Creation:** Verify validation of required fields, constraints on Date of Birth (`dob`), and correct formatting of email/phone inputs.
*   **Contract Setup:** Validate wage type configurations (Monthly, Daily, Hourly). Verify that only active contracts are parsed by the payslip calculations engine.
*   **Attendance Logging:** Verify shift-based worked hour checks. Validate that clock-in timestamps are registered correctly in the database.

---

## 6. Integration Testing

*   **Attendance-to-Allowance Sync:** Verify that approving daily overtime (`attendance_overtime_approve = True`) immediately increments `AttendanceOverTime.overtime_second` for the month. Disapproving must correctly decrement it.
*   **Leave-to-Payroll Integration:** Verify that approved unpaid leaves logged in the `leave` app automatically translate into LOP deductions under the correct contract rules (either daily computed salary or fixed penalty rate).

---

## 7. Payroll & Overtime Math Validation

The QA suite must enforce mathematical correctness check verification:

### A. Overtime Calculation Payout
$$E = T \times \left(\frac{R}{3600}\right)$$
*Where:*
*   $E$ = Calculated Overtime Payout (rounded to 2 decimal places)
*   $T$ = Total approved overtime seconds from `Attendance.approved_overtime_second`
*   $R$ = Hourly rate from `Allowance.amount_per_one_hr`

### B. Loss of Pay (LOP) Deduction
*   If `calculate_daily_leave_amount = True`:
    $$\text{LOP} = \text{Unpaid Leaves} \times \left(\frac{\text{Wage}}{\text{Days in Month}}\right)$$
*   If `calculate_daily_leave_amount = False`:
    $$\text{LOP} = \text{Unpaid Leaves} \times \text{deduction\_for\_one\_leave\_amount}$$

---

## 8. Negative Testing Scenarios

*   **Negative Wages/Rates:** Submit negative values for `wage` or `amount_per_one_hr` to check for validation catches.
*   **Inverted Pay Periods:** Submit pay periods where `start_date > end_date` to ensure the form validation blocks submission.
*   **Boundary Dates:** Submit future attendance dates to verify that they are rejected.
*   **Invalid Choice Submissions:** Attempt to POST an inactive employee ID or an invalid `based_on` choice.

---

## 9. Regression Testing Suite

Following fixes to the codebase, the regression test suite must execute the following checks:
1.  **Single Payslip Redirect Verification:** Run single payslip creation and verify the client is redirected to `/payroll/view-payslip/<payslip_id>/` without encountering 404/500 errors.
2.  **Bulk Date Pollution Verification:** Generate bulk payslips for a list of employees with varying contract start dates, verifying that the start dates do not pollutes subsequent iterations.
3.  **Direct Form Method Post Verification:** Verify that `/payroll/create-payslip` forms are configured with fallback `method="post"` values.

---

## 10. Test Data Strategy

Testing will utilize a isolated sqlite database populated with standardized fixtures:
*   **Mock Shift:** Daily shift from 09:00 to 17:00 (Minimum hour: 8 hours).
*   **Mock Employee:** Profile for Michael Brown (`employee_id = 2`).
*   **Mock Contract:** Active contract starting `2025-07-01` with monthly wage of `28000.00`.
*   **Mock Attendance:** Log for `2025-07-15` with `02:30` hours overtime, validated and approved.
*   **Mock Allowance:** Overtime allowance worth `100.00` per hour.

---

## 11. Exit Criteria

The test cycle will be considered complete and ready for release when:
1.  All blocker and critical calculation defects (including Bulk Generation Scope pollution and Single Payslip Redirect crash) are resolved.
2.  Calculated payroll amounts (Gross Pay, LOP, Overtime Payout, Net Pay) match expected outcomes within a $\pm 0.01$ currency unit margin of error.
3.  All E2E Playwright test assertions pass successfully and generate expected screenshots under the `artifacts/screenshots` folder.
