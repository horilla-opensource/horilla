from django.db import migrations


SLUG = "my-attendances-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "My Attendances",
        "description": "This page shows your own attendance records — every day you have clocked in and out. You can review your attendance history, check validation status, raise correction requests and track your overtime hours, all from one place.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Your Attendance Records",
        "description": "Each row shows one day's attendance — your check-in time, check-out time, shift, work type, minimum required hours, hours worked and any overtime earned. Click a row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Date, Check-In, Check-Out, Shift, Work Type, Min Hour, At Work, Pending Hour and Overtime.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Validation Status",
        "description": "Each row has a coloured left border showing its status — validated (confirmed by manager), not validated (pending review), correction requested (awaiting manager action) or correction approved.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Request a Correction",
        "description": "If you spot an error — such as a missing clock-out or wrong check-in time — click the row to open the record and submit a correction request. Your manager will review and approve or reject it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter",
        "description": "Click Filter to narrow your records by date range, shift, work type or validation status — useful when reviewing a specific pay period or tracking down a missing entry.",
        "element_selector": "#filterForm .dropdown-wrapper",
        "side": "bottom",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "My Attendances",
            "description": "A guided tour of the My Attendances page — reviewing your own attendance records, understanding validation status and raising correction requests.",
            "page_match": "view-my-attendance",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "person-circle-outline",
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
        ("horilla_tour", "0034_seed_late_come_early_out_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
