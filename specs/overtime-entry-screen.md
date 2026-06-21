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
