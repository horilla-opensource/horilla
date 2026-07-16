from django.db import migrations


SLUG = "employee-bonus-point-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Employee Bonus Points",
        "description": "The Employee Bonus Points page tracks bonus points awarded to employees — a recognition and performance incentive system. Points can be awarded based on objectives achieved, feedback received or any custom criteria, and can later be encashed through the Reimbursements module.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Bonus Points List",
        "description": "Each row shows an employee's bonus point entry — the employee name, the number of bonus points awarded and what the points are based on (the reason or criteria). Click any row to edit or delete the entry.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Award Bonus Points",
        "description": "Click Create to award bonus points to an employee. Select the employee, enter the number of points and specify what the points are based on — for example an achieved objective, a completed feedback cycle or a custom award.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Points Encashment",
        "description": "Accumulated bonus points can be encashed into a monetary payment via the Reimbursements module. Once an employee requests encashment, the equivalent amount is added to their next payslip automatically.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Use the search bar to quickly find bonus point records by employee name. The list updates as you type.",
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
            "title": "Employee Bonus Points",
            "description": "A guided tour of the Employee Bonus Points page — awarding points to employees, understanding how points are tracked and how they can be encashed through payroll.",
            "page_match": "employee-bonus-point",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "star-outline",
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
        ("horilla_tour", "0056_seed_key_results_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
