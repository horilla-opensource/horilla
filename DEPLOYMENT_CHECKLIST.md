# Royal Falcon Security Leave Accrual - Deployment Checklist

## Pre-Deployment: Database & Code

### Code Preparation
- [x] Phase 1 - Foundation models created
- [x] Phase 2 - Scheduler logic implemented
- [x] Phase 3 - Admin interfaces created
- [x] All 15 HTML templates completed
- [x] Comprehensive unit tests created (25+ tests)
- [x] Integration tests for scheduler jobs (20+ tests)
- [x] Login page branded as Royal Falcon Security
- [x] Management command for initialization
- [x] Admin documentation completed
- [x] Employee documentation completed

### Database Preparation
- [ ] Backup production database
- [ ] Test backup restoration
- [ ] Schedule database maintenance window
- [ ] Prepare rollback procedure
- [ ] Verify Django permissions system is configured

### Testing
- [ ] Run full unit test suite: `python manage.py test leave`
- [ ] Run integration tests: `python manage.py test leave.integration_tests`
- [ ] Manual QA in staging environment
- [ ] Test with different employee categories (A-, S-, D-, P-)
- [ ] Test unpaid leave workflow end-to-end
- [ ] Test annual reset logic (can mock December 31)
- [ ] Verify audit logs are immutable

---

## Deployment Execution (Change Window)

### 1. Pre-Deployment Verification (15 min)

```bash
# Verify code is clean
git status  # Should show no uncommitted changes

# Run quick tests
python manage.py test leave --keepdb

# Check Django settings
python manage.py check

# Verify APScheduler is configured
python manage.py shell -c "from leave.scheduler import register_leave_scheduler; print('Scheduler configured')"
```

### 2. Database Migration (30 min)

```bash
# Run all migrations
python manage.py migrate

# Expected result:
# - New tables created for all 6 accrual models
# - Employee and AvailableLeave tables extended
# - No errors or warnings

# Verify migrations applied
python manage.py showmigrations leave
# Should show all migrations marked as [X] applied
```

### 3. Initialize Accrual Configuration (10 min)

```bash
# Run initialization command
python manage.py init_royal_falcon_accrual

# Expected output:
# ✓ Created employee categories (Management, Normal, Directors, Part Time)
# ✓ Created leave accrual configuration
# ✓ Populated Employee.original_joining_date for existing employees
# ✓ Initialization Complete!
```

### 4. Restart Services (10 min)

```bash
# Restart Django app server
sudo systemctl restart horilla

# Verify services are running
sudo systemctl status horilla  # Should show "active (running)"

# Check APScheduler started
python manage.py shell -c "from leave.scheduler import is_scheduler_running; print('Running' if is_scheduler_running() else 'Not running')"

# Restart APScheduler if needed
python manage.py shell -c "from leave.scheduler import register_leave_scheduler; register_leave_scheduler()"
```

### 5. Quick Verification (15 min)

```bash
# Check data was initialized
python manage.py shell << EOF
from leave.models import EmployeeCategory, LeaveAccrualConfiguration
print(f"Categories: {EmployeeCategory.objects.count()}")
print(f"Configurations: {LeaveAccrualConfiguration.objects.count()}")

# Should show:
# Categories: 4
# Configurations: 1 (or more if multi-company)
EOF

# Verify Employee records updated
python manage.py shell << EOF
from employee.models import Employee
emp_with_date = Employee.objects.filter(original_joining_date__isnull=False).count()
print(f"Employees with original_joining_date: {emp_with_date}")
EOF

# Test scheduler jobs don't have errors
python manage.py shell << EOF
from leave.scheduler import leave_monthly_accrual, leave_annual_reset
print("Accrual scheduler imported successfully")
print("Annual reset scheduler imported successfully")
EOF
```

---

## Post-Deployment: Verification (24 hours)

### Day 1 - Immediate Verification

**Checklist:**
- [ ] Login page shows "Royal Falcon Security" branding
- [ ] Dashboard loads without errors
- [ ] Leave module accessible
- [ ] Admin can access Leave > Employee Categories
- [ ] Admin can access Leave > Accrual Configuration
- [ ] Admin can create new unpaid leave record
- [ ] Admin can view accrual audit logs
- [ ] Employees can see their leave balance

**Test Accounts:**
- [ ] Login as HR user → See all audit logs
- [ ] Login as employee → See only own logs
- [ ] Login as manager → See own leave, not others'

### Day 1 - Monitoring

**Check logs for errors:**

```bash
# Django error log
tail -f /var/log/horilla/django.log | grep -i "error\|exception\|traceback"

# APScheduler log (if configured)
tail -f /var/log/horilla/scheduler.log

# System log
sudo journalctl -u horilla -f
```

**Look for:**
- Migration errors
- Scheduler job failures
- Permission denied errors
- Database connection issues

### Day 2-3 - Functional Verification

**If today is NOT December 31:**
- [ ] Verify scheduler logs show monthly accrual attempts
- [ ] Check Leave > Accrual Audit Logs for today's entries
- [ ] Verify monthly accrual ran for eligible employees

**Create test unpaid leave:**
- [ ] Create new unpaid leave for a test employee
- [ ] Verify accrual_paused_until is set
- [ ] Change status to "Returned"
- [ ] Verify accrual_paused_until is cleared
- [ ] Check audit logs for pause/resume entries

**Test authorization:**
- [ ] Employee tries to create unpaid leave → Denied
- [ ] Manager tries to edit employee category → Denied
- [ ] HR creates unpaid leave → Allowed
- [ ] SuperAdmin creates unpaid leave → Allowed

---

## During First Month (December)

### Monitor Accrual Schedule

**Daily:**
- [ ] Check scheduler logs for monthly accrual runs
- [ ] Verify no errors in django.log
- [ ] Spot check 2-3 employee balances

**Weekly:**
- [ ] Review accrual audit logs for unusual patterns
- [ ] Check for any employee with service < 30 days
- [ ] Verify unpaid leaves are properly tracking dates

**If Issues Found:**
- [ ] Review audit logs to understand what happened
- [ ] Check employee service calculation: 
  ```bash
  python manage.py shell << EOF
  from employee.models import Employee
  from leave.accrual_service import calculate_adjusted_service_days
  emp = Employee.objects.get(badge_id="S-001")
  service = calculate_adjusted_service_days(emp)
  print(f"Service days: {service}")
  EOF
  ```
- [ ] Contact support if scheduler not running

### December 31 Preparation

**December 20:**
- [ ] Notify all employees about year-end carryforward limits
- [ ] Send guide showing impact on each category
- [ ] HR reviews employees at/near limit
- [ ] Plan for employees who will lose leave

**December 30:**
- [ ] Final backup of database
- [ ] Verify accrual configuration is active
- [ ] Ensure scheduler is running

**December 31:**
- [ ] Monitor scheduler logs during reset
- [ ] Check for errors immediately after midnight
- [ ] Verify audit logs show reset entries

**January 1:**
- [ ] Verify all employees' balances are correct
- [ ] Spot-check 5-10 audit logs for reset entries
- [ ] Confirm any deductions are logged

---

## Troubleshooting

### Issue: "Authentication permission denied" for accrual views

**Solution:**
```bash
# Verify permissions are set up
python manage.py shell << EOF
from django.contrib.auth.models import Permission
perms = Permission.objects.filter(content_type__app_label='leave')
for p in perms:
    print(f"{p.content_type.model}: {p.codename}")
EOF

# Should include: add_unpaidleave, change_unpaidleave, view_unpaidleave, etc.
```

### Issue: Scheduler job failed / accrual not received

**Check:**
1. Scheduler is running:
   ```bash
   ps aux | grep scheduler
   ```

2. Job is registered:
   ```bash
   python manage.py shell -c "from leave.scheduler import SCHEDULER; print(SCHEDULER.get_jobs())"
   ```

3. No permission errors:
   ```bash
   tail -f /var/log/horilla/django.log | grep "leave_monthly_accrual"
   ```

4. Employee is eligible:
   ```bash
   python manage.py shell << EOF
   from employee.models import Employee
   from leave.accrual_service import is_service_eligible_for_accrual
   emp = Employee.objects.get(badge_id="S-001")
   eligible = is_service_eligible_for_accrual(emp)
   print(f"Eligible: {eligible}")
   EOF
   ```

### Issue: December 31 reset didn't run

**Solution:**
```bash
# Manually run annual reset for testing
python manage.py shell << EOF
from leave.scheduler import leave_annual_reset
from datetime import date
print(f"Running reset check for {date.today()}")
leave_annual_reset()
print("Reset check complete")
EOF

# Check audit logs for "annual_reset" entries
# Should show old_balance → new_balance adjustments
```

### Issue: Audit logs can be edited (shouldn't be possible)

**Solution:**
```bash
# Verify audit log save() method has validation
python manage.py shell << EOF
from leave.models import LeaveAccrualAuditLog
import inspect
print(inspect.getsource(LeaveAccrualAuditLog.save))
# Should show ValidationError if pk exists
EOF
```

---

## Rollback Procedure

If critical issues found:

### Immediate Rollback (within 24 hours)

```bash
# 1. Stop all applications
sudo systemctl stop horilla
sudo systemctl stop celery  # if using celery

# 2. Restore database from backup
mysql horilla < /path/to/backup_pre_deployment.sql

# 3. Revert code to previous commit
git checkout HEAD~1

# 4. Restart services
sudo systemctl start horilla
sudo systemctl start celery

# 5. Verify system is operational
curl http://localhost/dashboard  # Should load
```

### Partial Rollback (keep accrual, revert code)

```bash
# 1. Stop services
sudo systemctl stop horilla

# 2. Revert to previous version
git checkout HEAD~1

# 3. Clear Django cache
python manage.py clear_cache

# 4. Restart
sudo systemctl start horilla

# Note: Database changes remain, code reverted
# Accrual data is preserved but new features unavailable
```

---

## Performance Monitoring

### Monitor These Metrics

**Database:**
- [ ] Query execution time < 100ms for audit log queries
- [ ] No long-running transactions during accrual job
- [ ] LeaveAccrualAuditLog table < 100K rows (first year)

**Scheduler:**
- [ ] Monthly accrual job completes in < 5 minutes
- [ ] No missed jobs in scheduler log
- [ ] Signal handlers execute immediately (< 1 second)

**Application:**
- [ ] Leave module page load time < 2 seconds
- [ ] Admin views respond in < 3 seconds
- [ ] No memory leaks in Python process

**Queries:**

```bash
# Monitor slow queries
mysql -u root -p -e "SET GLOBAL slow_query_log = 'ON'; SET GLOBAL long_query_time = 1;"

# Check audit log table size
mysql -u root -p horilla -e "SELECT COUNT(*) FROM leave_leaveaccruaauditlog;"

# Monitor active connections
mysql -u root -p -e "SHOW PROCESSLIST;"
```

---

## Post-Deployment Support

### First Week Support
- [ ] HR team trained on new unpaid leave workflow
- [ ] HR team trained on interpreting audit logs
- [ ] Support team knows how to check employee accrual
- [ ] Escalation path clear for issues

### Ongoing Monitoring
- [ ] Weekly review of accrual logs for anomalies
- [ ] Monthly report of accrual events
- [ ] Quarterly audit of employee service calculations
- [ ] Annual review before next December 31 reset

### Documentation
- [ ] ADMIN_GUIDE.md provided to HR team
- [ ] EMPLOYEE_GUIDE.md provided to all employees
- [ ] Dashboard help links updated
- [ ] FAQ maintained and updated as questions arise

---

## Sign-Off

**Deployment Checklist Completion:**

- [ ] Code all committed and pushed
- [ ] All migrations applied successfully
- [ ] Initialization command ran without errors
- [ ] Services restarted and verified
- [ ] Post-deployment verification passed
- [ ] HR team trained and ready
- [ ] Employees notified of new features
- [ ] Monitoring in place
- [ ] Support procedures established

**Approved By:**

- Project Manager: _________________ Date: _______
- IT Lead: _________________ Date: _______
- HR Manager: _________________ Date: _______
- Development Lead: _________________ Date: _______

---

## Success Criteria

✅ All tests passing (unit + integration)
✅ Zero permission errors for authorized users
✅ Audit logs created for all accrual events
✅ Immutability enforcement working (no edits/deletes)
✅ Scheduler jobs running successfully
✅ Employee categories correctly determined from badge ID
✅ Unpaid leave pause/resume working
✅ Annual reset logic functioning (mock or wait for Dec 31)
✅ Login page branded as Royal Falcon Security
✅ All users can access their respective views

---

## Appendix: Useful Commands

### Run Tests

```bash
# All leave tests
python manage.py test leave

# Just unit tests
python manage.py test leave.tests

# Just integration tests
python manage.py test leave.integration_tests

# Specific test class
python manage.py test leave.tests.TestEmployeeCategoryDetection

# With verbose output
python manage.py test leave -v 2
```

### Debug Accrual Issues

```bash
# Check a specific employee's accrual eligibility
python manage.py shell << EOF
from employee.models import Employee
from leave.accrual_service import (
    is_service_eligible_for_accrual,
    calculate_adjusted_service_days,
    is_anniversary_month,
    get_employee_category
)
emp = Employee.objects.get(badge_id="S-001")
print(f"Employee: {emp.badge_id}")
print(f"Category: {get_employee_category(emp).name}")
print(f"Service days: {calculate_adjusted_service_days(emp)}")
print(f"Anniversary month: {is_anniversary_month(emp)}")
print(f"Eligible: {is_service_eligible_for_accrual(emp)}")
EOF

# View scheduler status
python manage.py shell << EOF
from leave.scheduler import SCHEDULER
for job in SCHEDULER.get_jobs():
    print(f"Job: {job.name}")
    print(f"  Next run: {job.next_run_time}")
    print(f"  Trigger: {job.trigger}")
EOF

# Run monthly accrual manually (for testing)
python manage.py shell << EOF
from leave.scheduler import leave_monthly_accrual
print("Running monthly accrual check...")
leave_monthly_accrual()
print("Complete")
EOF
```

---

*Royal Falcon Security HRMS - Deployment Checklist v1.0*
*Last Updated: 2024*
