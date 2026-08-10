# Royal Falcon Security Leave Accrual Policy - Admin Guide

## Overview

This guide covers the implementation of Royal Falcon Security's custom leave accrual policy. The system automates:
- **Monthly 2.5-day accrual** on employee anniversary dates
- **Employee categorization** based on badge ID prefix (Management vs. Normal)
- **Annual December 31 reset** with category-specific carryforward limits
- **Unpaid/unauthorized leave tracking** with automatic accrual pause
- **Complete audit trails** for all leave balance changes

---

## Getting Started

### 1. Initial Setup (First Time Only)

Run the initialization command to set up default configuration:

```bash
python manage.py init_royal_falcon_accrual
```

This command:
- Creates default employee categories (Management & Normal)
- Creates accrual configuration (2.5 days/month, reset Dec 31)
- Populates `Employee.original_joining_date` from existing `date_joining`

**Options:**
- `--dry-run` - Show what would be done without making changes
- `--reset` - Reinitialize all data (destructive, use with caution)

### 2. Verify Employee Categories

Navigate to **Leave > Employee Categories** to verify the setup:
- **A- prefix** → Management (30-day carryforward limit)
- **S- prefix** → Normal Employee (60-day carryforward limit)
- **D- prefix** → Directors (45-day limit)
- **P- prefix** → Part Time (40-day limit)

Edit categories as needed for your organization.

### 3. Verify Accrual Configuration

Navigate to **Leave > Accrual Configuration** to review:
- Monthly accrual days: **2.5**
- Annual reset date: **December 31**
- Active status: **Yes**

Adjust these settings if your policy differs from Royal Falcon's.

---

## Managing Unpaid Leave

### Creating an Unpaid Leave Record

**Path:** Leave > Unpaid Leaves > Add New

**Required Fields:**
- **Employee** - Select from dropdown (HR/Admin only can select any employee)
- **Start Date** - First day of unpaid leave
- **End Date** - Last day of unpaid leave
- **Reason** - Brief reason for unpaid leave (e.g., "Medical emergency", "Personal matter")
- **Status** - Select "Active" when creating

**What Happens Automatically:**
1. Days count is calculated: `End Date - Start Date`
2. Employee's accrual is immediately **paused** until return date
3. Audit log entry is created: "Accrual paused due to unpaid leave"
4. Service duration calculation **excludes** unpaid leave days

### Approving/Returning from Unpaid Leave

**Path:** Leave > Unpaid Leaves > Select Record > Edit

**Status Workflow:**
1. **Active** - Unpaid leave is in effect, accrual paused
2. **Returned** - Employee has returned to work
   - ✓ Accrual automatically resumes
   - ✓ Audit log created: "Accrual resumed after unpaid leave"
3. **Rejected** - Cancel unpaid leave record
   - ✓ Accrual resumes immediately
   - ✓ Previous balances restored

### Example: Employee with 2-Week Unpaid Leave

```
Employee: John Smith (S-042)
Start Date: Feb 1, 2024
End Date: Feb 14, 2024
Days Count: 14 days (auto-calculated)
Status: Active

Timeline:
- Feb 1: Accrual paused until Feb 14
- Feb 14: Employee returns to work
- Change status to "Returned"
- Accrual automatically resumes
- Service calculation adjusts: removes 14 days from service duration
```

---

## Managing Unauthorized Extensions

### Creating an Unauthorized Extension Record

**Path:** Leave > Unauthorized Extensions > Add New

**When to Use:**
- Employee was approved for paid leave ending on date X
- Employee did NOT return on date X
- Employee returned on a later date

**Fields:**
- **Employee** - Select employee
- **Leave Request** - Link to the approved paid leave request
- **Approved Return Date** - When they should have returned (auto-filled from leave request)
- **Actual Return Date** - When they actually returned
- **Unauthorized Days** - Auto-calculated difference
- **Status** - "Pending Review" or "Approved"

**What Happens:**
1. System calculates: `Actual Return Date - Approved Return Date = Unauthorized Days`
2. Unauthorized days are treated like unpaid leave
3. Service calculation **excludes** unauthorized days
4. Audit log tracks the adjustment

### Example: Extended Holiday

```
Approved leave: March 1-10, 2024 (10 days)
Approved return: March 11, 2024
Actually returned: March 15, 2024
Unauthorized days: 4

Employee can be:
- Approved (accept 4 unauthorized days)
- Rejected (require approval for leave extension)
- Converted to Paid (HR approves as paid leave)
```

---

## Understanding Audit Logs

### Viewing Audit Logs

**Path:** Leave > Accrual Audit Logs

**Who can see:**
- **HR/SuperAdmin:** All employees' audit logs
- **Employees:** Only their own audit logs

**Available Filters:**
- Employee name or badge ID
- Date range
- Event type (monthly accrual, annual reset, pause, resume)
- Reason (contains search)

### Reading Audit Log Entries

Each entry shows:
- **Employee** - Badge ID and name
- **Date** - Effective date of the accrual event
- **Type** - Type of event:
  - `monthly_accrual` - Automatic 2.5-day monthly accrual
  - `annual_reset` - December 31 carryforward limit enforcement
  - `accrual_pause_start` - Accrual paused due to unpaid leave
  - `accrual_pause_end` - Accrual resumed after unpaid leave
  - `manual_adjustment` - HR-made correction
- **Old Balance** - Leave balance before the change
- **New Balance** - Leave balance after the change
- **Accrual Days** - Days added (positive) or deducted (negative)
- **Reason** - Detailed reason for the change

### Example Audit Trail

```
Employee: Sarah Johnson (A-015)
------------------------------------------------------------
Date       Type             Old Balance → New Balance  Days  Reason
------------------------------------------------------------
Jan 15     monthly_accrual    0.0 → 2.5              +2.5  Monthly accrual
Feb 15     monthly_accrual    2.5 → 5.0              +2.5  Monthly accrual
Feb 16     accrual_pause      5.0 → 5.0               0.0  Accrual paused: unpaid leave Feb 16-28
Mar 1      accrual_pause_end  5.0 → 5.0               0.0  Accrual resumed after unpaid leave
Mar 15     monthly_accrual    5.0 → 7.5              +2.5  Monthly accrual (adjusted for 14 days unpaid)
Dec 31     annual_reset      47.0 → 30.0            -17.0  Annual reset: kept 30 (mgmt limit), removed 17
```

### Why Audit Logs Matter

✓ **Transparency** - Employees can verify their balance calculations
✓ **Compliance** - Complete trail for audits and HR reviews
✓ **Accuracy** - Track impact of unpaid leave and resets
✓ **Immutable** - Cannot be edited (legal protection)

---

## Employee Service Duration & Accrual Eligibility

### How Service is Calculated

**Formula:**
```
Adjusted Service Days = Total Service Days 
                        - Unpaid Leave Days 
                        - Unauthorized Extension Days
```

**Examples:**

```
Employee: Joined Jan 1, 2024
Reference Date: March 15, 2024

Scenario 1: No unpaid leave
- Total service: 74 days (Jan 1 to Mar 15)
- Adjusted service: 74 days

Scenario 2: 10 days unpaid leave (Feb 1-10)
- Total service: 74 days
- Unpaid leave: -10 days
- Adjusted service: 64 days

Scenario 3: Unauthorized extension (returned 5 days late)
- Total service: 74 days
- Unpaid/unauthorized: -15 days
- Adjusted service: 59 days
```

### Accrual Eligibility Criteria

An employee receives 2.5-day accrual ONLY if ALL conditions are met:

1. **✓ 30+ adjusted service days** (to prevent immediate accrual)
2. **✓ Anniversary month/day** (e.g., Jan 15 for employees joining Jan 15)
3. **✓ Not in accrual pause period** (paused during unpaid leave)
4. **✓ Not already accrued this month** (prevents duplicate accrual)

### Example: Employee Eligibility

```
Employee: Mike Chen (S-033)
Joined: June 15, 2023

Eligibility Timeline:
- July 15: 30+ days ✓, June anniversary ✗ → NO ACCRUAL
- July 16 - next June 14: 30+ days ✓, June anniversary ✗ → NO ACCRUAL
- June 15, 2024: 30+ days ✓, June anniversary ✓, not paused ✓ → ✓ ACCRUAL 2.5 days
- July 15, 2024: Already accrued in June ✓, new month (July) → ✓ ACCRUAL 2.5 days

With unpaid leave:
- Jan 1-15, 2024: Unpaid leave (15 days)
- June 15, 2024: Accrual attempted
  - Service calculation:
    - June 15 2023 to June 15 2024 = 365 days
    - Minus unpaid 15 days = 350 days ✓
  - Still 30+ days ✓, anniversary ✓, not paused ✓ → ✓ ACCRUAL 2.5 days
```

---

## Annual December 31 Reset

### What Happens

On December 31 each year, the system:

1. **Calculates** each employee's total leave balance
2. **Looks up** their category (based on badge ID prefix)
3. **Compares** balance to category limit:
   - Management (A-): Max 30 days
   - Normal (S-, D-, P-, etc.): Max 60 days
4. **Deducts** any excess days and **logs** the change

### Reset Example

```
Employee: Alice Williams (A-020) - Management
Balance before reset: 45 days
Category limit: 30 days
Excess to deduct: 15 days

After Dec 31 reset:
- Balance: 30 days
- Audit log reason: "Annual Carryforward Limit Reset - Management: 
  kept 30 days, removed 15 days"
```

### Important Notes

- ✓ Employees can **exceed limits during the year** (e.g., taking extra leave)
- ✓ Reset only happens **once per year** on December 31
- ✓ Audit logs track the **old balance → new balance → deducted amount**
- ✓ Reset applies to **all leave types** per employee

---

## Scheduler Jobs & Automation

### Monthly Accrual Job

**When:** Every day (checks if accrual is due)
**What:** Checks each employee for accrual eligibility
**Requirement:** APScheduler must be running
**Monitoring:** Check Leave Accrual Audit Logs for "monthly_accrual" entries

### Annual Reset Job

**When:** December 31 only
**What:** Enforces carryforward limits for all employees
**Requirement:** APScheduler must be running
**Monitoring:** Check Leave Accrual Audit Logs on Jan 1 for "annual_reset" entries

### Signal Handlers

When status of Unpaid Leave or Unauthorized Extension changes:
- **Automatic:** Accrual pause/resume triggered
- **No manual action needed**
- **Audit logs created** automatically

---

## HR Checklist

### Monthly Tasks

- [ ] Monitor scheduler logs for accrual errors
- [ ] Review new Unpaid Leave requests
- [ ] Update Unpaid Leave status when employee returns
- [ ] Check audit logs for any anomalies

### Quarterly Tasks

- [ ] Review employee service calculations
- [ ] Verify employee categories are correct
- [ ] Check for any employees with accrual issues
- [ ] Audit sample leave balances

### Annual Tasks (Before December 31)

- [ ] Verify accrual configuration is correct
- [ ] Review all employee categories
- [ ] Notify employees about year-end carryforward limits
- [ ] Prepare for annual reset on Dec 31

### After December 31 Reset

- [ ] Verify reset completed successfully
- [ ] Check audit logs for all reset entries
- [ ] Review any balance reductions
- [ ] Communicate changes to affected employees

---

## Troubleshooting

### Issue: Employee not receiving monthly accrual

**Check:**
1. Has 30+ adjusted service days?
   - Path: Leave > Accrual Audit Logs > Filter by employee
   - Look for service duration in logs

2. Is today their anniversary month?
   - Path: Leave > Employee Categories
   - Joining date: date_joining field
   - Anniversary: same month and day each year

3. Is accrual paused?
   - Path: Leave > Unpaid Leaves
   - Check if employee has active unpaid leave
   - Status should be "Active" (paused) or "Returned" (not paused)

4. Already accrued this month?
   - Path: Leave > Accrual Audit Logs
   - Filter: Employee + Type = "monthly_accrual"
   - Check if entry exists for current month

### Issue: Employee category not recognized

**Fix:**
1. Check badge ID format:
   - Should be "A-###", "S-###", etc.
   - System uses prefix before hyphen

2. Verify category exists:
   - Path: Leave > Employee Categories
   - Create category if missing
   - Badge ID Prefix should match employee's prefix

### Issue: Unpaid leave not pausing accrual

**Check:**
1. Status set to "Active"?
   - Path: Leave > Unpaid Leaves > Edit
   - Status must be "Active" to pause

2. Signal handler working?
   - After saving, check Available Leave record
   - Field `accrual_paused_until` should be set
   - If empty, restart Django app

### Issue: Audit log not appearing

**Check:**
1. Is action recent?
   - Audit logs created in real-time
   - Should appear immediately

2. Check filters:
   - Path: Leave > Accrual Audit Logs
   - Clear all filters
   - Select correct employee
   - Check date range

---

## Reference

### Employee Categories

| Badge Prefix | Category | Carryforward Limit | Notes |
|--------------|----------|-------------------|-------|
| A- | Management | 30 days | Can configure in system |
| S- | Normal Employee | 60 days | Default for most staff |
| D- | Directors | 45 days | Custom category |
| P- | Part Time | 40 days | Custom category |

### Accrual Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Monthly Accrual | 2.5 days | Credited on anniversary date |
| Anniversary Basis | Joining Date | Month and day each year |
| Annual Reset | December 31 | Automatic, enforces category limit |
| Service Eligibility | 30+ days | Minimum before accrual starts |

### Audit Log Types

| Type | Meaning | Who Creates |
|------|---------|-------------|
| `monthly_accrual` | 2.5-day monthly credit | Scheduler job |
| `annual_reset` | December 31 limit enforcement | Scheduler job |
| `accrual_pause_start` | Unpaid leave started | Signal handler |
| `accrual_pause_end` | Unpaid leave ended | Signal handler |
| `manual_adjustment` | HR correction | HR admin |

---

## Support & Questions

For questions about leave accrual policy:
- **Policy Details:** Contact HR Manager
- **System Issues:** Contact IT Support
- **Employee Inquiries:** Direct to HR dashboard or HR team

---

*Royal Falcon Security HRMS - Leave Accrual Policy v1.0*
