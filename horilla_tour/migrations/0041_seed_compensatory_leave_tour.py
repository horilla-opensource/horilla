from django.db import migrations


SLUG = "compensatory-leave-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Compensatory Leave Requests",
        "description": "This page manages compensatory leave — additional leave days granted to employees who work on public holidays or outside their scheduled hours. Employees can submit requests for compensatory leave, and managers review and approve or reject them here.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "My Requests Tab",
        "description": "The My Compensatory Leave Requests tab shows all compensatory leave requests you have submitted yourself — including the dates worked, the number of compensatory days requested and the current approval status.",
        "element_selector": ".oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "All Requests Tab",
        "description": "The Compensatory Leave Requests tab shows all requests submitted by employees across your team. Use this tab to review pending requests and take approval or rejection actions.",
        "element_selector": ".oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Requests List",
        "description": "Each row shows a compensatory leave request — the employee name, the date they worked extra, the number of compensatory days requested and the current status. Click any row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "New Compensatory Request",
        "description": "Click Create to submit a new compensatory leave request. Select the employee, the date they worked (on a holiday or day off), and the number of compensatory days being requested.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Approve & Reject",
        "description": "Click any request row to open its detail view where you can approve or reject it. Approving a compensatory leave request automatically adds the days to the employee's leave balance.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find requests by employee name. Use the Filter button to narrow results by status, date range, department or reporting manager.",
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
            "title": "Compensatory Leave Requests",
            "description": "A guided tour of the Compensatory Leave Requests page — submitting, reviewing and approving compensatory leave for employees who work on holidays or off-days.",
            "page_match": "view-compensatory-leave",
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
        ("horilla_tour", "0040_seed_leave_allocation_requests_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
