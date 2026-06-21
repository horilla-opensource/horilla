# Bug Report: HOR-PAY-003
**Title:** Server Crash (`TypeError`) When Generating Payslip for Employee Without Active Contract  
**Defect ID:** HOR-PAY-003  
**Severity:** High  
**Priority:** High  
**Component:** `payroll` — Wage Computation Orchestrator  
**Classification:** CODE FINDING ONLY  
**Reported:** 2026-06-21

---

## Who Gets Hurt

**HR Admin and Payroll Operator.** Any employee who is between contracts (contract terminated, not yet renewed, or in probation with no contract attached) will crash the payroll engine if included in payslip generation. The operator receives no helpful error message — only HTTP 500. The employee receives no payslip and no explanation.

---

## Steps to Reproduce

1. Create or identify an employee with **no active contract** (status: draft, terminated, or absent).
2. Navigate to **Payroll → Payslips → Create Payslip**.
3. Select the contractless employee.
4. Set any date range. Click **Save**.
5. Observe the server response.

---

## Expected Result

System rejects the request gracefully with a user-visible validation error:
> "This employee does not have an active contract for the selected period."

No HTTP 500. No server crash.

---

## Actual Result

**HTTP 500 Internal Server Error.**

Django traceback:
```
TypeError: 'NoneType' object is not subscriptable
  File "payroll/views/component_views.py", line 124
    contract = basic_pay_details["contract"]
```

---

## Root Cause Analysis

`compute_salary_on_period()` in `payroll/methods/methods.py` (lines 508–509) returns `None` when no active contract is found:

```python
contract = Contract.objects.filter(
    employee_id=employee, contract_status="active"
).first()
if contract is None:
    return contract  # returns None
```

The calling orchestrator in `payroll/views/component_views.py` (lines 124–125) immediately indexes into the return value without checking for `None`:

```python
basic_pay_details = compute_salary_on_period(employee, start_date, end_date)
contract = basic_pay_details["contract"]  # crashes if basic_pay_details is None
```

No `None` guard exists between the call and the indexing.

---

## Code References

| File | Lines | Note |
|------|-------|------|
| `payroll/views/component_views.py` | 124–125 | Unguarded indexing into possibly-None return |
| `payroll/methods/methods.py` | 508–509 | Returns `None` for missing contract |

---

## Recommended Fix

```python
basic_pay_details = compute_salary_on_period(employee, start_date, end_date)
if basic_pay_details is None:
    raise ValidationError(
        _("An active contract is required to compute payroll for this employee.")
    )
contract = basic_pay_details["contract"]
```
