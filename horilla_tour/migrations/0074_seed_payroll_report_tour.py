from django.db import migrations


SLUG = "payroll-report-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Payroll Report",
        "description": "The Payroll Report page provides an interactive pivot table for analysing payroll data. You can report across two datasets — Payslips and Allowance or Deduction breakdowns — to track salary distribution, pay head totals and payroll trends across departments and periods.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Select Data Model",
        "description": "Use the model selector dropdown to choose which dataset to analyse — Payslip (overall net pay, basic salary, deductions per employee) or Allowance/Deduction (individual pay head line items). Switching models refreshes the pivot with the relevant fields.",
        "element_selector": "[aria-labelledby='select2-model-select-container']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Pivot Table",
        "description": "The pivot table aggregates payroll data based on the rows and columns you configure. For example, group payslips by department and month to see total payroll spend per team over time, or break down by pay head to identify the largest cost components.",
        "element_selector": "#pivot-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Rows, Columns & Aggregation",
        "description": "Use the field buttons at the top of the pivot to drag attributes onto Rows or Columns. Choose an Aggregation (Sum, Average, Count) and a Renderer (Table, Bar Chart, Heatmap) from the dropdowns to change how payroll data is summarised and displayed.",
        "element_selector": "select.pvtRenderer",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Filter",
        "description": "Click Filter to narrow the payroll records feeding the pivot. Filter by employee, department, pay period start and end dates, payslip status or pay grade — then re-run the pivot on the filtered subset.",
        "element_selector": "#filterForm .oh-dropdown > button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Export to Excel",
        "description": "Click Export Table to download the current pivot as an Excel file with your company details and a generation timestamp. Use this to share payroll summaries with finance teams or for compliance reporting.",
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
            "title": "Payroll Report",
            "description": "A guided tour of the Payroll Report page — analysing payslips and pay head breakdowns with an interactive pivot table and Excel export.",
            "page_match": "payroll-report",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "cash-outline",
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
        ("horilla_tour", "0073_seed_leave_report_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
