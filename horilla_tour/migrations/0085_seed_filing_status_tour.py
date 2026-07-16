from django.db import migrations


SLUG = "filing-status-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Filing Status",
        "description": "The Filing Status page lets you define the tax filing categories used in payroll — such as Single, Married Filing Jointly or Head of Household. Each filing status groups a set of tax brackets that determine how employee income is taxed.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Filing Status List",
        "description": "Each row represents one filing status. Click a row to expand it and view the tax brackets associated with that filing status — the income ranges and corresponding tax rates applied during payroll calculation.",
        "element_selector": "#FilingStatusList",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Filing Status Row",
        "description": "Click on any filing status row to expand it and see its tax brackets. The brackets define the income bands and the percentage of tax applied at each band for employees assigned to that filing status.",
        "element_selector": ".oh-accordion-meta__header",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Actions",
        "description": "Each filing status row has an Actions button. Use it to create a new tax bracket under that status, update the filing status name, or delete it. Changes here directly affect payroll tax calculations.",
        "element_selector": ".oh-accordion-meta__btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Create a Filing Status",
        "description": "Click Create to add a new filing status. Give it a name and then use its Actions menu to add the tax brackets that apply. Filing statuses are linked to employee contracts to determine the correct tax treatment during payroll.",
        "element_selector": "a[data-target='#objectCreateModal']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to filter filing statuses by name. Useful when you have multiple statuses configured and need to locate a specific one quickly.",
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
            "title": "Filing Status",
            "description": "A guided tour of the Filing Status page — creating and managing tax filing categories and their associated tax brackets for payroll.",
            "page_match": "filing-status-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "document-text-outline",
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
        ("horilla_tour", "0084_seed_individual_payslip_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
