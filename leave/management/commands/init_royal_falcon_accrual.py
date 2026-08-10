"""
Management command to initialize Royal Falcon Security leave accrual policy data.
- Creates default EmployeeCategory records (Management & Normal)
- Creates default LeaveAccrualConfiguration for all companies
- Populates Employee.original_joining_date from existing date_joining

Usage: python manage.py init_royal_falcon_accrual
"""

from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.models import Company
from employee.models import Employee
from leave.models import EmployeeCategory, LeaveAccrualConfiguration


class Command(BaseCommand):
    """Initialize Royal Falcon Security leave accrual policy."""

    help = "Initialize Royal Falcon Security leave accrual policy data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset and reinitialize all data (destructive)",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        dry_run = options.get("dry_run", False)
        reset = options.get("reset", False)

        self.stdout.write(
            self.style.WARNING(
                "Royal Falcon Security Leave Accrual Policy - Initialization"
            )
        )
        self.stdout.write("-" * 60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No changes will be made")
            )
            self.stdout.write("-" * 60)

        if reset:
            if not dry_run:
                confirm = input(
                    "WARNING: This will DELETE all existing EmployeeCategory and "
                    "LeaveAccrualConfiguration records. Continue? (yes/no): "
                )
                if confirm.lower() != "yes":
                    self.stdout.write(self.style.ERROR("Aborted."))
                    return

            if not dry_run:
                with transaction.atomic():
                    EmployeeCategory.objects.all().delete()
                    LeaveAccrualConfiguration.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS("Deleted existing records.")
                    )
            else:
                self.stdout.write("Would delete all EmployeeCategory records")
                self.stdout.write("Would delete all LeaveAccrualConfiguration records")

        # 1. Create employee categories for each company
        self.stdout.write("\n[1] Creating Employee Categories...")
        categories_created = 0

        for company in Company.objects.all():
            # Management category (A prefix)
            mgmt_cat, created = EmployeeCategory.objects.get_or_create(
                company_id=company,
                badge_id_prefix="A",
                defaults={
                    "name": "Management",
                    "max_carryforward_days": 30,
                },
            )
            if created and not dry_run:
                categories_created += 1
                self.stdout.write(
                    f"  ✓ Created Management category for {company.company_name}"
                )

            # Normal Employee category (S prefix)
            normal_cat, created = EmployeeCategory.objects.get_or_create(
                company_id=company,
                badge_id_prefix="S",
                defaults={
                    "name": "Normal Employee",
                    "max_carryforward_days": 60,
                },
            )
            if created and not dry_run:
                categories_created += 1
                self.stdout.write(
                    f"  ✓ Created Normal Employee category for {company.company_name}"
                )

            # Other common prefixes (can be customized later)
            for prefix, name, limit in [
                ("D", "Directors", 45),
                ("P", "Part Time", 40),
            ]:
                cat, created = EmployeeCategory.objects.get_or_create(
                    company_id=company,
                    badge_id_prefix=prefix,
                    defaults={
                        "name": name,
                        "max_carryforward_days": limit,
                    },
                )
                if created and not dry_run:
                    categories_created += 1
                    self.stdout.write(
                        f"  ✓ Created {name} category for {company.company_name}"
                    )

        if dry_run:
            self.stdout.write(f"Would create ~3 categories per company")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created {categories_created} categories")
            )

        # 2. Create LeaveAccrualConfiguration for each company
        self.stdout.write("\n[2] Creating Leave Accrual Configuration...")
        config_created = 0

        for company in Company.objects.all():
            config, created = LeaveAccrualConfiguration.objects.get_or_create(
                company_id=company,
                defaults={
                    "monthly_accrual_days": 2.5,
                    "annual_reset_month": 12,
                    "annual_reset_day": 31,
                    "is_active": True,
                },
            )
            if created and not dry_run:
                config_created += 1
                self.stdout.write(
                    f"  ✓ Created accrual config for {company.company_name}: "
                    f"2.5 days/month, reset Dec 31"
                )

        if dry_run:
            self.stdout.write(f"Would create config for each company")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created {config_created} configurations")
            )

        # 3. Populate Employee.original_joining_date
        self.stdout.write("\n[3] Populating Employee.original_joining_date...")
        updated_count = 0

        for employee in Employee.objects.filter(original_joining_date__isnull=True):
            try:
                work_info = employee.employee_work_info
                if work_info and work_info.date_joining:
                    if not dry_run:
                        employee.original_joining_date = work_info.date_joining
                        employee.save(update_fields=["original_joining_date"])
                    updated_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ✗ Could not update {employee.badge_id}: {str(e)}"
                    )
                )

        if dry_run:
            self.stdout.write(f"Would update ~{updated_count} employees")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Updated {updated_count} employees with original_joining_date"
                )
            )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✓ Initialization Complete!"))
        self.stdout.write("\nNext Steps:")
        self.stdout.write("  1. Verify employee categories are correct")
        self.stdout.write("  2. Review accrual configuration settings")
        self.stdout.write("  3. Run tests: python manage.py test leave")
        self.stdout.write("  4. Deploy to staging for UAT")
