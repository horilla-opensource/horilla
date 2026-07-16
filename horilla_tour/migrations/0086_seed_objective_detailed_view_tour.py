from django.db import migrations


SLUG = "objective-detailed-view-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Objective Detailed View",
        "description": "This page shows everything about a single OKR objective — its details, the employees assigned to it, their key results, progress and status. Managers can edit the objective, add assignees, track progress and log activities all from here.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Objective Details",
        "description": "The header card shows the objective title along with its managers, duration and description. This gives a quick overview of what the objective aims to achieve and who is responsible for it.",
        "element_selector": ".oh-helpdesk__header",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Edit Objective",
        "description": "Click the Edit button to update the objective title, description, duration or managers. Changes here apply to all employees assigned to this objective.",
        "element_selector": "button[data-target='#objectCreateModal']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Add Assignees",
        "description": "Click the Add Assignees button to assign additional employees to this objective. Each assigned employee will have their own set of key results and progress tracked independently under this objective.",
        "element_selector": "button[hx-get*='add-assignees']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Employee Objectives",
        "description": "Each row below represents an employee assigned to this objective. You can see their name, progress bar, current status and action buttons. Click a row to expand it and view or manage the employee's key results.",
        "element_selector": "#emp_objective_card",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Employee Row",
        "description": "Click on any employee row to expand it and see all key results assigned to that employee for this objective. The progress bar shows how far along they are towards completing the objective.",
        "element_selector": "button.accordion-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Objective Status",
        "description": "Each employee row has a status dropdown — Not Started, In Progress, Completed or Cancelled. Update it to reflect the current state of the employee's progress on this objective.",
        "element_selector": "a.dropdown-toggle",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Activity Log",
        "description": "Click the activity icon on an employee row to open the activity sidebar. It shows a timeline of all updates — status changes, key result edits, comments and progress updates — for that employee's objective.",
        "element_selector": ".oh-activity-sidebar__open",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Add Key Result",
        "description": "Click the Add Key Result button on an employee row to define a measurable outcome for that employee under this objective. Set the key result title, target value, unit and end date to track their progress towards the goal.",
        "element_selector": "a[title='Add Key Result']",
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
            "title": "Objective Detailed View",
            "description": "A guided tour of the Objective Detailed View — reviewing objective details, managing assignees, tracking key results and monitoring progress.",
            "page_match": "objective-detailed-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "trophy-outline",
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
        ("horilla_tour", "0085_seed_filing_status_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
