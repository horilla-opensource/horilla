from django.db import migrations


SLUG = "scheduled-interviews-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Scheduled Interviews",
        "description": "The Scheduled Interviews page lists every interview across all recruitments in one place. Each row shows the candidate, assigned interviewers, date, time and a live status — Upcoming, Interview Today, Completed or Expired — calculated automatically.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Interview List",
        "description": "Each row shows the candidate name, interviewer(s), scheduled date and time, description and current status. Click any row to open the full interview detail — update the outcome, add notes or reschedule from there.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Schedule an Interview",
        "description": "Click Create to schedule a new interview. Select the candidate, assign one or more interviewers, set the date and time, and add a description or agenda. The interview appears in the list immediately.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Interviewer, Interview Time, Description or Status — so you can focus on the data you need.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Type in the search box to filter interviews by candidate name or interviewer. The list updates as you type — handy for finding a specific interview in a busy schedule.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter",
        "description": "Click Filter to narrow the list by candidate, interviewer, interview date range or status. Use date filters to see all interviews due today or this week at a glance.",
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
            "title": "Scheduled Interviews",
            "description": "A guided tour of the scheduled interviews list — statuses, filtering, scheduling and managing interviews.",
            "page_match": "interview-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "calendar-number-outline",
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
        ("horilla_tour", "0011_seed_candidate_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
