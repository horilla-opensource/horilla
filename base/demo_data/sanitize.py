"""String sanitization helpers for demo catalogs and side fixtures."""

from __future__ import annotations

import logging
from pathlib import Path

from django.apps import apps
from django.db import transaction
from django.db.models import Q

from base.demo_data.catalog import STRING_REPLACEMENTS

logger = logging.getLogger(__name__)


def apply_replacements(text: str | None) -> str | None:
    if text is None:
        return None
    result = text
    for old, new in STRING_REPLACEMENTS:
        if old in result:
            result = result.replace(old, new)
    return result


def scrub_side_fixture_files(load_dir: Path) -> int:
    """
    Scrub vendor strings in side-load JSON fixtures (mail/FAQ) on disk.

    These files are not always loaded by load_demo_data but are imported from
    product UIs, so cleaning the source keeps demos consistent.
    """
    targets = (
        "mail_automations.json",
        "mail_templates.json",
        "faq.json",
        "faq_category.json",
        "tags.json",
    )
    scrubbed = 0
    for name in targets:
        path = load_dir / name
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = apply_replacements(original) or original
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            scrubbed += 1
            logger.info("Scrubbed side fixture: %s", name)
    return scrubbed


@transaction.atomic
def sanitize_loaded_records() -> dict[str, int]:
    """Rewrite informal / vendor-specific labels already loaded into the DB."""
    counts: dict[str, int] = {}

    # Leave restriction titles
    if apps.is_installed("leave"):
        from leave.models import RestrictLeave

        n = 0
        for row in RestrictLeave.objects.filter(
            Q(title__icontains="S/W")
            | Q(title__icontains="Odoo")
            | Q(title__icontains="Engineering.")
            | Q(title__icontains="Dept")
        ):
            new_title = apply_replacements(row.title) or row.title
            new_title = new_title.replace(
                "Engineering. Restriction", "Engineering Restriction"
            )
            new_title = new_title.replace("Engineering. ", "Engineering ")
            if new_title and new_title != row.title:
                row.title = new_title
                row.save(update_fields=["title"])
                n += 1
        counts["restrict_leave"] = n

    # Recruitment survey template + questions
    if apps.is_installed("recruitment"):
        from recruitment.models import RecruitmentSurvey, SurveyTemplate

        n = 0
        for tmpl in SurveyTemplate.objects.filter(
            Q(title__icontains="Odoo") | Q(description__icontains="Odoo")
        ):
            tmpl.title = apply_replacements(tmpl.title) or tmpl.title
            tmpl.description = apply_replacements(tmpl.description)
            # Prefer clean enterprise wording after generic replace
            if "the platform" in (tmpl.title or "").lower() or "Software Engineer" in (
                tmpl.title or ""
            ):
                tmpl.title = "Software Engineer Assessment"
                tmpl.description = (
                    "Structured interview assessment covering software engineering "
                    "fundamentals, backend development, and problem-solving skills."
                )
            tmpl.save()
            n += 1

        QUESTION_MAP = {
            "Have you worked with Odoo's ORM before ?": (
                "Have you worked with an ORM framework before?"
            ),
            "Which Odoo module have you worked on the most?": (
                "Which application modules have you worked on the most?"
            ),
            "Which of the following are key features of OdooÆs ORM?": (
                "Which of the following are key features of a modern ORM?"
            ),
            "Explain how you would customize an Odoo report for a client.": (
                "Explain how you would customize a business report for a client."
            ),
            "How many years of experience do you have working with Odoo?": (
                "How many years of professional software development experience do you have?"
            ),
            "Estimate your proficiency with Python in relation to Odoo development (0-100%).": (
                "Estimate your proficiency with Python (0-100%)."
            ),
            "Rate your experience in using Odoo Studio on a scale of 1 to 5.": (
                "Rate your experience with low-code customization tools on a scale of 1 to 5."
            ),
        }
        for survey in RecruitmentSurvey.objects.all():
            q = survey.question or ""
            new_q = QUESTION_MAP.get(q) or apply_replacements(q)
            if new_q and new_q != q:
                survey.question = new_q
                survey.save(update_fields=["question"])
                n += 1
        counts["recruitment_survey"] = n

    # Projects
    if apps.is_installed("project"):
        from project.models import Project

        n = 0
        for project in Project.objects.filter(
            Q(title__icontains="Horilla")
            | Q(description__icontains="Horilla")
            | Q(title__icontains="Odoo")
        ):
            project.title = apply_replacements(project.title) or project.title
            project.description = apply_replacements(project.description)
            if project.title == "Enterprise HR Platform" or "OpenSource" in (
                project.title or ""
            ):
                project.title = "Enterprise HR Platform"
                project.description = (
                    "Internal platform initiative to modernize HR workflows across "
                    "payroll, attendance, leave, and employee self-service."
                )
            project.save()
            n += 1
        counts["projects"] = n

    # PMS meetings / objectives with brand names
    if apps.is_installed("pms"):
        n = 0
        try:
            from pms.models import Meetings

            for meeting in Meetings.objects.filter(title__icontains="Horilla"):
                meeting.title = apply_replacements(meeting.title) or meeting.title
                meeting.save(update_fields=["title"])
                n += 1
        except Exception:
            pass
        try:
            from pms.models import EmployeeObjective, Objective

            for model in (Objective, EmployeeObjective):
                for obj in model.objects.filter(
                    Q(title__icontains="Horilla") | Q(title__icontains="Odoo")
                ):
                    obj.title = apply_replacements(obj.title) or obj.title
                    obj.save(update_fields=["title"])
                    n += 1
        except Exception:
            pass
        counts["pms"] = n

    return counts
