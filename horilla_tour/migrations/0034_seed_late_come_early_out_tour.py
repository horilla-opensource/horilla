from django.db import migrations


SLUG = "late-come-early-out-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Late Come & Early Out",
        "description": "This page tracks attendance exceptions — employees who clocked in late or left before their shift ended. Each record is automatically generated when an attendance entry doesn't meet the required check-in or check-out time for the assigned shift.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Exception Records",
        "description": "Each row shows the employee name, the attendance date, the type of exception (Late Come or Early Out), how many minutes late or early they were, and whether a penalty has been applied. Click any row to open the full detail.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Late Come",
        "description": "A Late Come record is created when an employee's check-in time is later than the start time defined in their shift. The late duration is calculated automatically and shown in the record.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Early Out",
        "description": "An Early Out record is created when an employee checks out before their shift's scheduled end time. The early departure duration is captured and can trigger a penalty if your policy requires it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Penalty Rules",
        "description": "If your organisation has penalty rules configured, they are applied automatically to late come or early out records. Click a record row to view or manage the penalty applied for that exception.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Export",
        "description": "Use Actions → Export to download the late come and early out records as a spreadsheet. Apply filters before exporting to get the specific date range or department you need.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find records by employee name. Use the Filter button to narrow results by exception type, date range, department, shift or reporting manager.",
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
            "title": "Late Come & Early Out",
            "description": "A guided tour of the Late Come & Early Out page — reviewing attendance exceptions, understanding penalties and exporting exception reports.",
            "page_match": "late-come-early-out-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "timer-outline",
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
        ("horilla_tour", "0033_seed_attendance_activity_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
