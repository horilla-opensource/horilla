from django.db import migrations


SLUG = "recruitment-list-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Recruitment",
        "description": "The Recruitment page lists all your hiring drives. Each row is one recruitment — showing its title, assigned managers, open job positions, vacancy target, total hires to date, start and end dates, and whether it is open or closed.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Recruitment List",
        "description": "Each row represents one recruitment drive. Click a row to open its detail panel — where you can view the full record, edit settings, or access the pipeline for that job opening. A coloured left border indicates whether it is open or closed.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Recruitment",
        "description": "Click Create to start a new recruitment drive. Set the title, assign recruitment managers, add job positions, define the vacancy count, attach survey templates, and set the start and end dates.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Managers, Open Jobs, Vacancy, Total Hires, Start Date or End Date — so you can tailor the view to what you need.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Type in the search box to filter recruitments by title. The list updates as you type — helpful when you manage many open and closed positions and need to locate one quickly.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter",
        "description": "Click Filter to narrow the list by job position, department, company, open or closed status, and start or end date range. Use the closed filter to review historical recruitment data.",
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
            "title": "Recruitment",
            "description": "A guided tour of the recruitment list — creating, managing and sharing recruitment drives.",
            "page_match": "recruitment-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "briefcase-outline",
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
        ("horilla_tour", "0012_seed_scheduled_interviews_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
