from django.db import migrations


SLUG = "roster-planner-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Roster Planner",
        "description": "The Roster Planner lets you schedule employee shifts across a date range in a visual grid. You can assign shifts to individual employees for each day, then publish the schedule so employees can see it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Filter by Department & Date Range",
        "description": "Use the department dropdown and date pickers to control which employees and which period are shown in the grid. Click the search button to reload the roster for the selected filters.",
        "element_selector": "#rosterFilterForm",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Roster Grid",
        "description": "The grid shows one row per employee and one column per day in the selected date range. Each cell can hold a shift assignment. Today's column is highlighted for quick reference.",
        "element_selector": "#rosterGridContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Assigning Shifts",
        "description": "Click any empty cell in the grid to assign a shift to that employee for that day. Click an existing assignment to edit or remove it. Cells can hold multiple shifts if needed.",
        "element_selector": "#rosterGridContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Publish the Roster",
        "description": "Click Publish to make the scheduled shifts visible to employees. You can publish for all employees or select specific ones. Employees can view their published roster from their own dashboard.",
        "element_selector": "button.oh-btn--secondary.oh-btn--shadow[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Import Roster",
        "description": "Click Import to upload a pre-filled roster spreadsheet — useful for bulk-scheduling large teams. Download the template first from the import dialog to ensure the correct format.",
        "element_selector": "button.oh-btn--light.oh-btn--shadow[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Select & Bulk Publish",
        "description": "Use the Select button in the grid to select multiple employees at once, then use Publish to push the roster for just those employees — handy when you only need to notify a subset of your team.",
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
            "title": "Roster Planner",
            "description": "A guided tour of the Roster Planner — scheduling shifts in the grid, publishing the roster and importing bulk schedules.",
            "page_match": "roster-home",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "calendar-outline",
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
        ("horilla_tour", "0026_seed_rotating_work_type_assign_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
