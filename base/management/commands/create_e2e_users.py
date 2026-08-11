"""
Horilla management command to create/ensure the E2E test users used by
tests/e2e/ (feature 002-instrument-i18n-strings), one preconfigured with
Português (Brasil) and the other with Inglês (padrão).
"""

from django.core.management.base import BaseCommand

from employee.models import Employee
from horilla_auth.models import HorillaUser

E2E_USERS = [
    {
        "username": "e2e_ptbr",
        "password": "e2e_ptbr_password",
        "email": "e2e_ptbr@example.com",
        "first_name": "E2E",
        "last_name": "PtBr",
        "phone": "0000000001",
    },
    {
        "username": "e2e_en",
        "password": "e2e_en_password",
        "email": "e2e_en@example.com",
        "first_name": "E2E",
        "last_name": "En",
        "phone": "0000000002",
    },
]


class Command(BaseCommand):
    """Creates/ensures the E2E test users used by tests/e2e/ (feature 002)."""

    help = "Creates or ensures the e2e_ptbr and e2e_en test users used by tests/e2e/"

    def handle(self, *args, **options):
        for spec in E2E_USERS:
            if HorillaUser.objects.filter(username=spec["username"]).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{spec["username"]}" already exists')
                )
                continue

            user = HorillaUser.objects.create_superuser(
                username=spec["username"],
                email=spec["email"],
                password=spec["password"],
            )
            employee = Employee()
            employee.employee_user_id = user
            employee.employee_first_name = spec["first_name"]
            employee.employee_last_name = spec["last_name"]
            employee.email = spec["email"]
            employee.phone = spec["phone"]
            employee.save()

            self.stdout.write(
                self.style.SUCCESS(f'User "{spec["username"]}" created successfully')
            )
