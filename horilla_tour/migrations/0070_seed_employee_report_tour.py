from django.db import migrations


SLUG = "employee-report-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Employee Report",
        "description": "The Employee Report page provides an interactive pivot table for analysing your workforce data. Slice and group employees by department, job role, job position, shift, work type and more — then switch to charts for visual insights. All data can be exported to Excel.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Pivot Table",
        "description": "The pivot table is the heart of the report. It aggregates employee data based on the rows and columns you configure. By default it groups by Department, Job Position and Job Role — but you can drag any available field into the row or column area to reshape the view instantly.",
        "element_selector": "#pivot-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Rows, Columns & Aggregation",
        "description": "Use the field buttons at the top of the pivot to drag attributes onto Rows or Columns. Choose an Aggregation (Count, Sum, Average) and a Renderer (Table, Bar Chart, Heatmap, Scatter Chart) from the dropdowns to change how the data is summarised and displayed.",
        "element_selector": "select.pvtRenderer",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Filter",
        "description": "Click Filter to narrow the employee data that feeds the pivot. Filter by name, email, company, department, job role, job position, shift, work type, employee type, reporting manager, gender, country or phone before the pivot processes it.",
        "element_selector": "#filterForm .oh-dropdown > button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Export to Excel",
        "description": "Click Export Table to download the current pivot table as an Excel file. The export includes your company details and a timestamp. The Export button is only visible when a table renderer (Table, Heatmap, etc.) is active — it hides automatically when a chart renderer is selected.",
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
            "title": "Employee Report",
            "description": "A guided tour of the Employee Report page — building pivot tables to analyse workforce data by department, role and more, and exporting results to Excel.",
            "page_match": "employee-report",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "people-outline",
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
        ("horilla_tour", "0069_seed_timesheets_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
