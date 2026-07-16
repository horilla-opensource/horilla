from django.db import migrations


SLUG = "pms-report-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "PMS Report",
        "description": "The PMS Report page provides an interactive pivot table for analysing Performance Management System data. You can report across three datasets — Objectives, Feedback and Employee Key Results — to track goal progress, feedback trends and performance ratings across the organisation.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Select Data Model",
        "description": "Use the model selector dropdown to choose which performance dataset to analyse — Objective (company and individual goals), Feedback (360° feedback entries) or Employee Objective (key results linked to an employee). Each model exposes different fields in the pivot.",
        "element_selector": "[aria-labelledby='select2-model-select-container']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Pivot Table",
        "description": "The pivot table aggregates the selected model's data based on the rows and columns you configure. For example, group objectives by department and status to see goal completion rates per team, or group feedback by reviewer and rating to identify performance patterns.",
        "element_selector": "#pivot-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Rows, Columns & Aggregation",
        "description": "Use the field buttons at the top of the pivot to drag attributes onto Rows or Columns. Choose an Aggregation (Count, Average rating) and a Renderer (Table, Bar Chart, Heatmap) from the dropdowns to change how performance data is summarised and displayed.",
        "element_selector": "select.pvtRenderer",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Filter",
        "description": "Click Filter to narrow the PMS records feeding the pivot. Filter objectives by employee, department or manager; filter feedback by reviewer, employee or period — then re-run the pivot on the filtered subset.",
        "element_selector": "#filterForm .oh-dropdown > button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Export to Excel",
        "description": "Click Export Table to download the current pivot as an Excel file with your company details and a generation timestamp. Use this to share performance summaries with leadership or for appraisal cycle documentation.",
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
            "title": "PMS Report",
            "description": "A guided tour of the PMS Report page — analysing objectives, feedback and employee key results with an interactive pivot table and Excel export.",
            "page_match": "pms-report",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "trophy-outline",
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
        ("horilla_tour", "0075_seed_asset_report_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
