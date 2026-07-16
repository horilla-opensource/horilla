from django.db import migrations


SLUG = "disciplinary-actions-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Disciplinary Actions",
        "description": "This page records and manages disciplinary actions taken against employees — warnings, suspensions, terminations and other formal actions. Each record is linked to the employee and includes the action type, date and supporting details.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Actions List",
        "description": "Each row shows the employee name, the type of disciplinary action taken, the action date, whether login is blocked, any attachments and a description. Click any row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Disciplinary Action",
        "description": "Click Create to record a new disciplinary action. Select the employee, choose the action type, set the date, optionally block their login, and attach any supporting documents such as warning letters.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Action Taken, Login Block, Action Date, Attachments and Description.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Row Actions",
        "description": "Each row has action icons to edit the record, duplicate it for another employee, or delete it. Click the row itself to open the full detail view including follow-up notes and attached files.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to filter disciplinary records by employee name. The list updates as you type — useful when reviewing a specific employee's history.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow the list by action type, action date, department, company or reporting manager. Use this to audit disciplinary records across a team or time period.",
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
            "title": "Disciplinary Actions",
            "description": "A guided tour of disciplinary actions — recording, reviewing and managing formal disciplinary measures for employees.",
            "page_match": "disciplinary-actions",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "alert-circle-outline",
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
        ("horilla_tour", "0027_seed_roster_planner_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
