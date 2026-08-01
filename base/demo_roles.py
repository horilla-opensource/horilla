"""
Demo-data helpers for role (user group) assignments.

Groups are created by post_migrate (see base.signals._DEFAULT_HRMS_GROUPS),
so membership is applied by group *name* after fixtures load — never by PK.
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import Group
from django.db import transaction

from base.models import Company, CompanyGroupAssignment
from horilla_auth.models import HorillaUser

logger = logging.getLogger(__name__)

# (user email, group name, company name)
# Keep this small — enough to demo Roles & Permissions and company-scoped access.
DEMO_ROLE_ASSIGNMENTS = (
    ("alexander.smith@horilla.com", "Asset Manager", "Your Company"),
    ("alexander.smith@horilla.com", "Asset Manager", "Your Company Inc."),
    ("michael.brown@horilla.com", "HR Manager", "Your Company"),
    ("sarah.anderson@horilla.com", "Payroll Manager", "Your Company"),
    ("emily.clark@horilla.com", "Leave Manager", "Your Company"),
    ("jessica.evans@horilla.com", "Attendance Manager", "Your Company"),
    ("benjamin.parker@horilla.com", "Recruiter", "Your Company Ltd."),
    ("lily.campbell@horilla.com", "Helpdesk Agent", "Your Company Inc."),
    ("matthew.harris@horilla.com", "Performance Manager", "Your Company"),
    ("david.king@horilla.com", "Project Manager", "Your Company"),
)


@transaction.atomic
def assign_demo_user_groups():
    """
    Assign a few demo employees to default HRMS roles.

    Safe to call repeatedly (get_or_create). Skips missing users/groups/companies.
    Syncs ``user.groups`` so legacy (non-scoped) mode still works.
    """
    created = 0
    for email, group_name, company_name in DEMO_ROLE_ASSIGNMENTS:
        user = HorillaUser.objects.filter(email=email).first()
        if not user:
            user = HorillaUser.objects.filter(username=email).first()
        group = Group.objects.filter(name=group_name).first()
        company = Company.objects.filter(company=company_name).first()
        if not user or not group or not company:
            logger.debug(
                "Skipping demo role assignment %s / %s / %s (missing user=%s group=%s company=%s)",
                email,
                group_name,
                company_name,
                bool(user),
                bool(group),
                bool(company),
            )
            continue
        _, was_created = CompanyGroupAssignment.objects.get_or_create(
            user=user,
            group=group,
            company=company,
        )
        CompanyGroupAssignment.sync_user_group_membership(user, group)
        if was_created:
            created += 1
    return created
