from django.db import migrations


SLUG = "attendances-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Attendances",
        "description": "This page records every clock-in and clock-out event for your employees. You can review attendance entries, validate them, track overtime hours, and see which records have already been approved — all from one place.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Attendance Records",
        "description": "The list shows each attendance entry with the employee name, check-in time, check-out time, worked hours and current validation status. Click any row to open the full detail view for that entry.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Tabs — Validate, OT & Validated",
        "description": "Use the tabs to switch between views: Attendance To Validate shows entries pending approval, OT Attendances shows overtime records awaiting approval, and Validated Attendances shows all approved records.",
        "element_selector": "#attendances-tab .oh-tabs__tab",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Create Attendance",
        "description": "Click Create to manually add an attendance record — useful for correcting missed clock-ins or adding records for employees who work off-system. Fill in the employee, date, check-in and check-out times.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Import Attendance",
        "description": "Use Actions → Import to upload a spreadsheet of attendance records in bulk. Download the template from the import dialog to ensure your file uses the correct column format.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Attendance To Validate",
        "description": "Click the Attendance To Validate tab to review pending records. You can approve individual entries or select multiple rows and use the Validate button to bulk-approve them in one action.",
        "element_selector": "#attendances-tab .oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Overtime (OT) Attendances",
        "description": "Switch to the OT Attendances tab to see overtime entries. Review each record and use Approve OT to confirm the overtime hours, which will then flow into payroll calculations.",
        "element_selector": "#attendances-tab .oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Validated Attendances",
        "description": "The Validated Attendances tab shows all records that have already been approved. Use this view to audit approved entries or export a validated attendance report.",
        "element_selector": "#attendances-tab .oh-tabs__tab[data-tab-index='2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Filter & Search",
        "description": "Use the search bar to find records by employee name. Use the Filter button to narrow results by date range, department, shift, work type, validation status or late-arrival flag.",
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
            "title": "Attendances",
            "description": "A guided tour of the Attendances page — reviewing records, validating entries, approving overtime and importing bulk attendance data.",
            "page_match": "attendance-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "time-outline",
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
        ("horilla_tour", "0029_seed_policies_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
