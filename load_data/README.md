# Demo data

Enterprise demo fixtures and the post-load seeder used by Horilla HR.

## Load

```bash
# Full reset (destructive)
python manage.py load_demo_data --flush --no-input

# Or from the login screen: "Load Demo Data"
```

## What happens

1. Copies icons (`load_data/icons/`) and avatars (`load_data/avatars/`) into `MEDIA_ROOT`
2. Loads JSON fixtures in dependency order with dates shifted to the current month
3. Runs `run_enterprise_demo_seeder()`:
   - Activates `Your Company` / `Your Company Inc.` / `Your Company Ltd.`
   - Renames departments and job titles to standard enterprise names (PKs preserved)
   - Refreshes announcements with relative dates/copy
   - Scrubs vendor-specific labels (e.g. Odoo/Cybrosys leftovers)
4. Re-anchors demo payslips (`Demo Payroll M-n`)
5. Assigns demo role memberships (`base/demo_roles.py`)

## People layer

`user_data.json`, `employee_info_data.json`, and avatars are the source of truth for
employees. The seeder does **not** recreate people — it only standardizes org
taxonomy and module catalogs around them.

## Fixture hygiene

Catalog fixtures (`base_data`, `recruitment_data`, `project_data`, `leave_data`,
`pms_data`) already ship with enterprise-standard labels and active companies.
The seeder remains as an idempotent safety net and for **dynamic** steps
(relative announcement dates, payslip month re-anchor, media copy, demo roles).
