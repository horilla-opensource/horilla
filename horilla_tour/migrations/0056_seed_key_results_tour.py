from django.db import migrations


SLUG = "key-results-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Key Results",
        "description": "The Key Results page lists all Key Results defined in the system — the measurable outcomes that determine whether an Objective has been achieved. Each Key Result has a progress type, a target value and a duration, and tracks actual progress as employees update their current values.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Key Results List",
        "description": "Each row shows a Key Result — its title, the progress type (percentage, number or currency), the target value, the duration and a description. Click any row to open the full detail view with progress history and linked objectives.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Key Result",
        "description": "Click Create to define a new Key Result. Set the title, choose a progress type (percentage, number or currency), enter the target value, add a description and set the start and end dates. The Key Result can then be linked to one or more Objectives.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Progress Types",
        "description": "Key Results support three progress types — Percentage (0–100%), Number (any numeric target such as units sold or tickets closed) and Currency (a monetary target such as revenue or cost savings). Choose the type that best represents the outcome you are measuring.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "List & Card Views",
        "description": "Use the view toggle buttons to switch between List view and Card view. Card view gives a compact visual overview of each Key Result with its key settings and progress at a glance.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Use the search bar to quickly find Key Results by title or description. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow Key Results by progress type, target value range, duration or active status.",
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
            "title": "Key Results",
            "description": "A guided tour of the Key Results page — creating measurable outcomes, understanding progress types and linking Key Results to Objectives.",
            "page_match": "view-key-result",
            "match_type": "url_name",
            "audience": "managers",
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
        ("horilla_tour", "0055_seed_meetings_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
