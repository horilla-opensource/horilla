# Bug Report: HOR-PAY-005
**Title:** Direct URL Access to Create Payslip Causes Silent GET Submission — No Record Created, No Error Shown  
**Defect ID:** HOR-PAY-005  
**Severity:** Medium  
**Priority:** Medium  
**Component:** `payroll` — Templates & View Integration  
**Classification:** VERIFIED REPRODUCED  
**Reported:** 2026-06-21

---

## Who Gets Hurt

**Payroll Operator.** If a payroll operator bookmarks the create-payslip URL, receives it in a shared link, or navigates to it directly (common on mobile or when the HTMX modal fails to load), they fill in the form and click Save. The page reloads. No payslip is created. No error is shown. The operator assumes the payslip was generated and moves on. The employee receives no salary disbursement.

---

## Steps to Reproduce

1. Open a browser and navigate directly to:  
   `http://127.0.0.1:8000/payroll/create-payslip`
2. Observe the page loads a bare, unstyled form fragment (no header, no navigation).
3. Select an employee. Set Start Date: `2026-06-01`, End Date: `2026-06-30`.
4. Click **Save**.
5. Observe the browser address bar and the page state.

---

## Expected Result

**Option A:** Direct GET request is intercepted → user redirected to `/payroll/view-payslip/` with a message to use the modal.  
**Option B:** Form submits via POST → payslip created → redirect to payslip detail.

Either outcome must produce visible feedback.

---

## Actual Result

Browser address bar changes to:
```
/payroll/create-payslip?csrfmiddlewaretoken=abc123&employee_id=1&start_date=2026-06-01&end_date=2026-06-30
```

Page reloads showing the same blank form.  
**HTTP 200 returned. No payslip created. No error displayed.**

---

## Root Cause Analysis

The form template (`payroll/templates/payroll/payslip/create_payslip.html`, lines 11–12) uses HTMX:

```html
<form hx-post="{% url 'create-payslip' %}" hx-target="#objectCreateModalTarget"
      id="payslipCreateForm">
```

There is **no `method="post"` attribute**. HTMX intercepts the submit event and issues a POST via JavaScript. But when the page is accessed directly without the parent layout, HTMX is not loaded. The browser falls back to the HTML default: **GET submission**.

The view `create_payslip` (`payroll/views/component_views.py`, lines 946–950) only processes `POST` requests:

```python
if request.method == "POST":
    # process form...
# GET falls through — renders empty form again with HTTP 200
```

No redirect, no error, silent failure.

---

## Reproduction Evidence

Accessing the URL directly and submitting the form results in a GET request confirmed by observing the browser address bar with form parameters appended as query string. The database record count for `Payslip` is unchanged after submission.

Automated test: `tests/negative/test_create_payslip_get_method.py` — 6 tests, all pass.

---

## Code References

| File | Lines | Note |
|------|-------|------|
| `payroll/templates/payroll/payslip/create_payslip.html` | 11–12 | Missing `method="post"` on form tag |
| `payroll/views/component_views.py` | 946–950 | GET request silently re-renders form |

---

## Recommended Fix

**Template fix:**
```diff
- <form hx-post="{% url 'create-payslip' %}" hx-target="#objectCreateModalTarget"
+ <form method="post" hx-post="{% url 'create-payslip' %}" hx-target="#objectCreateModalTarget"
```

**View fix — add redirect for non-HTMX GET:**
```python
if request.method == "GET" and not request.headers.get("HX-Request"):
    return redirect("view-payslip")
```
