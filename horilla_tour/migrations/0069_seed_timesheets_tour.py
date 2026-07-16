from django.db import migrations


SLUG = "timesheets-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Time Sheets",
        "description": "The Time Sheets page is where employees log the time they spend on project tasks. Managers can review all time entries across the team, track hours by project or employee, and monitor workload distribution. Each entry links a date, a project, a task and the time spent to an employee.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Timesheets List",
        "description": "Each row shows one time entry — the employee, the project, the task, the date, time spent and the current status (Requested, Approved or Rejected). Click any row to open the full timesheet detail including the description of work done.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Log Time",
        "description": "Click Create to log a new time entry. Select the project and task, enter the date and the time spent, add a description of the work done and submit. The entry is created with a Requested status and can be approved by a manager.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Timesheet Detail",
        "description": "Click any timesheet row to open its detail view. Here you can review all the information for that entry, update the status (Approve or Reject), and read the description of work completed. Managers use this view to review and action individual time entries.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Delete Entries",
        "description": "Select one or more timesheet rows and use the Actions menu to delete entries in bulk. Use this to remove duplicate or incorrectly logged entries before they are reviewed.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "List, Card & Graph Views",
        "description": "Switch between views using the view toggle. The List view shows all entries in a sortable table; the Card view presents each entry as a tile; the Graph view gives a visual breakdown of time spent per employee or project — useful for workload analysis and reporting.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Use the search bar to find timesheet entries by employee name or task title. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow entries by project, task, employee, status or date range. Use the Group By option to reorganise entries by employee, project, date, department or reporting manager for structured reporting.",
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
            "title": "Time Sheets",
            "description": "A guided tour of the Time Sheets page — logging time entries, reviewing and approving timesheets, and analysing workload distribution across projects and employees.",
            "page_match": "view-time-sheet",
            "match_type": "url_name",
            "audience": "all",
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
        ("horilla_tour", "0068_seed_tasks_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
