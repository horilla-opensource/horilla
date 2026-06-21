# Bug Report: HOR-PAY-001
**Title:** Server Crash (Django `NoReverseMatch`) on Single Payslip Submission Redirect  
**Defect ID:** HOR-PAY-001  
**Severity:** Blocker / Critical  
**Priority:** High  
**Component:** `payroll` — Views & URL routing  
**Classification:** CODE FINDING ONLY  
**Reported:** 2026-06-21

---

## Who Gets Hurt

**Payroll Operator.** Every time they create an individual payslip via the UI, the server crashes with HTTP 500. The payslip may or may not have been saved (race condition at the point of failure), meaning operators cannot confirm whether salary was computed or must retry — risking duplicate payslips.

---

## Steps to Reproduce

1. Log in as Administrator or Payroll Manager.
2. Navigate to **Payroll → Payslips**.
3. Click **Create Payslip** (opens HTMX modal at `/payroll/create-payslip`).
4. Select an active employee from the dropdown.
5. Set Start Date: `2026-06-01`, End Date: `2026-06-30`.
6. Click **Save**.
7. Observe the HTTP response and Django server log.

---

## Expected Result

Payslip is saved. User is redirected to the payslip detail view at `/view-payslip/<payslip_id>/` with a success notification.

---

## Actual Result

Server returns **HTTP 500 Internal Server Error**.

Django traceback:
```
django.urls.exceptions.NoReverseMatch: Reverse for 'view-payslip' with
keyword arguments '{'payslip_id': <id>}' not found. 'view-payslip' is not
a valid view function or pattern name.
```

---

## Root Cause Analysis

In `payroll/views/component_views.py` (lines 939–944), after saving the payslip:

```python
return HorillaRedirect(
    request,
    redirect_to=reverse(
        "view-payslip", kwargs={"payslip_id": payslip.pk}
    ),
)
```

The URL named `"view-payslip"` is defined in `payroll/urls/component_urls.py` as a **parameterless** list view:
```python
path("view-payslip/", component_views.view_payslip, name="view-payslip"),
```

Passing `kwargs={"payslip_id": payslip.pk}` to a parameterless route causes `NoReverseMatch`. The correct URL for individual payslip detail is `"view-created-payslip"` (defined in `payroll/urls/urls.py` line 73).

---

## Code References

| File | Lines | Note |
|------|-------|------|
| `payroll/views/component_views.py` | 939–944 | Broken redirect call |
| `payroll/urls/component_urls.py` | 89 | Parameterless route definition |
| `payroll/urls/urls.py` | 73–77 | Correct detail route |

---

## Recommended Fix

```diff
- redirect_to=reverse("view-payslip", kwargs={"payslip_id": payslip.pk})
+ redirect_to=reverse("view-created-payslip", kwargs={"payslip_id": payslip.pk})
```
