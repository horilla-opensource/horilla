from django.db import migrations


SLUG = "asset-category-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Asset Category",
        "description": "The Asset Category page organises your company's assets into logical groups — for example Laptops, Furniture, Vehicles or IT Equipment. Each category acts as a container for individual assets, making it easy to track inventory, run reports and manage assignments by type.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Category List",
        "description": "Each row represents one asset category. The badge shows how many assets are in that category. Click any row to expand it and see the individual assets within — their tracking IDs, status, assigned employee and purchase details.",
        "element_selector": "#assetCategoryList",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Category",
        "description": "Click Create to add a new asset category. Provide a name and an optional description. Once the category exists, you can start adding individual assets to it.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Assets within a Category",
        "description": "Click any category row to expand it and view all assets in that group. Each asset entry shows the tracking ID, status (In Use, Available, Broken, etc.), the assigned employee and the purchase date. Click an asset row to open its full detail view.",
        "element_selector": "button.accordion-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Category Actions",
        "description": "Each category row has an Actions menu — use it to Add an Asset to that category, Edit the category name or description, Duplicate the category structure or Delete it. Deleting a category does not delete the assets inside — they will need to be reassigned.",
        "element_selector": "a.dropdown-toggle",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Use the search bar to quickly find a category or asset by name or tracking ID. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow the list by category name, asset name, tracking ID, purchase date, purchase cost, batch number, category or status. You can also import assets in bulk or export the full asset list from the Import and Export options next to the Create button.",
        "element_selector": "span.border-primary-500",
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
            "title": "Asset Category",
            "description": "A guided tour of the Asset Category page — organising assets into categories, adding assets within each category and managing inventory by type.",
            "page_match": "asset-category-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "folder-outline",
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
        ("horilla_tour", "0060_seed_exit_process_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
