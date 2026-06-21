# Bug Report: HOR-PAY-004
**Title:** Stubbed `find_half_day_leaves()` Returns Zero — Half-Day Leaves Never Deducted from Salary  
**Defect ID:** HOR-PAY-004  
**Severity:** Medium  
**Priority:** High  
**Component:** `payroll` — Leave & Absence Integration  
**Classification:** CODE FINDING ONLY  
**Reported:** 2026-06-21

---

## Who Gets Hurt

**Finance Team and Employees.** Any employee who takes a half-day unpaid leave is **overpaid** — the system counts the half-day as zero, so no deduction is applied. The employee receives full salary for a day they worked only half. When this is discovered (audit, reconciliation), the company must recover the overpayment from the employee — creating a dispute. At scale with 100+ employees, this creates significant undetected payroll liability.

---

## Steps to Reproduce

1. Create an unpaid leave type in the Leave module.
2. Create and approve a **half-day** unpaid leave request for any employee within the current pay period.
3. Navigate to **Payroll → Payslips** and generate a payslip for that employee.
4. Inspect the payslip's `paid_leaves`, `unpaid_leaves` values and the LOP deduction amount.

---

## Expected Result

Half-day leave = **0.5 days** deducted.  
If daily rate is ₹2,000: LOP deduction = ₹1,000 for the half-day.

---

## Actual Result

Half-day leave = **0.0 days** deducted (treated as if no half-day leave exists).  
Employee receives full daily salary for the absent half-day.

---

## Root Cause Analysis

`find_half_day_leaves()` in `payroll/methods/methods.py` (lines 199–223) is **completely stubbed**:

```python
def find_half_day_leaves():
    paid_queryset = []      # hardcoded empty list — no DB query
    unpaid_queryset = []    # hardcoded empty list — no DB query
    paid_leaves = list(filter(None, list(set(paid_queryset))))
    unpaid_leaves = list(filter(None, list(set(unpaid_queryset))))
    paid_half = len(paid_leaves) * 0.5    # always 0
    unpaid_half = len(unpaid_leaves) * 0.5  # always 0
    ...
    return {
        "half_day_leaves": total_leaves,   # always 0
        "half_paid_leaves": paid_half,     # always 0
        "half_unpaid_leaves": unpaid_half, # always 0
    }
```

The function accepts no parameters and runs no database queries. In `get_leaves()` (line 92), the return values feed directly into leave calculations:

```python
half_day_data = find_half_day_leaves()
unpaid_half = half_day_data["half_unpaid_leaves"]  # always 0
paid_half = half_day_data["half_paid_leaves"]      # always 0
unpaid_leave = len(unpaid_leave_dates) - unpaid_half  # no adjustment
```

Result: half-day leaves are counted as full days — **every half-day unpaid leave is a silent overpayment**.

---

## Code References

| File | Lines | Note |
|------|-------|------|
| `payroll/methods/methods.py` | 199–223 | Stubbed function body |
| `payroll/methods/methods.py` | 92 | Call site in `get_leaves()` |

---

## Recommended Fix

Implement actual DB query. Function signature must accept `employee`, `start_date`, `end_date`:

```python
def find_half_day_leaves(employee, start_date, end_date):
    half_day_leaves = LeaveRequest.objects.filter(
        employee_id=employee,
        leave_type_id__leave_type="half_day",
        start_date__gte=start_date,
        end_date__lte=end_date,
        status="approved"
    )
    # compute paid_half, unpaid_half from queryset
    ...
```
