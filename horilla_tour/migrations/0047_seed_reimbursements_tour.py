from django.db import migrations


SLUG = "reimbursements-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Reimbursements",
        "description": "This page manages employee reimbursements and encashments — expenses employees have paid out of pocket that the company reimburses, as well as leave and bonus encashments. All approved amounts are included automatically in the next payslip.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Reimbursements Tab",
        "description": "The Reimbursements tab shows all expense reimbursement requests — such as travel, medical or equipment claims. Each row shows the employee, the amount claimed, the type of reimbursement and the current approval status.",
        "element_selector": "#reimbursmentContainer .oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Leave Encashments Tab",
        "description": "The Leave Encashments tab shows requests to convert unused leave days into cash. Employees can encash eligible leave balances based on your organisation's encashment policy.",
        "element_selector": "#reimbursmentContainer .oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Bonus Encashments Tab",
        "description": "The Bonus Encashments tab shows requests to encash accrued bonus points or entitlements. Once approved, the encashed amount is added to the employee's payslip.",
        "element_selector": "#reimbursmentContainer .oh-tabs__tab[data-tab-index='2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Requests List",
        "description": "Each row in the active tab shows the employee, the amount requested, the request date and the approval status. Click any row to open the full detail view including attached receipts or supporting documents.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Create a Request",
        "description": "Click Create to submit a new reimbursement request. Select the employee, choose the reimbursement type, enter the amount, attach any supporting receipts, and submit for manager approval.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Approve & Payslip Integration",
        "description": "Approved reimbursements are automatically added to the employee's next payslip as a non-taxable addition. No manual payroll entry is needed — once approved, the amount flows into the next payroll run.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter & Search",
        "description": "Use the search bar to find requests by employee name. Use the Filter button to narrow results by reimbursement type, status, date range or department.",
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
            "title": "Reimbursements",
            "description": "A guided tour of the Reimbursements page — submitting, approving and processing expense reimbursements, leave encashments and bonus encashments.",
            "page_match": "view-reimbursement",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "card-outline",
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
        ("horilla_tour", "0046_seed_loan_advance_salary_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
