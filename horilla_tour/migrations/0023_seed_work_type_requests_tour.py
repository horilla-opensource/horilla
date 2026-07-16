from django.db import migrations


SLUG = "work-type-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Work Type Requests",
        "description": "This page manages requests from employees to change their assigned work type — for example switching from on-site to remote or part-time. Managers can review and approve or reject each request.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Requests List",
        "description": "Each row shows the employee name, their current work type, the work type they have requested, the date range, and the current approval status — Requested (orange), Approved (green) or Rejected (red).",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Work Type Request",
        "description": "Click Create to raise a new work type request. Select the employee, choose the requested work type, and set the date from which the change should take effect.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Actions",
        "description": "Click Actions to bulk approve requests, bulk reject requests, export the list to a spreadsheet, or delete selected records. Select rows using their checkboxes first.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Requested Work Type, Current Work Type, Requested Date, Requested Till, Status and Description.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Approve & Reject",
        "description": "Use the approve or reject action on a request row to action it individually. Approved requests automatically update the employee's work type from the effective date.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Type in the search box to filter work type requests by employee name. The list updates as you type — useful when managing a large number of pending requests.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow the list by employee, work type, department, date range or approval status. Use Group By to organise requests by employee, work type or department.",
        "element_selector": "#filterForm .dropdown-wrapper",
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
            "title": "Work Type Requests",
            "description": "A guided tour of work type requests — creating, approving, rejecting and tracking employee work type change requests.",
            "page_match": "work-type-request-view",
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
        ("horilla_tour", "0022_seed_shift_requests_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
