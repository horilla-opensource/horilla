from django.db import migrations


SLUG = "attendance-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Attendance Requests",
        "description": "This page manages employee requests to correct or add attendance records. Employees can raise a request when they miss a clock-in or need to adjust their attendance details. Managers review and approve or reject those requests here.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Requested Attendances Tab",
        "description": "The Requested Attendances tab shows all pending correction requests submitted by employees. Each row displays the employee, the requested check-in and check-out times, and the current approval status.",
        "element_selector": "#attendance-container .oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "All Attendances Tab",
        "description": "Switch to the All Attendances tab to see every attendance record across all employees — including those that were never flagged for correction. Use this for a complete audit view.",
        "element_selector": "#attendance-container .oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Records List",
        "description": "Each row in the list shows the employee name, the original attendance details, the corrected values they requested, and whether the request is pending, approved or rejected. Click a row to open the full detail and take action.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "New Attendance Request",
        "description": "Click Create to submit a new attendance request on behalf of an employee — useful when a manager needs to add or correct a record directly. Fill in the employee, date, check-in and check-out times and the reason for the change.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Approve & Reject",
        "description": "Click any request row to open its detail view where you can approve or reject it. Use Actions → Bulk Approve or Bulk Reject to process multiple selected requests at once.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter & Search",
        "description": "Use the search bar to find requests by employee name. Use the Filter button to narrow results by date range, department, approval status or reporting manager.",
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
            "title": "Attendance Requests",
            "description": "A guided tour of the Attendance Requests page — reviewing, approving and managing employee attendance correction requests.",
            "page_match": "request-attendance-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "clipboard-outline",
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
        ("horilla_tour", "0030_seed_attendances_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
