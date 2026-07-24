"""
audit_perms — snapshot effective permissions per user (optionally per company).

Used as the verification harness for the company-scoped permissions rollout:
capture a baseline before any change, then diff after each phase.

Usage:
    python manage.py audit_perms                          # all active users, current (global) perms
    python manage.py audit_perms --output baseline.json   # save to file
    python manage.py audit_perms --user adam              # single user
    python manage.py audit_perms --per-company            # repeat per company (after scoping lands)
"""

import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from base.models import Company
from horilla.horilla_middlewares import set_selected_company


def _fresh_user(user_id):
    """Fetch a fresh user instance so Django's per-instance perm cache is empty."""
    return get_user_model().objects.get(id=user_id)


def _perms_for(user):
    return sorted(user.get_all_permissions())


class Command(BaseCommand):
    help = (
        "Dump effective permission codenames per user (optionally per company) as JSON."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Limit to a single username")
        parser.add_argument(
            "--output", help="Write JSON to this file instead of stdout"
        )
        parser.add_argument(
            "--per-company",
            action="store_true",
            help="Compute permissions once per company (sets the company context var per pass)",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Include inactive users",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all().order_by("username")
        if not options["include_inactive"]:
            users = users.filter(is_active=True)
        if options["user"]:
            users = users.filter(username=options["user"])

        result = {}
        user_ids = list(users.values_list("id", "username"))

        if options["per_company"]:
            companies = list(Company.objects.all().order_by("id"))
            for user_id, username in user_ids:
                per_company = {}
                for company in companies:
                    set_selected_company(str(company.id))
                    per_company[f"{company.id}:{company.company}"] = _perms_for(
                        _fresh_user(user_id)
                    )
                set_selected_company(None)
                per_company["_no_company_context"] = _perms_for(_fresh_user(user_id))
                result[username] = per_company
        else:
            set_selected_company(None)
            for user_id, username in user_ids:
                result[username] = _perms_for(_fresh_user(user_id))

        payload = json.dumps(result, indent=2, sort_keys=True)
        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as fh:
                fh.write(payload)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Wrote permissions for {len(result)} user(s) to {options['output']}"
                )
            )
        else:
            self.stdout.write(payload)
