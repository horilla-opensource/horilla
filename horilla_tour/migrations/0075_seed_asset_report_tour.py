from django.db import migrations


SLUG = "asset-report-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Asset Report",
        "description": "The Asset Report page provides an interactive pivot table for analysing asset data across the organisation. Group and aggregate by asset name, category, status, assigned employee, purchase date and cost to track asset utilisation, depreciation and allocation patterns.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Pivot Table",
        "description": "The pivot table aggregates asset data based on the rows and columns you configure. Drag any available field into the row or column area to reshape the analysis — for example, group by category and status to see how many assets in each category are in use, available or under maintenance.",
        "element_selector": "#pivot-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Rows, Columns & Aggregation",
        "description": "Use the field buttons at the top of the pivot to drag attributes onto Rows or Columns. Choose an Aggregation (Count, Sum of cost) and a Renderer (Table, Bar Chart, Heatmap) from the dropdowns to change how asset data is summarised and displayed.",
        "element_selector": "select.pvtRenderer",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Filter",
        "description": "Click Filter to narrow the asset records feeding the pivot. Filter by asset name, tracking ID, purchase cost range, category, status or purchase date range — then re-run the pivot on the filtered subset.",
        "element_selector": "#filterForm .oh-dropdown > button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Export to Excel",
        "description": "Click Export Table to download the current pivot as an Excel file with your company details and a generation timestamp. Use this to share asset inventory summaries or prepare audit reports.",
        "element_selector": "#export-btn",
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
            "title": "Asset Report",
            "description": "A guided tour of the Asset Report page — building pivot tables to analyse asset inventory, allocation and cost data, and exporting results to Excel.",
            "page_match": "asset-report",
            "match_type": "url_name",
            "audience": "managers",
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
        ("horilla_tour", "0074_seed_payroll_report_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
