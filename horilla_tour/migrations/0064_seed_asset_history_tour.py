from django.db import migrations


SLUG = "asset-history-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Asset History",
        "description": "The Asset History page provides a complete audit trail of all asset assignments across the organisation — showing which assets were assigned to which employees, when they were assigned, when they were returned and the return status. It is the go-to view for tracking an asset's lifecycle.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "History List",
        "description": "Each row shows one assignment record — the asset name, the employee it was assigned to, the assigned date, the returned date and the return status (returned, damaged or still active). Click any row to open the full assignment detail.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Assignment Detail",
        "description": "Clicking a row opens the asset assignment detail — showing the tracking ID, batch number, assigned date, return status, assigned-by employee and asset description. Use this to investigate the complete history of a specific asset or assignment.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Search",
        "description": "Use the search bar to quickly find history records by asset name or employee name. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Filter",
        "description": "Click Filter to narrow history records by asset, employee, department, assigned date range, returned date range or return status. Combine filters to pinpoint specific assignment events.",
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
            "title": "Asset History",
            "description": "A guided tour of the Asset History page — reviewing the full audit trail of asset assignments, returns and statuses across the organisation.",
            "page_match": "asset-history",
            "match_type": "url_name",
            "audience": "managers",
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
        ("horilla_tour", "0063_seed_asset_section_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
