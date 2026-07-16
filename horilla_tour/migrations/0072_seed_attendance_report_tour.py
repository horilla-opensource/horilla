from django.db import migrations


SLUG = "attendance-report-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Attendance Report",
        "description": "The Attendance Report page provides an interactive pivot table for analysing attendance records across the organisation. Group and aggregate by employee, department, shift, date, clock-in time and more to identify patterns, late arrivals or absenteeism trends.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Pivot Table",
        "description": "The pivot table aggregates attendance data based on the rows and columns you configure. By default it groups by employee and date — but you can drag any available field into the row or column area to reshape the analysis. Switch renderers to view Bar Charts or Heatmaps for visual patterns.",
        "element_selector": "#pivot-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Rows, Columns & Aggregation",
        "description": "Use the field buttons at the top of the pivot to drag attributes onto Rows or Columns. Choose an Aggregation (Count, Sum of hours, Average) and a Renderer (Table, Bar Chart, Heatmap) from the dropdowns to change how attendance data is summarised and displayed.",
        "element_selector": "select.pvtRenderer",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Filter",
        "description": "Click Filter to narrow the attendance records feeding the pivot. Filter by employee, department, shift, company, job position, work type, attendance date range, clock-in time, clock-out time or batch attendance status.",
        "element_selector": "#filterForm .oh-dropdown > button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Export to Excel",
        "description": "Click Export Table to download the current pivot as an Excel file with your company details and a generation timestamp. The button is visible only when a table-style renderer is active — it hides automatically when a chart renderer is selected.",
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
            "title": "Attendance Report",
            "description": "A guided tour of the Attendance Report page — building pivot tables to analyse attendance patterns by employee, department and date, and exporting results to Excel.",
            "page_match": "attendance-report",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "calendar-outline",
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
        ("horilla_tour", "0071_seed_recruitment_report_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
