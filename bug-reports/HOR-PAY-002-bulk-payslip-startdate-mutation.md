# Bug Report: HOR-PAY-002
**Title:** Bulk Payslip Generation Mutates `start_date` Across Employees — Wrong Pay Period for All Except First  
**Defect ID:** HOR-PAY-002  
**Severity:** Critical  
**Priority:** High  
**Component:** `payroll` — Views & Business Logic  
**Classification:** VERIFIED REPRODUCED  
**Reported:** 2026-06-21

---

## Who Gets Hurt

**Every employee after the first in a bulk payslip run.** If Employee A has a contract starting June 15 and Employee B has a contract starting June 1, Employee B's payslip will be computed from June 15 — losing 14 days of pay. This is a direct financial loss. At scale (10+ employees per batch), most employees receive incorrect payslips with no visible error.

---

## Steps to Reproduce

1. Create two active employees with active contracts:
   - **Employee A:** Contract starts `2026-06-15`
   - **Employee B:** Contract starts `2026-06-01`
2. Navigate to **Payroll → Payslips → Bulk Generate** (`/payroll/generate-payslip`).
3. Select both employees.
4. Set Start Date: `2026-06-01`, End Date: `2026-06-30`.
5. Submit.
6. Open the generated payslips for both employees and check their `start_date` field.

---

## Expected Result

- Employee A payslip: `start_date = 2026-06-15` (contract started mid-month)
- Employee B payslip: `start_date = 2026-06-01` (full month contract)

---

## Actual Result

- Employee A payslip: `start_date = 2026-06-15` ✅
- Employee B payslip: `start_date = 2026-06-15` ❌ (inherited mutated date from Employee A's iteration)

Employee B loses 14 days of computed salary.

---

## Root Cause Analysis

In `payroll/views/component_views.py` (lines 763–774), `start_date` is read from the form **once**, before the loop:

```python
start_date = form.cleaned_data["start_date"]  # set once
for employee in employees:
    if start_date < contract.contract_start_date:
        start_date = contract.contract_start_date  # MUTATES the shared variable
    payslip = payroll_calculation(employee, start_date, end_date)
```

Python has no block scope — mutating `start_date` inside the loop changes it for all subsequent iterations. After processing Employee A (whose contract starts June 15), `start_date` becomes `2026-06-15`, which is then used for Employee B.

---

## Reproduction Evidence

Verified via direct execution script simulating the loop logic. Output confirmed:
- Iteration 1 (Employee A): `start_date` = `2026-06-15` (mutated from `2026-06-01`)
- Iteration 2 (Employee B): `start_date` = `2026-06-15` (wrong — should be `2026-06-01`)

Regression test committed: `tests/regression/test_bulk_payslip_start_date.py`

---

## Code References

| File | Lines | Note |
|------|-------|------|
| `payroll/views/component_views.py` | 763–774 | Loop with shared mutable `start_date` |

---

## Recommended Fix

```diff
- start_date = form.cleaned_data["start_date"]
+ requested_start_date = form.cleaned_data["start_date"]
  for employee in employees:
+     start_date = requested_start_date  # reset per employee
      if start_date < contract.contract_start_date:
          start_date = contract.contract_start_date
```
