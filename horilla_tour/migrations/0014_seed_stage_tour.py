from django.db import migrations


SLUG = "recruitment-stage-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Stages",
        "description": "Stages define the steps candidates move through in a recruitment pipeline — Initial, Test, Interview, Hired and Cancelled. This page lists all active stages with their recruitment, assigned managers and type. The order here determines the column sequence in the pipeline kanban board.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Stages List",
        "description": "Each row shows a stage with its title, assigned stage managers and type. Click any row to open the detail panel where you can edit the stage name, reassign managers, change its type or delete it.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Stage",
        "description": "Click Create to add a new stage. Give it a title, select the stage type — Initial, Test, Interview, Hired or Cancelled — assign stage managers and link it to a recruitment. The stage appears immediately in that recruitment's pipeline.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Title, Managers or Type — to focus on the information you need.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Type in the search box to filter stages by name. The list updates as you type — useful when you have many stages across several recruitments and need to find one quickly.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter",
        "description": "Click Filter to narrow the list by recruitment, stage type (Initial, Test, Interview, Hired, Cancelled) or stage manager. Use the Group By option inside the filter to organise stages under their recruitment.",
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
            "title": "Stages",
            "description": "A guided tour of recruitment stages — types, grouping by recruitment, creating and managing pipeline steps.",
            "page_match": "rec-stage-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "git-network-outline",
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
        ("horilla_tour", "0013_seed_recruitment_view_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
