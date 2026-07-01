"""
Create (or refresh) the "Operations Manager" group and grant it the
Configuration permissions, so its members can use the Configuration section
(HR aside). HR assigns employees to this group via Groups & Permissions or the
Django admin.

Run once after deploy:  python manage.py setup_operations_manager
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from base.access import OPERATIONS_MANAGER_GROUP

# (app_label, model) of the models exposed in the Configuration menu.
CONFIG_MODELS = [
    ("base", "multipleapprovalcondition"),
    ("base", "multipleapprovalmanagers"),
    ("base", "horillamailtemplate"),
    ("base", "dynamicemailconfiguration"),
    ("base", "holidays"),
    ("base", "companyleaves"),
    ("horilla_automations", "mailautomation"),
    ("leave", "restrictleave"),
]


class Command(BaseCommand):
    help = "Create the Operations Manager group and grant Configuration permissions."

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name=OPERATIONS_MANAGER_GROUP)
        self.stdout.write(
            ("Created" if created else "Found") + f' group "{OPERATIONS_MANAGER_GROUP}".'
        )

        granted = 0
        for app_label, model in CONFIG_MODELS:
            perms = Permission.objects.filter(
                content_type__app_label=app_label, content_type__model=model
            )
            if not perms.exists():
                self.stdout.write(
                    self.style.WARNING(f"  no permissions found for {app_label}.{model}")
                )
                continue
            group.permissions.add(*perms)
            granted += perms.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Granted {granted} Configuration permissions to "
                f'"{OPERATIONS_MANAGER_GROUP}". Assign employees to this group '
                "(Groups & Permissions / Django admin) to give them Configuration access."
            )
        )
