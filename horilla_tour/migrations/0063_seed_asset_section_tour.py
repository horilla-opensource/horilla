from django.db import migrations


SLUG = "asset-section-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Asset",
        "description": "The Asset page is the central hub for tracking asset assignments, requests and allocations across the organisation. Employees can view assets assigned to them and raise requests here, while managers can manage all allocations and approvals.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Asset Tab",
        "description": "The Asset tab shows all assets currently assigned to you. Each row displays the asset name, category, tracking ID, batch number, assigned date and current status. Click any row to view the full asset detail including description and assigned-by information.",
        "element_selector": ".oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Asset Request Tab",
        "description": "The Asset Request tab lists all asset requests — yours as an employee, and requests from your subordinates as a manager. Managers can approve or reject requests directly from this tab. Use the Create Request action in the tab menu to raise a new asset request.",
        "element_selector": ".oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Asset Allocation Tab",
        "description": "The Asset Allocation tab shows all allocation records — which assets have been assigned to which employees, on what date and with what expected return date. Managers can create new allocations, renew existing ones or process returns from the tab actions menu.",
        "element_selector": ".oh-tabs__tab[data-tab-index='2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Records List",
        "description": "The records list updates when you switch tabs — showing your assets, requests or allocations depending on the active tab. Click any row to open a detailed view of that asset, request or allocation record.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Tab Actions",
        "description": "Each tab has an Actions menu for operations relevant to that tab — Create Request on the Asset Request tab, and Create Allocation or Asset Renewal on the Asset Allocation tab. Click the Actions button next to the active tab to see the available options.",
        "element_selector": "span[title='Actions']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Use the search bar to quickly find an asset, request or allocation by employee name, asset name or tracking ID. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow the list by asset category, employee, department, assigned date, return date or request status. Filters apply to the currently active tab.",
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
            "title": "Asset",
            "description": "A guided tour of the Asset page — viewing assigned assets, raising requests, managing allocations and processing returns.",
            "page_match": "asset-request-allocation-view",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "cube-outline",
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
        ("horilla_tour", "0062_seed_asset_batch_number_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
