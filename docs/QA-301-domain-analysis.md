# QA-301 — Domain Analysis: Horilla HRMS
**Candidate:** Purabh Singh  
**Project:** Horilla HRMS (DeepThought QA Fellowship)  
**Date:** 2026-06-21  
**Status:** Complete

---

## Grounding Question 1

> *Every piece of data in this HRMS flows toward one output. What is that output and why does everything revolve around it?*

**The output is the Payslip.**

Every module in Horilla exists to feed accurate, verified data into one final calculation — the monthly payslip that determines what an employee is paid.

Trace the data flow:

1. **Employee profile** → defines the person, their designation, department, and joining date. Without a valid employee record, no contract can be created.
2. **Contract** → defines the base wage, currency, payment type (monthly/hourly/daily), and the pay period. The payslip engine reads contract data as the foundation of every salary calculation. Without an active contract, payslip generation fails silently.
3. **Attendance** → records daily presence, absences, and overtime seconds (`overtime_second`, `attendance_overtime`). These feed directly into loss-of-pay (LOP) deductions and overtime additions on the payslip.
4. **Leave** → approved leave records are consumed during payslip calculation. Half-day leaves trigger the `find_half_day_leaves()` function in `payroll/methods/methods.py`, which (as verified during audit) is currently stubbed and returns zero — meaning leave deductions are silently dropped.
5. **Allowances** → configured per-employee or company-wide (e.g., HRA, transport, meal allowance). Each allowance has a condition, computation method, and tax flag. They are summed into gross pay on the payslip.
6. **Deductions** → similarly configured (e.g., PF, ESI, income tax). Computed per payslip period and subtracted from gross pay.
7. **Payslip** → the final output. It aggregates: base pay from contract + allowances − deductions − LOP + overtime payout = **Net Pay**. This is the number the employee receives as their salary.

The payslip is not just an output — it is the **legal record** of compensation. It is the document presented to banks for loans, to courts in disputes, and to tax authorities. Every upstream data error (wrong attendance, incorrect contract dates, missing leave records, stubbed calculations) silently corrupts this single output. That is why everything revolves around it.

---

## Grounding Question 2

> *Who is the most vulnerable person in this system? What does a system failure mean for them this month?*

**The most vulnerable person is the hourly-wage or daily-rated contract employee — particularly one in their first or last partial month of employment.**

Here is why:

- A salaried employee on a full monthly contract has a fixed base pay. Even if attendance integration partially fails, their gross pay floor is likely to survive most bugs.
- An hourly or daily-rated employee's pay is **entirely derived from attendance records**. If `overtime_second` is not captured correctly, if attendance records are missing for a day, or if the `find_half_day_leaves()` stub silently returns zero when it should deduct half a day — their net pay is computed on wrong inputs with no visible error.

**What a system failure means for them this month:**

| Failure Scenario | Impact on Vulnerable Employee |
|------------------|-------------------------------|
| Defect B (bulk start_date mutation) | Their payslip covers the wrong pay period — they may receive payment for dates they did not work, or miss payment for dates they did |
| Defect D (`find_half_day_leaves` stub) | Half-day leaves are never deducted from salary. The employee is overpaid — but when the bug is fixed, they may face retroactive recovery |
| Defect E (GET on create-payslip silently fails) | Their payslip is never generated. The payroll operator sees no error. The employee receives no salary disbursement this month. |
| Overlapping contracts (NT-03) | Two active contracts exist. The system picks one arbitrarily. The employee receives either too much or too little pay with no audit trail. |

For a daily-wage earner, missing one month's salary is not an inconvenience — it is a **financial crisis**. Rent, food, and loan repayments are all due on the same cycle. A system failure at payslip generation directly translates into material harm for this person, and the silence of these bugs (no error messages, no alerts to payroll operators) makes detection unlikely until the employee complains.

---

## Grounding Question 3

> *Trace what happens when a site manager enters incorrect overtime hours. Where does the error travel, who should catch it, and who actually catches it?*

**Step-by-step trace of an incorrect overtime entry:**

### Entry Point — Attendance Module
A site manager opens `Attendance → Attendance → Add Attendance` and enters `overtime_second = 7200` (2 hours) for an employee who actually worked 0 overtime. The form is submitted via HTMX POST to `attendance/views.py`.

**Who should catch it here:** The form validator should cross-check `overtime_second` against shift end time and work duration. **Who actually catches it:** Nobody. There is no cross-field validation between `overtime_second` and actual shift hours. The record is saved as submitted.

### Storage — AttendanceOverTime Model
The `AttendanceOverTime` accumulator (`attendance/models.py`) stores `attendance_overtime` (HH:MM string) and `overtime_second` (integer). These two fields can be independently set to inconsistent values. There is no `clean()` method enforcing consistency. The incorrect `7200` seconds is written to the database.

**Who should catch it here:** Model-level validation via `clean()`. **Who actually catches it:** Nobody.

### Payslip Calculation — Payroll Engine
When the payroll operator generates the payslip for that employee, `payroll/methods/methods.py` → `compute_salary_on_period()` queries `AttendanceOverTime` records for the pay period and reads `overtime_second` to calculate the overtime payout.

The formula uses the incorrect `7200` seconds. The employee's overtime payout is inflated by 2 hours × hourly rate. This is added to gross pay without any flag.

**Who should catch it here:** An automated anomaly check — e.g., "overtime > 4 hours in a day triggers approval gate." **Who actually catches it:** Nobody. There is no overtime cap or approval requirement at the payslip computation stage.

### Payslip Output — Final Record
The payslip is generated with an inflated net pay. The `Payslip` model stores the computed gross, deductions, and net pay. No diff is shown against the previous month. No alert is triggered.

**Who should catch it here:** The HR Admin reviewing the payslip before release, or an automated variance report (e.g., "net pay increased >20% vs last month"). **Who actually catches it:** Potentially nobody, unless the HR Admin manually compares payslips. In practice, bulk payslip generation means per-record review does not happen.

### Who Gets Hurt
- **The company** is overpaying the employee due to a data entry error that was never validated.
- **The employee** receives more money than entitled — creating a potential recovery dispute later.
- **The site manager** has no feedback that their entry was incorrect, so the error repeats next month.
- **The Finance team** sees inflated payroll costs with no explanation in the audit log.

### Summary of Accountability Gap

| Stage | Should Catch | Actually Catches | Gap |
|-------|-------------|-----------------|-----|
| Attendance form submission | Form validator | Nothing | No cross-field validation |
| Model save | `clean()` method | Nothing | No `MinValueValidator` or consistency check |
| Payslip computation | Overtime cap / approval gate | Nothing | No business rule enforcement |
| Payslip review | HR Admin / variance report | Manual review only | No automated anomaly detection |

**The error travels all the way from attendance entry to the final payslip without being intercepted at any automated checkpoint.** This represents a complete absence of defence-in-depth for one of the most financially sensitive data paths in the system.

---

## Supporting Evidence

All findings in this document are grounded in actual Horilla source code investigation:

| File | Relevance |
|------|----------|
| `payroll/views/component_views.py` | `generate_payslip` loop mutation (Defect B), `create_payslip` GET failure (Defect E) |
| `payroll/methods/methods.py` | `find_half_day_leaves` stub returning zero (Defect D) |
| `attendance/models.py` | `AttendanceOverTime` fields: `overtime_second`, `attendance_overtime` |
| `payroll/models/models.py` | `Contract` model — no overlap validation, no `clean()` |
| `payroll/methods/payslip_calc.py` | Salary computation pipeline |
