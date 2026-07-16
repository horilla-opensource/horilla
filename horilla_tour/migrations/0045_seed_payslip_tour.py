from django.db import migrations


SLUG = "payslip-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Payslips",
        "description": "The Payslips page is where employee payslips are created, reviewed and processed. Each payslip calculates an employee's net pay for a specific period based on their contract, allowances, deductions and attendance data.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Payslip List",
        "description": "Each row shows one payslip — the employee name, the pay period, basic wage, net pay and current status. Click any row to open the individual payslip detail where you can review the full pay breakdown.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Payslip Status",
        "description": "Each payslip has a status: Draft (created but not yet reviewed), Review Ongoing (sent for employee review), Confirmed (approved and ready to pay) and Paid (salary has been disbursed). Use the inline status dropdown on each row to update the status directly from the list.",
        "element_selector": "div[data-cell-index='3']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Create a Payslip",
        "description": "Click Create to generate a payslip for an individual employee. Select the employee, set the pay period start and end dates, and the system will auto-calculate pay based on the active contract, allowances and deductions.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Generate Bulk Payslips",
        "description": "Use Actions → Generate to create payslips for all employees at once for a selected pay period. The system processes each employee's contract and generates individual payslips in bulk — saving time at the end of each payroll cycle.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Send for Review & Confirm",
        "description": "Once payslips are generated, send them to employees for review. After the review period, confirm the payslips to lock the figures. Confirmed payslips can then be marked as Paid once the salary transfer is complete.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Send via Mail & Export",
        "description": "Use Actions → Send Via Mail to email payslips directly to employees. Use Actions → Export or Payslip Report to download payslip data as a spreadsheet for finance or audit purposes.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter & Search",
        "description": "Use the search bar to find payslips by employee name. Use the Filter button to narrow results by pay period, status, department, contract type or net pay range.",
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
            "title": "Payslips",
            "description": "A guided tour of the Payslips page — generating, reviewing, confirming and distributing employee payslips.",
            "page_match": "view-payslip",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "receipt-outline",
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
        ("horilla_tour", "0044_seed_deductions_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
