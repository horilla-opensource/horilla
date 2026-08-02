"""Rewrite announcements with relative, enterprise-standard copy."""

from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta

from django.db import transaction

from base.models import Announcement

logger = logging.getLogger(__name__)


def _relative_announcements(today: date) -> list[dict]:
    """Build announcement payloads keyed by existing demo PKs 1–10."""
    month_name = calendar.month_name[today.month]
    year = today.year
    # Derive a stable “previous quarter” label
    prev_q = ((today.month - 1) // 3) or 4
    prev_q_year = year if today.month > 3 else year - 1
    next_month = today.month % 12 + 1
    next_month_name = calendar.month_name[next_month]
    next_month_year = year if today.month < 12 else year + 1

    family_day = today + timedelta(days=24)
    training_deadline = today + timedelta(days=18)
    encash_deadline = today + timedelta(days=13)

    return [
        {
            "pk": 1,
            "title": f"Q{prev_q} {prev_q_year} Performance Highlights — Thank You, Team!",
            "description": (
                f"<p><strong>Dear Team,</strong></p>"
                f"<p>We are pleased to share that <strong>Q{prev_q} {prev_q_year} "
                f"was a strong quarter</strong> across all companies:</p>"
                "<ul>"
                "<li>Revenue target exceeded by <strong>18%</strong></li>"
                "<li>Customer satisfaction score reached <strong>4.7 / 5.0</strong></li>"
                "<li>On-time delivery improved to <strong>94%</strong></li>"
                "<li>Employee retention at <strong>96%</strong></li>"
                "</ul>"
                "<p>Thank you for your dedication and collaboration.</p>"
                "<p><em>— The Leadership Team</em></p>"
            ),
            "expire_date": today + timedelta(days=45),
        },
        {
            "pk": 2,
            "title": f"Mid-Year Performance Reviews — {month_name} {year}",
            "description": (
                f"<p><strong>Mid-year performance reviews for {month_name} {year} "
                f"are now open.</strong></p>"
                "<p>Please complete self-assessments and schedule 1-on-1 discussions "
                "with your manager before month end.</p>"
                "<p>Guidelines are available under Performance → Reviews.</p>"
            ),
            "expire_date": today + timedelta(days=28),
        },
        {
            "pk": 3,
            "title": f"Annual Leave Encashment — Submit Before {encash_deadline:%b %d}",
            "description": (
                "<p><strong>From: Human Resources</strong></p>"
                f"<p>Unused annual leave encashment requests must be submitted by "
                f"<strong>{encash_deadline:%B %d, %Y}</strong>.</p>"
                "<ul>"
                "<li>Employees with more than 1 year of service</li>"
                "<li>Maximum encashable: 5 leave days</li>"
                "</ul>"
                "<p>Apply via Leave → Leave Request.</p>"
            ),
            "expire_date": encash_deadline,
        },
        {
            "pk": 4,
            "title": (
                f"Mandatory Cybersecurity Awareness Training — "
                f"Complete by {training_deadline:%b %d}"
            ),
            "description": (
                f"<p>All employees must complete cybersecurity awareness training by "
                f"<strong>{training_deadline:%B %d, %Y}</strong>.</p>"
                "<p>Topics include phishing, password hygiene, MFA, and incident reporting. "
                "Approximate duration: 45 minutes.</p>"
            ),
            "expire_date": training_deadline,
            "disable_comments": True,
        },
        {
            "pk": 5,
            "title": f"Employee of the Month — {month_name} {year}",
            "description": (
                f"<p>We are delighted to recognize our "
                f"<strong>Employee of the Month for {month_name} {year}</strong>.</p>"
                "<p>Please join us in celebrating outstanding contributions across "
                "Engineering and other departments.</p>"
            ),
            "expire_date": today + timedelta(days=30),
        },
        {
            "pk": 6,
            "title": (
                f"Updated Work-From-Home Policy — Effective {next_month_name} 1, "
                f"{next_month_year}"
            ),
            "description": (
                f"<p>The remote work policy update is effective "
                f"<strong>{next_month_name} 1, {next_month_year}</strong>.</p>"
                "<ul>"
                "<li>Engineering &amp; Finance: up to 3 WFH days per week</li>"
                "<li>Sales, Marketing &amp; HR: up to 2 WFH days per week</li>"
                "<li>Wednesday remains the in-office anchor day</li>"
                "</ul>"
                "<p>Request WFH days through Attendance.</p>"
            ),
            "expire_date": today + timedelta(days=60),
        },
        {
            "pk": 7,
            "title": f"Compensation Review Cycle — {month_name} Payroll",
            "description": (
                f"<p>The compensation review cycle for {month_name} {year} is underway. "
                "Updated letters will appear under Profile → Documents when available.</p>"
                "<p>Compensation details are confidential.</p>"
            ),
            "expire_date": today + timedelta(days=30),
            "disable_comments": True,
        },
        {
            "pk": 8,
            "title": f"Company Family Day — {family_day:%B %d, %Y}",
            "description": (
                f"<p>Join us for <strong>Company Family Day on "
                f"{family_day:%A, %B %d, %Y}</strong>.</p>"
                "<ul>"
                "<li>Time: 10:00 AM – 6:00 PM</li>"
                "<li>Guests: up to 3 family members per employee</li>"
                "<li>Activities, meals, and awards included</li>"
                "</ul>"
                "<p>Please register with HR.</p>"
            ),
            "expire_date": family_day,
        },
        {
            "pk": 9,
            "title": "Scheduled IT Infrastructure Maintenance",
            "description": (
                "<p><strong>From: IT Department</strong></p>"
                "<p>A planned infrastructure maintenance window will run this weekend. "
                "Internal systems may be briefly unavailable overnight. "
                "Email will remain available.</p>"
                "<p>Contact IT Helpdesk if you notice issues on Monday morning.</p>"
            ),
            "expire_date": today + timedelta(days=14),
            "disable_comments": True,
        },
        {
            "pk": 10,
            "title": "Employee Referral Program — Earn Referral Bonuses",
            "description": (
                "<p>Our employee referral program is open. Refer qualified candidates "
                "for open roles and earn a referral bonus upon successful hire.</p>"
                "<p>Submit referrals through Recruitment → Referrals.</p>"
            ),
            "expire_date": today + timedelta(days=90),
        },
    ]


@transaction.atomic
def refresh_announcements(today: date | None = None) -> int:
    """Overwrite demo announcements with relative enterprise copy."""
    today = today or date.today()
    updated = 0
    for payload in _relative_announcements(today):
        ann = Announcement.objects.filter(pk=payload["pk"]).first()
        if not ann:
            continue
        ann.title = payload["title"][:100]
        ann.description = payload["description"]
        ann.expire_date = payload["expire_date"]
        if "disable_comments" in payload:
            ann.disable_comments = payload["disable_comments"]
        ann.save()
        updated += 1
    logger.info("Refreshed %s demo announcements", updated)
    return updated
