# Royal Falcon Security Leave Accrual Policy - Quick Start

## What's New?

This implementation adds a comprehensive custom leave accrual policy for Royal Falcon Security:

✅ **Monthly 2.5-day accrual** on employee anniversary dates
✅ **Employee categories** with carryforward limits (30-60 days)
✅ **Annual December 31 reset** enforcing limits
✅ **Unpaid leave tracking** with automatic accrual pause
✅ **Complete audit trail** for all balance changes
✅ **Login page branding** updated to Royal Falcon Security

---

## Getting Started

### For System Administrators / DevOps

1. **Deploy the code**
   ```bash
   git pull origin main  # Or checkout the socversity-upgraded-tribble branch
   ```

2. **Initialize the system**
   ```bash
   python manage.py migrate              # Apply database migrations
   python manage.py init_royal_falcon_accrual  # Set up categories and config
   ```

3. **Restart services**
   ```bash
   sudo systemctl restart horilla         # Restart Django
   systemctl status horilla               # Verify running
   ```

4. **Verify deployment**
   ```bash
   python manage.py test leave            # Run all tests
   ```

See **DEPLOYMENT_CHECKLIST.md** for complete deployment procedures.

### For HR Administrators

1. **Review the Admin Guide**
   - Path: `ADMIN_GUIDE.md`
   - Learn how to create unpaid leave records
   - Understand annual reset process
   - Read audit logs

2. **Configure employee categories**
   - Navigate: Leave > Employee Categories
   - Verify A-, S-, D-, P- prefixes are set up
   - Adjust carryforward limits if needed

3. **Create first unpaid leave record**
   - Navigate: Leave > Unpaid Leaves > Add New
   - Select employee, start/end dates, reason
   - Set status to "Active" to pause accrual

4. **Monitor audit logs**
   - Navigate: Leave > Accrual Audit Logs
   - Filter by employee or date
   - Verify monthly accrual is running

See **ADMIN_GUIDE.md** for complete procedures.

### For Employees

1. **Review the Employee Guide**
   - Path: `EMPLOYEE_GUIDE.md`
   - Learn how accrual works (2.5 days/month)
   - Understand carryforward limits
   - Read comprehensive FAQ

2. **Check your leave balance**
   - Navigate: Dashboard > Leave > My Leave Balance
   - See current available days
   - View last accrual date

3. **View your accrual history**
   - Navigate: Dashboard > Leave > My Leave History
   - Filter by "Accrual" type
   - See monthly accruals and any pauses

4. **Submit leave request**
   - Navigate: Dashboard > Leave > New Leave Request
   - Select dates and leave type
   - Submit for approval

See **EMPLOYEE_GUIDE.md** for complete information.

---

## Key Features at a Glance

### Monthly Accrual
- Employees receive 2.5 days per month
- Credited on their joining date anniversary
- Example: Joined Feb 10 → Gets 2.5 days every Feb 10

### Carryforward Limits
- **Management (A-):** Max 30 days
- **Normal (S-, D-, P-):** Max 60 days
- Excess removed automatically on December 31

### Unpaid Leave
- HR creates record when employee takes unpaid time
- Accrual automatically pauses during unpaid period
- Service calculation excludes unpaid days
- Resumes automatically when employee returns

### Audit Logs
- Every accrual event is logged
- Logs are immutable (cannot be edited)
- Employees see their own, HR sees all
- Shows: date, type, old balance → new balance, reason

### Automation
- Monthly accrual: APScheduler job runs daily
- Annual reset: APScheduler job runs Dec 31
- Unpaid leave pause/resume: Automatic via signals
- No manual intervention needed

---

## File Structure

### New/Updated Files

**Models:**
- `leave/models.py` - 6 new models, 2 extended

**Business Logic:**
- `leave/accrual_service.py` - 7 core functions (NEW)
- `leave/scheduler.py` - Monthly/annual jobs (UPDATED)
- `leave/signals.py` - Automation (UPDATED)

**Admin Interface:**
- `leave/cbv/` - 4 modules with 15 views (NEW)
- `leave/forms.py` - 3 new forms (UPDATED)
- `leave/filters.py` - 3 new filters (UPDATED)
- `leave/templates/cbv/leave_accrual/` - 15 templates (NEW)
- `leave/urls.py` - 18 new routes (UPDATED)

**Management:**
- `leave/management/commands/init_royal_falcon_accrual.py` (NEW)

**Testing:**
- `leave/tests.py` - 25+ unit tests (UPDATED)
- `leave/integration_tests.py` - 20+ integration tests (NEW)

**Documentation:**
- `ADMIN_GUIDE.md` - 14KB procedures (NEW)
- `EMPLOYEE_GUIDE.md` - 15KB guide (NEW)
- `DEPLOYMENT_CHECKLIST.md` - 14KB checklist (NEW)
- `IMPLEMENTATION_SUMMARY.md` - 21KB summary (NEW)

---

## Database Changes

### New Tables

| Table | Purpose |
|-------|---------|
| leave_employeecategory | Employee categories (A-, S-, etc.) |
| leave_leaveaccrualconfiguration | Accrual settings (2.5 days, reset date) |
| leave_unpaidleave | Unpaid leave records |
| leave_unauthorizedextension | Late return tracking |
| leave_leaveaccruaauditlog | Immutable audit trail |
| leave_employeeserviceadjustment | Service adjustments tracking |

### Modified Tables

- **employee_employee:** Added original_joining_date, adjusted_service_start_date
- **leave_availableleave:** Added last_accrual_date, accrual_paused_until

All changes are **reversible** via migrations.

---

## Testing

### Run All Tests

```bash
python manage.py test leave
python manage.py test leave.integration_tests
```

### Run Specific Tests

```bash
python manage.py test leave.tests.TestEmployeeCategoryDetection
python manage.py test leave.integration_tests.TestMonthlyAccrualScheduler
```

### Test Coverage

- **Unit Tests:** Category detection, anniversary month, service calculation, immutability
- **Integration Tests:** Scheduler jobs, multi-employee scenarios, signal handlers

Total: 45+ test cases

---

## Common Tasks

### Create Unpaid Leave Record (HR Only)

1. Navigate: **Leave > Unpaid Leaves > Add New**
2. Fill in:
   - Employee: Select from dropdown
   - Start Date: First day of unpaid leave
   - End Date: Last day of unpaid leave
   - Reason: e.g., "Medical emergency"
   - Status: "Active"
3. Save
4. Result: Accrual automatically paused

### Approve Return from Unpaid Leave

1. Navigate: **Leave > Unpaid Leaves > Select Record**
2. Change Status to "Returned"
3. Save
4. Result: Accrual automatically resumes

### View Accrual Audit Logs

1. Navigate: **Leave > Accrual Audit Logs**
2. Filter by:
   - Employee
   - Date range
   - Event type (monthly_accrual, annual_reset, etc.)
3. View details for each entry

### Check Employee Service Duration

```bash
python manage.py shell << EOF
from employee.models import Employee
from leave.accrual_service import calculate_adjusted_service_days
emp = Employee.objects.get(badge_id="S-042")
service = calculate_adjusted_service_days(emp)
print(f"Service days: {service}")
EOF
```

---

## Troubleshooting

### "Accrual not received on anniversary date"

**Check:**
1. Does employee have 30+ days of service?
2. Are they currently on unpaid leave?
3. Did they already accrue this month?

```bash
python manage.py shell << EOF
from employee.models import Employee
from leave.accrual_service import is_service_eligible_for_accrual
emp = Employee.objects.get(badge_id="S-001")
eligible = is_service_eligible_for_accrual(emp)
print(f"Eligible: {eligible}")
EOF
```

### "Scheduler job not running"

1. Verify APScheduler is running:
   ```bash
   ps aux | grep scheduler
   ```

2. Restart scheduler:
   ```bash
   python manage.py shell -c "from leave.scheduler import register_leave_scheduler; register_leave_scheduler()"
   ```

3. Check logs:
   ```bash
   tail -f /var/log/horilla/django.log
   ```

### "Employee balance seems incorrect"

1. Check audit log for that employee
2. Verify service calculation:
   ```bash
   python manage.py shell << EOF
   from employee.models import Employee
   from leave.accrual_service import calculate_adjusted_service_days
   emp = Employee.objects.get(badge_id="S-001")
   service = calculate_adjusted_service_days(emp)
   print(f"Adjusted service: {service} days")
   EOF
   ```

3. Check for unpaid/unauthorized leaves:
   ```bash
   python manage.py shell << EOF
   from leave.models import UnpaidLeave, UnauthorizedExtension
   from employee.models import Employee
   emp = Employee.objects.get(badge_id="S-001")
   unpaid = UnpaidLeave.objects.filter(employee_id=emp, status='active')
   print(f"Active unpaid leaves: {unpaid.count()}")
   EOF
   ```

See **ADMIN_GUIDE.md** for more troubleshooting.

---

## Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| ADMIN_GUIDE.md | Procedures and processes | HR/Admin |
| EMPLOYEE_GUIDE.md | FAQ and how-to | Employees |
| DEPLOYMENT_CHECKLIST.md | Deployment steps | DevOps/IT |
| IMPLEMENTATION_SUMMARY.md | Technical details | Developers |
| README.md | Quick start (this file) | Everyone |

---

## Version Info

- **Policy Version:** 1.0
- **Release Date:** 2024
- **Company:** Royal Falcon Security
- **Status:** Production Ready ✅

---

## Support

**For HR/Admin questions:**
- Contact: HR Manager
- See: ADMIN_GUIDE.md

**For Employee questions:**
- Contact: HR team or Dashboard Help
- See: EMPLOYEE_GUIDE.md

**For Technical/IT issues:**
- Contact: IT Support
- See: DEPLOYMENT_CHECKLIST.md

**For Development:**
- See: IMPLEMENTATION_SUMMARY.md
- See: Code comments in leave/accrual_service.py

---

## Next Steps

### Day 1: Post-Deployment
- [ ] Verify scheduler is running
- [ ] Test login page branding
- [ ] Create test unpaid leave record
- [ ] Monitor logs for errors

### Week 1
- [ ] HR team trained on new features
- [ ] Employees notified of new system
- [ ] Verify accrual is running
- [ ] Monitor for issues

### Month 1
- [ ] Review accrual logs
- [ ] Spot-check employee balances
- [ ] Monitor scheduler performance
- [ ] Gather feedback

### Before Dec 31
- [ ] Prepare for annual reset
- [ ] Communicate limits to employees
- [ ] Review reset logic
- [ ] Final backup

---

*Royal Falcon Security HRMS - Leave Accrual Policy v1.0*
*Quick Start Guide - For detailed information see documentation files*
