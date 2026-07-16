from django.db import migrations


SLUG = "hour-account-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Hour Account",
        "description": "The Hour Account page tracks each employee's overtime (OT) hours. Every attendance record that includes overtime contributes to this balance, which can then be carried forward, encashed or used as compensatory leave depending on your organisation's policy.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "OT Records List",
        "description": "Each row shows an employee's overtime entry — the date, the number of OT hours logged, the validation status and whether the overtime has been approved or is still pending. Click any row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Add OT Record",
        "description": "Click Create to manually add an overtime record for an employee. Enter the employee, the date and the number of overtime hours. This is useful when overtime is tracked outside the standard clock-in system.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Approval Status",
        "description": "Each OT record has a status indicator — pending, approved or validated. Approved records are confirmed by a manager; validated records have been processed for payroll or compensatory leave purposes.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Export",
        "description": "Use Actions → Export to download the hour account data as a spreadsheet. You can export filtered results to share with payroll teams or for compliance reporting.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter & Search",
        "description": "Use the search bar to find records by employee name. Use the Filter button to narrow results by date range, department, validation status or reporting manager.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Hour Account",
            "description": "A guided tour of the Hour Account page — tracking, approving and exporting employee overtime hours.",
            "page_match": "attendance-overtime-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "hourglass-outline",
            "is_published": True,
        },
    )
    if not created:
        return
    for step in STEPS:
        TourStep.objects.create(
            tour=tour,
            sequence=step["sequence"],
            title=step["title"],
            description=step["description"],
            element_selector=step["element_selector"],
            side=step["side"],
            align=step["align"],
        )


def unseed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    Tour.objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0031_seed_attendance_requests_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
