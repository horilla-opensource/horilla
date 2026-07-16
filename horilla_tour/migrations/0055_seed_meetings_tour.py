from django.db import migrations


SLUG = "meetings-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Meetings",
        "description": "The Meetings page is where one-on-one and group meetings between managers and employees are tracked. Each meeting record stores the agenda, the attendees, the date and the Minutes of Meeting (MoM) — creating a written record of what was discussed and agreed.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Meetings List",
        "description": "Each row shows one meeting — the title, the employees invited, the managers involved, the meeting date and a MoM (Minutes of Meeting) indicator. Click any row to open the full meeting detail in a modal.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Meeting",
        "description": "Click Create to schedule a new meeting. Set the title, select the manager and employees, pick the date, add an agenda, and optionally attach a question template for structured discussion. After the meeting, you can fill in the MoM directly from the detail view.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Minutes of Meeting (MoM)",
        "description": "The MoM column shows whether minutes have been recorded for each meeting. After a meeting, open the detail view and fill in what was discussed, any decisions taken and action items assigned. MoM entries become a searchable log of your team conversations.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Meeting Detail",
        "description": "Click any meeting row to open the full detail — attendees, agenda, date, MoM notes and any linked question-and-answer responses. Managers can edit or update the record directly from this view.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Use the search bar to quickly find meetings by title or employee name. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow the meeting list by employee, manager, date range or active status.",
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
            "title": "Meetings",
            "description": "A guided tour of the Meetings page — scheduling meetings, recording Minutes of Meeting and tracking manager-employee conversations.",
            "page_match": "view-meetings",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "people-outline",
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
        ("horilla_tour", "0054_seed_feedbacks_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
