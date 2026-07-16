from django.db import migrations


SLUG = "leave-allocation-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Leave Allocation Requests",
        "description": "This page manages requests for additional leave days. Employees can request extra allocation beyond their standard entitlement — for example requesting additional annual leave days. Managers review and approve or reject those requests here.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "My Requests Tab",
        "description": "The My Leave Allocation Request tab shows all allocation requests you have submitted yourself — including their current approval status and the number of days requested.",
        "element_selector": "#leave-allocation .oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "All Requests Tab",
        "description": "The Leave Allocation Requests tab shows all requests submitted by employees across your team. Use this tab to review pending requests and take approval actions.",
        "element_selector": "#leave-allocation .oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Requests List",
        "description": "Each row shows an allocation request — the employee name, the leave type they are requesting extra days for, the number of days requested, the reason given and the current status (pending, approved or rejected).",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "New Allocation Request",
        "description": "Click Create to submit a new allocation request on behalf of an employee. Select the employee, the leave type, the number of additional days needed and the reason for the request.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Approve & Reject",
        "description": "Click any request row to open its detail view where you can approve or reject it. Approving a request automatically adds the allocated days to the employee's leave balance for that leave type.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find requests by employee name. Use the Filter button to narrow results by leave type, status, number of days or reporting manager. Use Group By to organise the list by employee, leave type or status.",
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
            "title": "Leave Allocation Requests",
            "description": "A guided tour of the Leave Allocation Requests page — submitting, reviewing and approving requests for additional leave days.",
            "page_match": "leave-allocation-request-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "add-circle-outline",
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
        ("horilla_tour", "0039_seed_assigned_leaves_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
