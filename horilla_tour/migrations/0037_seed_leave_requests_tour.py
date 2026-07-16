from django.db import migrations


SLUG = "leave-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Leave Requests",
        "description": "This page is the central place for managing all employee leave requests across your organisation. You can review pending requests, approve or reject them, check leave clashes and track the full leave history for every employee.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Requests List",
        "description": "Each row shows a leave request — the employee name, leave type, start and end dates, number of days requested, leave clash indicator, and the current approval status. Click any row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create a Leave Request",
        "description": "Click Create to raise a leave request on behalf of an employee — useful when a manager needs to record leave directly. Select the employee, leave type and dates, then submit.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Bulk Actions",
        "description": "Click Actions to bulk approve or bulk reject selected requests at once, or to export the list as a spreadsheet. Select rows using their checkboxes first.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Approve",
        "description": "Each pending request row has an Approve button. Click it to accept the leave — the employee's leave balance is deducted immediately and they are notified.",
        "element_selector": "a[title='Approve']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Reject",
        "description": "Click the Reject button on a request row to decline the leave. You will be prompted to enter a reason which is sent back to the employee.",
        "element_selector": "a[title='Reject']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Leave Clashes",
        "description": "The groups icon on each row shows how many teammates have overlapping leave on the same dates. Click it to open the clash details and see who else is off before deciding whether to approve.",
        "element_selector": "div[data-target='#clashModal']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Employee, Leave Type, Start Date, End Date, Requested Days, Leave Clash, Status and more.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Search",
        "description": "Type in the search box to filter requests by employee name. The list updates as you type — useful when managing leave across a large team.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 10,
        "title": "Filter",
        "description": "Click Filter to narrow the list by leave type, status, date range, department or reporting manager. Use Group By to organise requests by employee, leave type or date.",
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
            "title": "Leave Requests",
            "description": "A guided tour of the Leave Requests page — reviewing, approving, rejecting and managing employee leave requests.",
            "page_match": "request-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "calendar-outline",
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
        ("horilla_tour", "0036_seed_my_leave_request_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
