# Product Requirement Specification: Manual Overtime Entry Screen

**Roles:** Product Manager & QA Lead  
**Feature Name:** Manual Overtime Entry Screen  
**App Component:** `attendance` app integration  
**Target File Path:** `specs/overtime-entry-screen.md`

---

## 1. Problem Statement
Currently, Horilla HRMS computes employee overtime strictly based on daily clock-in and clock-out timestamps in the `Attendance` model. If employees perform overtime during offsite work, field travel, or when clocking devices fail, managers have no administrative interface to log manual overtime hours. Managers are currently forced to modify daily check-in/out timestamps to force the calculations engine to compute the desired overtime. This results in data corruption of actual clocking history and introduces manual errors.

---

## 2. Business Goal
Provide a secure and user-friendly **Overtime Entry Screen** for HR Admins and Managers to directly input manual overtime hours for employees on specific dates. The feature must leverage the existing Horilla attendance database architecture, respect the monthly `AttendanceOverTime` accumulators, validate entries against global overtime cut-offs, and seamlessly feed approved hours into the payroll payslip generation engine.

---

## 3. User Stories

1.  **As a Manager,** I want to manually log overtime hours for a specific employee and date, so that offsite and device-failure hours are recorded.
2.  **As an HR Admin,** I want the manual overtime entry to automatically inherit and apply the company's daily `overtime_cutoff` rules, so that we prevent unauthorized overtime logging.
3.  **As a Payroll Operator,** I want manually created overtime to be aggregated into the employee's monthly `AttendanceOverTime` accumulator, so that it is automatically calculated and paid out on their monthly payslip.
4.  **As an Employee,** I want to view my logged manual overtime on my personal attendance tab and generated payslips, so that I can audit my compensation.

---

## 4. Functional Requirements

### A. UI/Screen Layout & Input Fields
The screen will be mapped under **Attendance** -> **Attendances** -> **Log Manual Overtime** and present a form containing:
*   **Employee Selector (`employee_id`):** Dropdown displaying active employees.
*   **Date Selector (`attendance_date`):** Date field (defaulting to today).
*   **Overtime Duration Input (`attendance_overtime`):** String text input field requiring `"HH:MM"` format (e.g., `02:30` or `01:45`).
*   **Overtime Note (`note`):** Optional text area for audit comments justifying the manual log.

### B. Business Logic & Processing Workflow
When a manager submits a manual overtime record:
1.  **Form Formatting Translation:** The system automatically converts the input `"HH:MM"` string into total integer seconds and populates the `overtime_second` database field.
2.  **Attendance Record Matching:**
    *   If no `Attendance` record exists for the employee and date, the system instantiates a new record, setting `attendance_worked_hour = minimum_hour` (to show they met shift requirements) and populating the overtime parameters.
    *   If an `Attendance` record already exists, the system updates the overtime parameters on the existing record.
3.  **Applying Validation Conditions:** The transaction calls `handle_overtime_conditions()` to cap hours at the global `overtime_cutoff` configuration.
4.  **Enforcing Approval Rules:** Manual entries default to unapproved (`attendance_overtime_approve = False`) unless created by an admin possessing the `attendance.approve_overtime` permission, which triggers auto-approval and populates `approved_overtime_second`.
5.  **Accumulator Synchronization:** Saving triggers the database hooks on `Attendance` to update the monthly cumulative total in the `AttendanceOverTime` model.

---

## 5. Non-Functional Requirements

*   **Security & Permissions:** The screen is restricted to users with `attendance.add_attendance` and `attendance.change_attendance` permissions. Employees must not have access to this screen.
*   **Audit Trail Logs:** Any manual overtime creation or modification must trigger a historical audit log under `horilla_audit` capturing the user ID, timestamp, original values, and new values.
*   **Performance:** Form validation and DB commit (including accumulator recalculations) must complete in under **500ms**.

---

## 6. Validation Rules

1.  **Future Date Block:** The `attendance_date` cannot be a future date.
2.  **Format Constraints:** The `attendance_overtime` field must pass the `validate_time_format` regex validation (pattern: `^[0-9]{2,}:[0-5][0-9]$`).
3.  **Active Contract Validation:** The selected employee must possess an active contract (`contract_status = 'active'`) covering the targeted `attendance_date`.
4.  **Boundary Maximum Capping:** If the entered overtime exceeds the global `overtime_cutoff` parameter, the system must trigger a confirmation modal warning the user that hours will be capped at the cutoff limit before saving.

---

## 7. Error Handling

*   **Format Mismatch:** If the user inputs invalid characters (e.g. `"2.5"` or `"abc"`), the system must reject submission and highlight the input field with: *"Please enter duration in HH:MM format (e.g. 02:30)."*
*   **Duplicate Record Conflict:** If manual overtime is submitted for a date that already has an approved overtime log, the system must prompt: *"An approved overtime record already exists for this date. Modifying will recalculate monthly payroll. Do you wish to proceed?"*
*   **Missing Contract Exception:** If the selected employee has no active contract, the form must block submission and display: *"Cannot log overtime. No active payroll contract exists for this employee."* (To prevent Defect 3 subscript crashes).

---

## 8. API & Data Model Impact

No new tables are introduced. The feature utilizes the existing models:
*   **Write Targets:** Writes directly to the `Attendance` model in [attendance/models.py](file:///C:/purabh/horilla-hr/attendance/models.py).
*   **Recalculation Call:** Triggering the `Attendance.save()` method automatically recalculates `AttendanceOverTime` via `self.update_ot()` and `attendance_account.save()`, ensuring downstream payslip runs dynamically pick up the new hours.

---

## 9. Edge Cases

1.  **Overtime Cap changes:** If the global `overtime_cutoff` is changed *after* a manual overtime entry has been logged, the system must **not** retroactively mutate historical manual entries unless those records are edited and re-saved.
2.  **Retroactive logs for Closed Payroll Periods:** If a manager logs manual overtime for a date that falls within a previously locked/paid payslip period, the form must display a blocking warning and require a secondary confirmation from a superuser.
3.  **Null-Shift Mappings:** If the employee's contract does not define a shift, daily `minimum_hour` defaults to `00:00`, and all manual entries are added as pure overtime.

---

## 10. Acceptance Criteria

1.  **Verify UI Fields:** The user can access the entry screen and fill in the Employee, Date, and Overtime Duration inputs.
2.  **Verify Time Formatting:** Entering `"03:30"` successfully writes `12600` to `overtime_second` in the database.
3.  **Verify Cutoff Enforcement:** If the cutoff is set to `"02:00"`, entering `"03:00"` manual overtime is automatically capped at `"02:00"` (7,200 seconds) on save.
4.  **Verify Accumulator Integration:** Saving an approved manual overtime entry of 2 hours (`7200` seconds) increments the monthly `AttendanceOverTime.overtime_second` record by `7200` seconds.
5.  **Verify Payslip Calculation:** Running a payroll generation for the month successfully pulls the manual approved overtime hours and calculates the earning amount using the hourly rate.

---

## 11. Questions to Ask Before Development Starts

These must be answered by the PM and business before a single line of code is written. Each unanswered question is a mid-sprint scope change waiting to happen.

### Business Rules
1. **Monthly overtime cap:** What is the exact 60-hour cap rule? Is it 60 hours of overtime per month, or 60 total hours including regular hours? Who can override the cap — only a superuser, or any manager with a reason?
2. **Dual-supervisor conflict:** Two site managers log overtime for the same worker on the same day. Which entry wins? Is it first-in, last-in, requires merge approval, or blocks the second entry entirely?
3. **Retroactive entries:** How far back can a supervisor log manual overtime? Same day only? Within the current pay period? Across closed payroll periods? Who approves retroactive entries?
4. **Approval chain:** Does every manual overtime entry require HR Admin approval before it feeds into payroll, or can managers self-approve up to a threshold (e.g., ≤2 hours)?
5. **Deletion:** Can a submitted overtime entry be deleted after it has been approved? What happens to the monthly accumulator if an approved entry is deleted?

### Technical Constraints
6. **Offline/mobile submission:** Site managers enter data at construction sites with poor connectivity. If the form is submitted and the network drops mid-request, does the system guarantee idempotency? Can the manager resubmit safely without creating a duplicate?
7. **Existing clock-in data conflict:** If an employee already has a clock-in/clock-out record for a date (showing 0 overtime via the biometric system), and a manager logs 2 hours of manual overtime, which value takes precedence in payroll calculation?
8. **Notification:** Should the employee receive a notification (email/in-app) when manual overtime is logged on their behalf?
9. **Audit visibility:** Can employees see who logged their manual overtime and when? Is this a legal requirement in the jurisdictions where the system is deployed?

### Scope Boundary
10. **Bulk entry:** Can a manager log overtime for multiple workers at once (e.g., end-of-week batch for 10 labourers), or is this screen single-entry only?

---

## 12. Test Scenarios (Given / When / Then)

### Happy Path

**Scenario 1: Manager logs valid overtime within cap**
```
Given a site manager is logged in with attendance entry permissions
  And employee "Rajan Kumar" has an active contract for June 2026
  And the global overtime_cutoff is set to "04:00"
When the manager enters: Employee = Rajan Kumar, Date = 2026-06-15, Overtime = "02:30"
  And clicks Save
Then a new Attendance record is created for 2026-06-15 with overtime_second = 9000
  And AttendanceOverTime for June 2026 increments by 9000 seconds
  And the entry status is "pending approval"
  And the manager sees a success confirmation message
```

**Scenario 2: Admin logs overtime with auto-approval**
```
Given an HR Admin is logged in with the "attendance.approve_overtime" permission
When the admin logs 1 hour of overtime for any employee
Then the entry is saved with attendance_overtime_approve = True
  And approved_overtime_second is populated immediately
  And the June payslip for that employee will include the overtime payout
```

### Boundary / Edge Cases

**Scenario 3: Overtime exceeds the 60-hour monthly cap**
```
Given employee "Arjun Mehta" has already accumulated 55 hours of overtime in June
  And the monthly cap is 60 hours
When a supervisor submits 7 hours of overtime for Arjun on 2026-06-28
Then the system displays a warning: "Adding 7 hours would exceed the 60-hour monthly cap.
  Only 5 hours will be recorded."
  And the entry is saved with exactly 5 hours (18000 seconds)
  And the supervisor must explicitly confirm before save completes
```

**Scenario 4: Dual supervisor conflict — same worker, same day**
```
Given supervisor A logs 2 hours of overtime for worker "Priya Nair" on 2026-06-10
  And that entry has status "pending"
When supervisor B attempts to log 3 hours for the same worker on 2026-06-10
Then the system blocks the second submission
  And displays: "An overtime entry for Priya Nair on 2026-06-10 already exists and
  is pending approval. Contact HR to modify it."
  And no duplicate record is created
```

**Scenario 5: Offline submission / connectivity loss**
```
Given a manager submits an overtime entry from a mobile browser at a construction site
  And the network drops after form submission but before the server response arrives
When the manager reloads the page and resubmits the same entry
Then the system detects the duplicate (same employee + date + duration submitted within 5 minutes)
  And returns a warning: "A matching entry may already exist. Check the overtime list before resubmitting."
  And does NOT create a second record if the first was persisted
```

### Negative / Failure Paths

**Scenario 6: Future date blocked**
```
Given today is 2026-06-21
When a manager submits overtime with Date = 2026-06-25
Then the form rejects the submission
  And displays: "Overtime cannot be logged for a future date."
  And no record is created
```

**Scenario 7: Invalid time format**
```
When a manager enters "2.5" or "90minutes" in the Overtime Duration field
Then the form rejects submission immediately (client-side validation)
  And displays: "Please enter duration in HH:MM format (e.g. 02:30)."
```

**Scenario 8: Employee with no active contract**
```
When a manager selects an employee whose contract has expired
  And submits any overtime duration
Then the form displays: "Cannot log overtime. No active payroll contract exists for this employee."
  And no Attendance record is created
  And the payroll engine is never invoked (prevents HOR-PAY-003)
```

**Scenario 9: Zero overtime entry**
```
When a manager submits "00:00" as overtime duration
Then the form rejects submission
  And displays: "Overtime duration must be greater than zero."
```

---

## 13. Launch Blocker vs v2

### 🔴 Launch Blockers (must be complete before any production deployment)

| # | Item | Reason |
|---|------|--------|
| 1 | Monthly overtime cap enforcement with warning modal | Financial/legal liability — uncapped overtime is a compliance risk |
| 2 | Dual-supervisor duplicate entry prevention | Data integrity — two entries for same worker/day corrupts accumulator |
| 3 | Employee without active contract blocked at form level | Prevents HOR-PAY-003 server crash |
| 4 | Pending approval workflow (entries don't auto-apply to payroll) | Without this, unreviewed overtime reaches payslips |
| 5 | Future date submission blocked | Basic data integrity |
| 6 | HH:MM format validation with clear error message | Required for usable mobile entry |
| 7 | AttendanceOverTime accumulator correctly updated on save | Core payroll integration — without this the feature does nothing useful |
| 8 | Audit log entry created for every manual overtime record | Legal requirement for construction payroll compliance |

### 🟡 v2 (valuable but not blocking launch)

| # | Item | Reason |
|---|------|--------|
| 1 | Offline / idempotent submission support | Helpful for construction sites; workaround is mobile data reload |
| 2 | Bulk entry for multiple workers at once | Efficiency feature; single-entry works for MVP |
| 3 | Employee notification on overtime entry | Nice-to-have; HR can inform employees manually |
| 4 | Retroactive entry across closed payroll periods | Complex approvals; block this at launch, unlock in v2 with superuser gate |
| 5 | Overtime entry visible on employee self-service portal | Transparency feature; read-only HR view is sufficient for v1 |
| 6 | Conflict resolution UI for supervisor disputes | Rare edge case; HR manual resolution is acceptable at launch |
