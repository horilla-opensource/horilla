from django.db import migrations


SLUG = "period-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Period",
        "description": "The Period page defines the time windows used for OKR and performance review cycles — for example Q1 2024, H1 2025 or Annual 2024. Each period has a start and end date. Objectives, Key Results and feedback cycles are scoped to these periods so progress can be tracked within a defined timeframe.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Periods List",
        "description": "Each row shows a defined period — its name, start date and end date. Click any row to open the full period detail where you can view all objectives linked to it.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Period",
        "description": "Click Create to define a new performance period. Give it a descriptive name (e.g. Q2 2025), set the start and end dates, and save. Objectives and Key Results can then be scoped to this period when they are created.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Edit & Delete",
        "description": "Click any period row to view its detail. Use the Edit action to update the name or dates, or Delete to remove it. Deleting a period does not delete the objectives linked to it — they simply lose their period association.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Use the search bar to quickly find periods by name. The list updates as you type.",
        "element_selector": "input[name='search']",
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
            "title": "Period",
            "description": "A guided tour of the Period page — creating and managing time periods used to scope OKR cycles, objectives and performance reviews.",
            "page_match": "period-view",
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
        ("horilla_tour", "0057_seed_employee_bonus_point_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
