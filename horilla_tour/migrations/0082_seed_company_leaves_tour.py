from django.db import migrations


SLUG = "company-leaves-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Company Leaves",
        "description": "The Company Leaves page lets you define which days of the week are treated as mandatory rest days for the company — for example, every Friday or every Sunday. These weekly rest days are factored into leave balance calculations and attendance tracking automatically.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Company Leaves List",
        "description": "Each row shows one configured company leave — the week it falls in and the specific day of the week. Click any row to open its detail panel where you can review the full record or make edits.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Company Leave",
        "description": "Click Create to add a new weekly rest day. Select the week number (first, second, last, etc.) and the day of the week (Monday through Sunday). Optionally restrict the leave to a specific company in multi-company setups.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Company Leave Detail",
        "description": "Click any row to open the detail view for that company leave. The panel shows which week and day are configured, along with the company it applies to. Use the Edit button to update the record or the Delete button to remove it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Type in the search box to filter company leaves by week or day. The list updates as you type — useful when you have multiple companies each with different weekly rest day configurations.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter",
        "description": "Click Filter to narrow the list by week, day of week or company. Use this to quickly review the rest day rules for a specific company or to check whether a particular day is already configured.",
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
            "title": "Company Leaves",
            "description": "A guided tour of the Company Leaves page — defining weekly rest days, reviewing configured records and managing company-specific rest day rules.",
            "page_match": "company-leave-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "calendar-clear-outline",
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
        ("horilla_tour", "0081_seed_holidays_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
