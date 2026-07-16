"""
Seed the "Dashboard Highlights" tour — a guided walkthrough anchored to real
dashboard elements (sidebar, KPI cards, charts, approvals, header, help button).

This is the richer replacement for the placeholder "Dashboard Overview" tour
from 0002, so we also unpublish that one to keep a single clean dashboard
walkthrough. Selectors target container IDs present in the initial dashboard
HTML, so highlighting works even before async chart data loads; if markup ever
changes, an unresolved selector simply degrades to a centered step and admins
can adjust it from Settings → Product Tours.
"""

from django.db import migrations

SLUG = "dashboard-highlights"

# (element_selector, side, title, description)
STEPS = [
    ("#sidebar", "right", "Navigation",
     "Every HR module lives in this sidebar — Employees, Attendance, Leave, "
     "Payroll, Recruitment and more."),
    ("#md-kpi-grid", "bottom", "Key metrics at a glance",
     "Headcount, attendance rate, people on leave and pending approvals update "
     "live here."),
    ("#md-open-customize", "left", "Make it yours",
     "Personalise the dashboard — add, hide or rearrange cards to match how "
     "your team works."),
    ("#department_headcount", "top", "Live charts",
     "Visual breakdowns (by department, gender, hiring, payroll…) refresh "
     "automatically as your data grows."),
    ("#md-pending-approvals", "top", "Act without leaving",
     "Approve or reject leave, attendance and other requests right from the "
     "dashboard."),
    ("#header", "bottom", "Top bar",
     "Global search, notifications, company switcher and your profile all live "
     "up here."),
    ("#tourLauncherBtn", "bottom", "Replay anytime",
     "Open this Help button to restart this tour or launch any other guided "
     "tour."),
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    # Retire the thin placeholder overview in favour of this richer tour.
    Tour.objects.filter(slug="dashboard-overview", company_id=None).update(
        is_published=False
    )

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        company_id=None,
        defaults={
            "title": "Dashboard Highlights",
            "description": "A guided look at your dashboard, anchored to real elements.",
            "page_match": "dashboard",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 20,
            "icon": "sparkles-outline",
            "is_published": True,
        },
    )
    if not created:
        return
    for i, (selector, side, title, desc) in enumerate(STEPS, start=1):
        TourStep.objects.create(
            tour=tour,
            sequence=i,
            title=title,
            description=desc,
            element_selector=selector,
            side=side,
            align="start",
        )


def unseed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    Tour.objects.filter(slug=SLUG, company_id=None).delete()
    Tour.objects.filter(slug="dashboard-overview", company_id=None).update(
        is_published=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0002_seed_default_tours"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
