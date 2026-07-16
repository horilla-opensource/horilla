from django.db import migrations


SLUG = "tasks-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Tasks",
        "description": "The Tasks page gives you a consolidated view of all tasks across every project you are part of. You can create standalone tasks, track progress by status, and filter across projects, stages and team members — all without having to open individual project pages.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Tasks List",
        "description": "Each row shows one task — the task title, the project it belongs to, its current stage, assigned members, priority, due date and completion status. A colour indicator shows whether the task is To Do, In Progress, Completed or Expired at a glance.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Task",
        "description": "Click Create to add a new task. Fill in the title, select the project and stage, assign team members, set the priority and due date, and add a description. Once saved, the task appears in the list and is visible to all assigned members.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Task Detail",
        "description": "Click any task row to open its detail view. Here you can update the status, reassign members, add subtasks, log comments and track the activity history for that task. The detail view is where the day-to-day work on a task is recorded.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Task Actions",
        "description": "The Actions menu provides bulk operations on selected tasks — Archive tasks that are complete but need to be retained for reference, Un-archive tasks that need to be brought back into active view, or Delete tasks that are no longer relevant.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "List & Card Views",
        "description": "Toggle between the tabular List view and the visual Card view. The list view is better for sorting and scanning many tasks; the card view presents each task as a visual tile, making it easier to get a quick overview of workload across the team.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Use the search bar to find tasks by title. The list updates as you type, making it easy to locate a specific task across all your projects without scrolling.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow tasks by project, stage, status, priority, assigned member or due date range. Use the Group By option to reorganise the list by project, stage or status for a structured view of workload distribution.",
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
            "title": "Tasks",
            "description": "A guided tour of the Tasks page — creating and tracking tasks across all projects, managing status and assignments, and using filters to focus on the work that matters most.",
            "page_match": "task-all",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "checkmark-circle-outline",
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
        ("horilla_tour", "0067_seed_projects_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
