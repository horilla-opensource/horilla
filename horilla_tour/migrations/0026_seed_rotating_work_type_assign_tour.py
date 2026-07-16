from django.db import migrations


SLUG = "rotating-work-type-assign-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Rotating Work Type Assign",
        "description": "This page manages rotating work type assignments for employees. A rotating work type automatically cycles an employee through a sequence of work types — for example alternating between on-site and remote — based on a schedule you define.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Assignments List",
        "description": "Each row shows an employee's active rotating work type assignment — the work type title, the rotation schedule (daily, weekly or monthly), the start date, their current work type and the date of the next automatic switch.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Assign Rotating Work Type",
        "description": "Click Assign to link a rotating work type to one or more employees. Choose the rotation pattern and set the start date — the system handles all future switches automatically.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Actions",
        "description": "Click Actions to bulk archive, un-archive or delete selected assignments. Use Import to bulk-upload assignments from a spreadsheet, or Export to download the current list.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Rotating Work Type, Based On, Start Date, Current Work Type, Next Switch and Next Work Type.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Row Actions",
        "description": "Each row has action icons to edit the assignment, duplicate it for another employee, or archive it to deactivate the rotation without losing history. Archived assignments can be restored from the Actions menu.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Type in the search box to filter assignments by employee name. The list updates as you type — useful when managing rotating work types across a large workforce.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow the list by employee, rotating work type, department, job role or reporting manager. Use Group By to reorganise the table by work type, department or any other field.",
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
            "title": "Rotating Work Type Assign",
            "description": "A guided tour of rotating work type assignments — assigning, editing, archiving and tracking automatic work type rotations for employees.",
            "page_match": "rotating-work-type-assign",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "repeat-outline",
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
        ("horilla_tour", "0025_fix_rotating_shift_assign_page_match"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
