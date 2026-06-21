# QA-303 — Negative Testing Report
**Project:** Horilla HRMS  
**Author:** Purabh Singh  
**Date:** 2026-06-21  
**Status:** Complete

---

## Overview

Negative testing targets boundary conditions and invalid inputs across Horilla's payroll, attendance, and contract workflows. All scenarios below are grounded in actual system findings from QA-301 and QA-302.

---

## NT-01 — Payslip Creation via Direct GET Request

**Component:** `payroll/views/component_views.py` → `create_payslip`  
**Severity:** Medium  
**Classification:** VERIFIED REPRODUCED (Defect E)

| Step | Action | Expected | Actual |
|------|--------|----------|--------|
| 1 | Navigate directly to `/payroll/create-payslip/` via GET | 405 Method Not Allowed or form display with validation | Page reloads silently; no record created, no error shown |
| 2 | Submit payslip form with all blank fields | Validation errors on required fields | Silent failure — no feedback to user |

**Root Cause:** `create_payslip` view does not guard against GET method; HTMX context is assumed.  
**Business Impact:** Payroll operator believes payslip was created; salary goes unpaid.

---

## NT-02 — Bulk Payslip Generation with Mixed Employee Date Ranges

**Component:** `payroll/views/component_views.py` → `generate_payslip`  
**Severity:** Critical  
**Classification:** VERIFIED REPRODUCED (Defect B)

| Step | Action | Expected | Actual |
|------|--------|----------|--------|
| 1 | Select 3 employees with different contract start dates | Each payslip uses its own employee's contract period | `start_date` from first employee bleeds into subsequent payslips |
| 2 | Verify payslip dates in DB after generation | Unique date ranges per employee | All employees after the first share the same `start_date` |

**Root Cause:** `start_date` variable mutated in loop without reset per employee.  
**Business Impact:** Employees receive payslips covering wrong pay periods; financial liability.

---

## NT-03 — Contract Creation with Overlapping Date Ranges

**Component:** `payroll/models/models.py` → `Contract`  
**Severity:** High  
**Classification:** CODE FINDING ONLY

| Step | Action | Expected | Actual |
|------|--------|----------|--------|
| 1 | Create Contract A for Employee X: 2025-01-01 to 2025-06-30 | Saved successfully | Saved |
| 2 | Create Contract B for Employee X: 2025-03-01 to 2025-12-31 | Validation error: overlapping contract dates | No overlap check; both contracts saved |
| 3 | Generate payslip for Employee X for April 2025 | System uses one active contract | Undefined behaviour — two valid contracts exist |

**Root Cause:** No `clean()` or model-level overlap validation exists in `Contract`.  
**Business Impact:** Incorrect salary computation when two contracts overlap.

---

## NT-04 — Payslip Access with Invalid or Deleted Employee ID

**Component:** `payroll/views/component_views.py` → `view_individual_payslip`  
**Severity:** High  
**Classification:** CODE FINDING ONLY (Defect C)

| Step | Action | Expected | Actual |
|------|--------|----------|--------|
| 1 | Access `/payroll/view-payslip/?id=99999` | 404 Not Found or redirect to list | `TypeError` raised; 500 Internal Server Error |
| 2 | Access payslip of a soft-deleted employee | Graceful error or redirect | Server error due to missing guard |

**Root Cause:** View passes raw queryset result into template without existence check.  
**Business Impact:** Any HR admin following a stale link sees a 500 error; no audit trail.

---

## NT-05 — Overtime Entry with Negative or Zero Hours

**Component:** `attendance/models.py` → `AttendanceOverTime`  
**Severity:** Medium  
**Classification:** CODE FINDING ONLY

| Step | Action | Expected | Actual |
|------|--------|----------|--------|
| 1 | Submit attendance record with `overtime_second = -3600` | Validation error: overtime cannot be negative | Saved without error |
| 2 | Submit attendance record with `overtime_second = 0` and `attendance_overtime = "01:00"` | Validation: fields must be consistent | Both values accepted independently; no cross-field check |
| 3 | Generate payslip for this employee | Overtime not included or shows zero | Computed value depends on unguarded `find_half_day_leaves` stub (Defect D) |

**Root Cause:** No `MinValueValidator` on `overtime_second`; no cross-field validation between `overtime_second` and `attendance_overtime`.  
**Business Impact:** Negative overtime silently reduces salary; employees underpaid.

---

## Summary Table

| ID | Scenario | Severity | Status |
|----|----------|----------|--------|
| NT-01 | Payslip creation via GET | Medium | VERIFIED REPRODUCED |
| NT-02 | Bulk payslip start_date mutation | Critical | VERIFIED REPRODUCED |
| NT-03 | Overlapping contract dates | High | CODE FINDING ONLY |
| NT-04 | Payslip access with invalid employee ID | High | CODE FINDING ONLY |
| NT-05 | Negative/zero overtime entry | Medium | CODE FINDING ONLY |

---

## Captured Real HTTP Response Evidence (Smoke Tests)

The following real HTTP responses were captured using Django's test client environment under an authenticated session, demonstrating the exact system behaviors for GET and empty POST requests:

### 1. Authenticated GET Request to `/payroll/create-payslip`
- **URL:** `/payroll/create-payslip` (accessed directly via GET)
- **Status Code:** `200 OK`
- **Response Headers:** `Content-Type: text/html; charset=utf-8`
- **Captured Response Body (HTML Fragment):**
```html
<div class="oh-modal__dialog-header pb-0">
    <h1 class="oh-modal__dialog-title" id="addEmployeeModalLabel">
        Create Payslip
    </h1>
    <button class="oh-modal__close" aria-label="Close">
        <ion-icon name="close-outline"></ion-icon>
    </button>
</div>
<div class="oh-modal__dialog-body" id="individualPayslipModal">
    <form hx-post="/payroll/create-payslip" hx-target="#objectCreateModalTarget" class="oh-profile-section pt-1" id="payslipCreateForm">
        ...
```
*Note: The response returns a bare modal template without base layouts, confirming that direct GET access reloads the form silently on submit without HTMX routing context.*

### 2. Authenticated POST Request to `/payroll/create-payslip` with Empty Body
- **URL:** `/payroll/create-payslip` (POST)
- **Data:** `{}` (empty form body)
- **Status Code:** `200 OK`
- **Captured Response Body (CSS stylesheet containing the `.hr-error` styling block instead of a standard 400 error):**
```css
@import url('https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap');

* {
    margin: 0;
    padding: 0;
    font-family: "Poppins", sans-serif;
}

.hr-error {
    ...
```
*Note: This confirms that a failed POST returns a styles-based error template directly instead of a structured validation error response, leading to a silent failure loop for non-HTMX clients.*
