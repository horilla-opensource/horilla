from django.db import migrations


SLUG = "leave-type-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Leave Types",
        "description": "Leave Types define the categories of leave available in your organisation — such as Annual Leave, Sick Leave, Maternity Leave and Compensatory Leave. Each leave type has its own rules for accrual, carry-forward limits, approval flow and eligibility.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Leave Type List",
        "description": "Each row shows a configured leave type — its name, the number of days allowed per year, whether it requires approval, whether unused days can be carried forward, and whether it accrues over time.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create a Leave Type",
        "description": "Click Create to define a new leave type. Set the name, total days allowed, approval requirement, carry-forward limit, accrual settings, and any eligibility restrictions such as gender or probation period.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "List & Card Views",
        "description": "Use the view toggle buttons in the top-right to switch between List view (tabular) and Card view (visual tiles). Card view gives a quick overview of each leave type with its key settings at a glance.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Carry Forward & Accrual",
        "description": "Each leave type can be configured to carry forward unused days to the next leave period and to accrue days over time based on the employee's tenure or work days. These settings control how balances grow and roll over.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Edit & Delete",
        "description": "Click the edit icon on any leave type to update its configuration. Use the delete icon to remove a leave type that is no longer in use — note that deleting a leave type also removes any assigned leave balances linked to it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find a leave type by name. Use the Filter button to narrow the list by approval requirement, carry-forward setting or accrual type.",
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
            "title": "Leave Types",
            "description": "A guided tour of the Leave Types page — creating, configuring and managing leave categories for your organisation.",
            "page_match": "type-view",
            "match_type": "url_name",
            "audience": "admins",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "layers-outline",
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
        ("horilla_tour", "0037_seed_leave_requests_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
