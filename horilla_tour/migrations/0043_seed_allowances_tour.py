from django.db import migrations


SLUG = "allowances-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Allowances",
        "description": "Allowances are additional pay components added on top of an employee's basic wage — such as housing allowance, transport allowance, meal allowance or performance bonuses. Each allowance defined here can be linked to employee contracts and included automatically in payroll calculations.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Allowances List",
        "description": "Each row shows a configured allowance — its name, the amount or percentage, whether it is taxable, whether it is a fixed amount or based on a condition, and whether it is currently active.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create an Allowance",
        "description": "Click Create to define a new allowance. Set the name, choose whether it is a fixed amount or a percentage of basic wage, mark it as taxable or non-taxable, and configure any conditions that determine when it applies.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "List & Card Views",
        "description": "Use the view toggle buttons to switch between List view and Card view. Card view gives a compact visual overview of each allowance with its key details at a glance.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Fixed vs Percentage",
        "description": "An allowance can be a fixed amount (e.g. £200 per month) or a percentage of the employee's basic wage (e.g. 10%). Percentage-based allowances automatically adjust when the basic wage changes.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Conditional Allowances",
        "description": "Allowances can be made conditional — for example applying only to employees in a specific department, job position or shift, or only when a certain attendance threshold is met. Conditions are configured within the allowance detail.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Edit & Delete",
        "description": "Click any allowance row to edit its configuration. You can update the amount, taxability, conditions or active status. Deleting an allowance removes it from all future payroll runs but does not affect historical payslips.",
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
            "title": "Allowances",
            "description": "A guided tour of the Allowances page — creating and managing pay allowances that are included in employee payroll calculations.",
            "page_match": "view-allowance",
            "match_type": "url_name",
            "audience": "admins",
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
        ("horilla_tour", "0042_seed_contracts_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
