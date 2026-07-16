from django.db import migrations


SLUG = "projects-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Projects",
        "description": "The Projects page is the central hub for managing work across the organisation. Project managers can create projects, assign team members, set milestones and track progress — while team members can see the projects they are part of and monitor their tasks.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Projects List",
        "description": "Each row or card represents one project — showing the project name, assigned managers, members, start and end dates, and current status. Click any project to open its detail page where you can manage tasks, milestones, members and activity.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Project",
        "description": "Click Create to start a new project. Enter the project name, description, select managers and members, set the start and end dates and choose the initial status. Once created, the project appears in the list and you can begin adding tasks and milestones.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Project Detail",
        "description": "Clicking a project opens its detail page. Here you can manage the project's tasks, set milestones, review the activity log, update members and track overall completion percentage. All project work — assignment, progress updates and comments — happens inside the detail view.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Project Actions",
        "description": "The Actions menu provides bulk and data operations — Import projects from a file, Export the list, Archive completed or inactive projects to keep the view clean, Un-archive projects that need to be reactivated, or Delete projects that are no longer needed.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "List & Card Views",
        "description": "Switch between the tabular List view and the visual Card view using the view toggle. The list view is best for scanning many projects and sorting by date or status; the card view gives a more visual overview of each project at a glance.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Use the search bar to find a project by name. The list updates as you type, making it quick to locate a specific project when you have many active ones.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow the projects list by manager, team member, status, active state or date range. Combine filters to focus on the projects most relevant to you — for example, all active projects you manage that end this quarter.",
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
            "title": "Projects",
            "description": "A guided tour of the Projects page — creating projects, managing tasks and milestones, tracking progress and using filters to stay on top of your team's work.",
            "page_match": "project-view",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "briefcase-outline",
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
        ("horilla_tour", "0066_seed_tickets_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
