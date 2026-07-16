from django.db import migrations


SLUG = "restricted-days-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Restricted Days",
        "description": "The Restricted Days page lets you block specific date ranges during which employees cannot submit leave requests. Use this to enforce blackout periods — such as peak business seasons, audit periods or critical project deadlines — for specific departments or job positions.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Restricted Days List",
        "description": "Each row shows one restricted period — its title, start and end dates, the department and job position it applies to, and a short description. Click any row to open its full detail panel.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Restricted Day",
        "description": "Click Create to define a new restricted period. Set a title, the date range, optionally scope it to a specific department or job position, and add a description explaining why leave is restricted during that window.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Restricted Day Detail",
        "description": "Click any row to open the detail view for that restriction. The panel shows the full date range, scope and description. Use the Edit button to modify the restriction or the Delete button to remove it entirely.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Actions",
        "description": "The Actions menu provides a bulk Delete option. Select the restricted days you want to remove using the checkboxes in the list, then choose Delete from the Actions menu to remove them all at once.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to filter restricted days by title, department or job position. The list updates as you type, making it easy to check whether a particular period or team already has a restriction configured.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow the list by date range, department, job position or company. Use this to review all restrictions affecting a specific team or to identify overlapping blackout periods.",
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
            "title": "Restricted Days",
            "description": "A guided tour of the Restricted Days page — defining leave blackout periods for specific teams, reviewing existing restrictions and managing them in bulk.",
            "page_match": "restrict-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "ban-outline",
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
        ("horilla_tour", "0082_seed_company_leaves_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
