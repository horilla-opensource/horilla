from django.db import migrations


SLUG = "loan-advance-salary-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Loan / Advanced Salary",
        "description": "This page manages employee financial assistance — loans repaid in instalments, advance salary payments drawn against future earnings, and fines applied for policy violations. All three are tracked here and automatically factored into payroll deductions.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Loan Tab",
        "description": "The Loan tab shows all active and completed employee loans. Each record shows the employee name, the loan amount, the number of instalments, the amount repaid so far and the outstanding balance.",
        "element_selector": ".oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Advanced Salary Tab",
        "description": "The Advanced Salary tab shows salary advance requests — where an employee has drawn part of their future salary early. The advance is automatically deducted from the next payslip or spread across multiple pay periods.",
        "element_selector": ".oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Fine Tab",
        "description": "The Fine tab records penalty deductions applied to employees — for example for attendance violations, policy breaches or disciplinary actions. Fines are deducted from the employee's payslip in the configured period.",
        "element_selector": ".oh-tabs__tab[data-tab-index='2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Records List",
        "description": "Each row in the active tab shows the employee, the amount, the instalment schedule and the current repayment status. Click any row to open the full detail view including the complete repayment history.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Create a Loan or Advance",
        "description": "Click Create to issue a new loan or advance salary. Select the employee, set the total amount, configure the number of instalments and the start date. The system will automatically schedule deductions across the specified payroll periods.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Automatic Payroll Deduction",
        "description": "Once a loan or advance is created, the instalment amounts are automatically deducted from the employee's payslip each period until the balance is cleared. No manual adjustments are needed — payroll handles it automatically.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter & Search",
        "description": "Use the search bar to find records by employee name. Use the Filter button to narrow results by status, amount range, department or instalment dates.",
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
            "title": "Loan / Advanced Salary",
            "description": "A guided tour of the Loan / Advanced Salary page — issuing loans, salary advances and fines, and tracking automatic payroll deductions.",
            "page_match": "view-loan",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "wallet-outline",
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
        ("horilla_tour", "0045_seed_payslip_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
