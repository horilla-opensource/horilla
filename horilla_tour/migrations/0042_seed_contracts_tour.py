from django.db import migrations


SLUG = "contracts-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Contracts",
        "description": "The Contracts page stores and manages employment contracts for your employees. Each contract defines the employee's pay structure, contract type, validity period and the wage details used in payroll calculations.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Contracts List",
        "description": "Each row shows one contract — the employee name, contract type (permanent, temporary, freelance etc.), start and end dates, the wage amount and the current contract status. Click any row to open the full contract detail.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create a Contract",
        "description": "Click Create to add a new contract for an employee. Define the contract type, set the start and end dates, enter the basic wage, and configure any allowances or deductions that apply to this contract.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Contract Status",
        "description": "Each row has an inline status dropdown — Active (currently in force), Draft, Expired or Terminated. Change the status directly from the list without opening the full contract detail.",
        "element_selector": "select.oh-table__editable-input",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Wage & Pay Structure",
        "description": "The wage details on each contract feed directly into payroll. The basic wage, along with any linked allowances and deductions, determines the employee's net pay for each payroll period.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Export",
        "description": "Use Actions → Export to download the contracts list as a spreadsheet. Useful for reporting, auditing employment terms or sharing data with legal or finance teams.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find a contract by employee name. Use the Filter button to narrow results by contract type, status, wage range, department or expiry date.",
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
            "title": "Contracts",
            "description": "A guided tour of the Contracts page — creating, managing and reviewing employee employment contracts and their pay structures.",
            "page_match": "view-contract",
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
        ("horilla_tour", "0041_seed_compensatory_leave_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
