from django.db import migrations


SLUG = "my-leave-request-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "My Leave Requests",
        "description": "This page shows all the leave requests you have submitted. You can track the status of each request, view the details of approved or rejected leaves, and submit new leave requests directly from here.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Your Leave Requests",
        "description": "Each row shows one leave request — the leave type, the start and end dates, the number of days requested, the current status and a cancel button. Click any row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Request a Leave",
        "description": "Click Create to submit a new leave request. Select the leave type, set the start and end dates, add a reason if required, and submit. Your manager will be notified to review and approve or reject it.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Request Status",
        "description": "Each row has a coloured left border showing the status — Requested (pending manager review), Approved (accepted, days deducted from balance), Rejected (declined) or Cancelled (withdrawn by you).",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Cancel a Request",
        "description": "Each row has a Cancel button in the last column. Click it to withdraw an approved leave request before its end date. Cancelling returns the deducted days to your leave balance.",
        "element_selector": ".oh-btn--primary",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Leave Type, Start Date, End Date, Requested Days, Status and Comment.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Type in the search box to filter your leave requests by leave type or keyword. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow your requests by leave type, status, date range or number of requested days. Use Group By to reorganise the list by leave type or status for a quick overview.",
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
            "title": "My Leave Requests",
            "description": "A guided tour of the My Leave Requests page — submitting, tracking and managing your personal leave requests.",
            "page_match": "user-request-view",
            "match_type": "url_name",
            "audience": "all",
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
        ("horilla_tour", "0035_seed_my_attendances_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
