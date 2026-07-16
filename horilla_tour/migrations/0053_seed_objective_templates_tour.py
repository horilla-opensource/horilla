from django.db import migrations


SLUG = "objective-templates-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Objective Templates",
        "description": "Objective Templates are reusable objective blueprints. Instead of creating the same objective structure from scratch each quarter, you define it once as a template — with predefined Key Results, durations and descriptions — and then apply it to create live objectives for any employee.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Templates List",
        "description": "Each row shows one template — its title, the managers assigned to it, the Key Results it contains, the assignees and the duration. Click any row to open the full template detail.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Template",
        "description": "Click Create to define a new objective template. Set the title, add a description, attach default Key Results with target values and units, and save. The template can then be reused to quickly spin up objectives for any team member.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Applying a Template",
        "description": "To use a template, open it and assign it to an employee. The system creates a live objective with all the predefined Key Results already linked — saving time when onboarding new team members or running recurring goal cycles.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Edit & Delete",
        "description": "Click the three-dot menu on any template row to Edit or Delete it. Editing a template does not affect objectives that were already created from it — changes apply only to future use of the template.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Use the search bar to quickly find templates by title. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow templates by assignee, key result, date range, status or progress percentage.",
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
            "title": "Objective Templates",
            "description": "A guided tour of the Objective Templates page — creating reusable objective blueprints with predefined Key Results that can be applied to any employee.",
            "page_match": "objective-template-list-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "copy-outline",
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
        ("horilla_tour", "0052_seed_objectives_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
