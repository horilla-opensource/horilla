import os

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dump all relevant data to JSON files."

    def handle(self, *args, **options):

        folder_name = input("Enter the name of the folder to save JSON files: ").strip()
        if not folder_name:
            self.stderr.write(self.style.ERROR("Folder name cannot be empty."))
            return

        dump_dir = os.path.join(settings.BASE_DIR, folder_name)
        os.makedirs(dump_dir, exist_ok=True)

        data_files = [
            ("auth.User", "user_data.json"),
            ("employee.Employee", "employee_info_data.json"),
            ("base", "base_data.json"),
            ("employee.employeeworkinformation", "work_info_data.json"),
            ("employee.employeebankdetails", "bank_info_data.json"),
        ]

        optional_apps = [
            ("attendance", "attendance_data.json"),
            ("leave", "leave_data.json"),
            ("asset", "asset_data.json"),
            ("recruitment", "recruitment_data.json"),
            ("onboarding", "onboarding_data.json"),
            ("offboarding", "offboarding_data.json"),
            ("pms", "pms_data.json"),
            ("payroll", "payroll_data.json"),
            ("payroll", "payroll_loanaccount_data.json"),
            ("project", "project_data.json"),
        ]

        data_files += [
            (app, file) for app, file in optional_apps if django_apps.is_installed(app)
        ]

        for data in data_files:
            output_path = os.path.join(dump_dir, data[1])

            try:
                with open(output_path, "w") as f:
                    call_command("dumpdata", data[0], stdout=f, indent=4)
                self.stdout.write(self.style.SUCCESS(f"Dumped: {data[0]}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error dumping {data[0]}: {e}"))
