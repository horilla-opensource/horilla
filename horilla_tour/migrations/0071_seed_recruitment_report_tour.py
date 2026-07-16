from django.db import migrations


SLUG = "recruitment-report-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Recruitment Report",
        "description": "The Recruitment Report page provides an interactive pivot table for analysing your hiring pipeline. You can report across three datasets — Candidates, Recruitment drives and Onboarding stages — making it easy to track conversion rates, stage durations and hiring trends.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Select Data Model",
        "description": "Use the model selector dropdown to choose which dataset to analyse — Candidate, Recruitment or Onboarding Stage. Each model exposes different fields in the pivot, so switch between them to answer different questions about your recruitment process.",
        "element_selector": "[aria-labelledby='select2-model-select-container']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Pivot Table",
        "description": "The pivot table aggregates the selected model's data based on the rows and columns you configure. Drag fields into the row or column areas and choose an aggregation and renderer to reshape the view. Switch to a Bar Chart or Scatter Chart for visual trend analysis.",
        "element_selector": "#pivot-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Rows, Columns & Aggregation",
        "description": "Use the field buttons at the top of the pivot to drag attributes onto Rows or Columns. Choose an Aggregation (Count, Sum, Average) and a Renderer (Table, Bar Chart, Heatmap) from the dropdowns to change how the hiring data is summarised and displayed.",
        "element_selector": "select.pvtRenderer",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Filter",
        "description": "Click Filter to narrow the dataset feeding the pivot. Filter candidates by stage, skill, source or joining date; filter recruitment drives by position and date; filter onboarding stages by pipeline and status — then re-run the pivot on the filtered subset.",
        "element_selector": "#filterForm .oh-dropdown > button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Export to Excel",
        "description": "Click Export Table to download the current pivot as an Excel file with your company details and a generation timestamp. The button is visible only when a table-style renderer is active.",
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
            "title": "Recruitment Report",
            "description": "A guided tour of the Recruitment Report page — analysing candidates, recruitment drives and onboarding stages with an interactive pivot table and Excel export.",
            "page_match": "recruitment-report",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "person-add-outline",
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
        ("horilla_tour", "0070_seed_employee_report_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
