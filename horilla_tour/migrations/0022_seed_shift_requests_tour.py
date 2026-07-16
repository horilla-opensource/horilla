from django.db import migrations


SLUG = "shift-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Shift Requests",
        "description": "This page manages employee requests to change their assigned work shift. Managers can review, approve or reject requests, and employees can track the status of their own submissions.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Shift Requests Tab",
        "description": "The Shift Requests tab lists all employee-raised requests to change their assigned shift. Each row shows the employee, their current shift, the requested shift, the date range and the current approval status.",
        "element_selector": "button.oh-tabs__tab[data-target='#shift-tab1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Allocated Shifts Tab",
        "description": "The Allocated Shift Requests tab shows shift allocations that a manager has directly assigned to employees — without requiring a request to be raised by the employee.",
        "element_selector": "button.oh-tabs__tab[data-target='#shift-tab2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Requests List",
        "description": "Each row shows the employee name, their current shift, the shift they have requested, the requested date range, and the current approval status — Requested (orange), Approved (green) or Canceled (red).",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Create Shift Request",
        "description": "Click Create to raise a new shift request. Select the employee, the shift they are requesting, and the date from which the change should apply.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Actions",
        "description": "Click Actions to bulk approve requests, bulk reject requests, export the list to a spreadsheet, or delete selected records. Select rows using their checkboxes first.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Requested Shift, Current Shift, Requested Date, Requested Till, Status, Description and more.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Approve & Reject",
        "description": "Click the approve or reject icon on any request row to action it individually. Approved requests update the employee's shift automatically. Rejected requests notify the employee with a reason if one is provided.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Search",
        "description": "Type in the search box to filter shift requests by employee name. The list updates as you type — useful when managing a large number of pending requests.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 10,
        "title": "Filter",
        "description": "Click Filter to narrow the list by employee, shift, department, date range or approval status. Use Group By to organise requests by employee, requested shift or current shift.",
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
            "title": "Shift Requests",
            "description": "A guided tour of shift requests — creating, approving, rejecting and tracking employee shift change requests.",
            "page_match": "shift-request-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "swap-horizontal-outline",
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
        ("horilla_tour", "0021_seed_document_requests_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
