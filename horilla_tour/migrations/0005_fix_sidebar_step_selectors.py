"""
Migration 0005 — fix #sidebar element selectors in seeded tour steps.

Steps that used element_selector="#sidebar" anchored to the full sidebar
<div>, which positioned the driver.js popover in the top-left corner pointing
at empty space. Change them to floating (element_selector="", side="over").
"""

from django.db import migrations


def fix_sidebar_steps(apps, schema_editor):
    TourStep = apps.get_model("horilla_tour", "TourStep")
    TourStep.objects.filter(element_selector="#sidebar").update(
        element_selector="", side="over"
    )


def restore_sidebar_steps(apps, schema_editor):
    """Restore original values by slug+sequence for a clean reverse."""
    TourStep = apps.get_model("horilla_tour", "TourStep")
    Tour = apps.get_model("horilla_tour", "Tour")

    SIDEBAR_STEPS = {
        "employee-directory": [2],
        "ess-dashboard-tour": [5],
        "leave-management": [4],
        "attendance-tracking": [3],
        "payroll-overview": [2],
        "asset-management": [2],
        "performance-management": [2],
        "onboarding-pipeline": [2],
        "offboarding-process": [2],
        "project-management": [2],
        "helpdesk-overview": [2],
    }

    for slug, sequences in SIDEBAR_STEPS.items():
        try:
            tour = Tour.objects.get(slug=slug)
        except Tour.DoesNotExist:
            continue
        TourStep.objects.filter(tour=tour, sequence__in=sequences).update(
            element_selector="#sidebar", side="right"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0004_seed_module_tours"),
    ]

    operations = [
        migrations.RunPython(fix_sidebar_steps, restore_sidebar_steps),
    ]
