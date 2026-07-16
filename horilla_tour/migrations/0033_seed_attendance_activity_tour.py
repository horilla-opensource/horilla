from django.db import migrations


SLUG = "attendance-activity-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Attendance Activity",
        "description": "The Attendance Activity page provides a detailed log of every clock-in and clock-out event recorded by the system. Unlike the main attendance list which shows one record per day, this view shows each individual activity entry — useful for auditing terminal-based or biometric check-in events.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Activity Log",
        "description": "Each row shows an individual attendance activity — the employee name, the date, the check-in time, the check-out time and the total duration. Click any row to open the full detail view for that activity entry.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Import Activity Data",
        "description": "Use Actions → Import to upload attendance activity records from a spreadsheet. This is useful when you receive raw clock-in data from an external time-tracking device or system.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Export Activity Data",
        "description": "Use Actions → Export to download the activity log as a spreadsheet. You can apply filters first so the export only includes the date range or employees you need.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Filter & Search",
        "description": "Use the search bar to find activity records by employee name. Use the Filter button to narrow results by date range, department, check-in time or check-out time.",
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
            "title": "Attendance Activity",
            "description": "A guided tour of the Attendance Activity page — viewing, importing and exporting individual clock-in and clock-out activity records.",
            "page_match": "attendance-activity-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "pulse-outline",
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
        ("horilla_tour", "0032_seed_hour_account_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
