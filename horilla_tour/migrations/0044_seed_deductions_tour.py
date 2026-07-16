from django.db import migrations


SLUG = "deductions-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Deductions",
        "description": "Deductions are amounts subtracted from an employee's gross pay before the final salary is calculated — such as income tax, provident fund contributions, loan repayments or absence deductions. Each deduction defined here can be linked to contracts and applied automatically during payroll runs.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Deductions List",
        "description": "Each row shows a configured deduction — its name, the amount or percentage, whether it is a pre-tax or post-tax deduction, whether it is based on a condition, and whether it is currently active.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create a Deduction",
        "description": "Click Create to define a new deduction. Set the name, choose whether it is a fixed amount or a percentage of basic wage, configure pre-tax or post-tax treatment, and add any conditions that determine when it applies.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "List & Card Views",
        "description": "Use the view toggle buttons to switch between List view and Card view. Card view gives a compact visual overview of each deduction with its key settings at a glance.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Fixed vs Percentage",
        "description": "A deduction can be a fixed amount (e.g. £50 per month) or a percentage of the employee's basic wage (e.g. 5%). Percentage-based deductions automatically recalculate when the basic wage changes.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Conditional Deductions",
        "description": "Deductions can be made conditional — for example applying only to employees above a certain salary threshold, in a specific department, or based on attendance criteria. Conditions are configured within the deduction detail.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Edit & Delete",
        "description": "Click any deduction row to edit its configuration — update the amount, conditions or active status. Deleting a deduction removes it from future payroll runs but does not affect historical payslips.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Deductions",
            "description": "A guided tour of the Deductions page — creating and managing pay deductions that are applied during employee payroll calculations.",
            "page_match": "view-deduction",
            "match_type": "url_name",
            "audience": "admins",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "remove-circle-outline",
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
        ("horilla_tour", "0043_seed_allowances_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
