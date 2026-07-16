from django.db import migrations


SLUG = "asset-batch-number-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Asset Batch Number",
        "description": "The Asset Batch Number page manages asset lot numbers — unique identifiers used to group assets that were purchased or received together. Tracking assets by batch makes it easy to manage warranties, returns and audits for an entire purchase group at once.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Batch List",
        "description": "Each row shows one asset batch — the lot number, the number of assets linked to that batch and an optional description. Click any row to open the batch detail view showing all assets belonging to that lot.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Batch Number",
        "description": "Click Create to define a new asset batch. Enter a unique lot number and an optional description. Once created, assets can be assigned to this batch when they are added to the system.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Batch Detail",
        "description": "Click any batch row to open its detail view. You can see all assets belonging to that lot — their names, categories, statuses and assigned employees. Use this view to manage warranties or returns for an entire purchase group.",
        "element_selector": "tr[data-toggle='oh-modal-toggle']",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Use the search bar to quickly find a batch by lot number or description. The list updates as you type.",
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
            "title": "Asset Batch Number",
            "description": "A guided tour of the Asset Batch Number page — creating lot numbers, linking assets to a batch and viewing batch details.",
            "page_match": "asset-batch-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "layers-outline",
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
        ("horilla_tour", "0061_seed_asset_category_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
