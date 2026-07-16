from django.db import migrations


SLUG = "individual-payslip-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Individual Payslip",
        "description": "This page shows the full payslip for a single employee and pay period. You can review the complete pay breakdown — basic pay, allowances, deductions and net pay — and take actions such as changing status, downloading or emailing the payslip.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Payslip Status",
        "description": "Use this dropdown to update the payslip status — Draft, Review Ongoing, Confirmed or Paid. Changing to Confirmed locks the figures; marking as Paid records that the salary has been disbursed.",
        "element_selector": ".select2-selection--single",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Download Payslip",
        "description": "Click the download icon to save this payslip as a PDF. Useful for sharing with the employee, storing records or attaching to finance reports.",
        "element_selector": "a[title='Download']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Send via Mail",
        "description": "Click the mail icon to email this payslip directly to the employee. Once sent, the icon turns green to confirm delivery. Employees can then view their payslip from their self-service portal.",
        "element_selector": "a[title='Send via mail']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Employee Details & Net Pay",
        "description": "The summary block shows the employee's name, ID, department and bank account alongside the net pay, actual basic pay, paid days and any loss-of-pay days. This gives a quick snapshot before reviewing the detailed breakdown below.",
        "element_selector": ".oh-payslip__summary",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Pay Breakdown",
        "description": "The main body lists every earning and deduction line by line — basic pay, allowances, deductions and the final net pay. Review each component here to verify the payslip is correct before confirming or sending it to the employee.",
        "element_selector": "#payslipBody",
        "side": "top",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Individual Payslip",
            "description": "A guided tour of the individual payslip view — reviewing pay breakdowns, updating status, downloading and emailing payslips.",
            "page_match": "view-created-payslip",
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
        ("horilla_tour", "0083_seed_restricted_days_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
