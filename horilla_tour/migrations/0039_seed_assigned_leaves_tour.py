from django.db import migrations


SLUG = "assigned-leaves-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "All Assigned Leaves",
        "description": "This page shows the leave balances assigned to every employee across all leave types. Each record represents one employee's allocation for a specific leave type — including the total days granted, days used, days remaining and any carry-forward balance.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Assigned Leave Balances",
        "description": "Each row shows one assignment — the employee name, leave type, total days allocated, days already used, remaining balance and carry-forward days from the previous period. Click any row to open the full detail and make adjustments.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Assign Leave",
        "description": "Click Assign to allocate a leave type to one or more employees. Choose the leave type, set the number of days and the validity period. You can assign to individual employees or to an entire department at once.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Adjust Balances",
        "description": "Open any record to manually adjust an employee's leave balance — for example to add extra days, correct an error or account for a policy exception. All adjustments are logged for audit purposes.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Carry Forward",
        "description": "The Carryforward Days column shows how many unused days were rolled over from the previous leave period. This is controlled by the carry-forward settings on each leave type.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Import & Export",
        "description": "Use Actions → Import to bulk-assign leave balances from a spreadsheet. Use Actions → Export to download the current balances for reporting or payroll reconciliation.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find records by employee name. Use the Filter button to narrow by leave type, department, remaining days or carry-forward status. Use Group By to organise the view by employee, leave type or assigned date.",
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
            "title": "All Assigned Leaves",
            "description": "A guided tour of the All Assigned Leaves page — viewing, assigning and managing employee leave balances across all leave types.",
            "page_match": "assign-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "briefcase-outline",
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
        ("horilla_tour", "0038_seed_leave_type_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
