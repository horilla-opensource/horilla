from django.db import migrations


SLUG = "candidate-view-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Candidates",
        "description": "The Candidates page is a consolidated view of every applicant across all your active recruitments. Search, filter, group and manage candidates — regardless of which pipeline or stage they are currently in.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Candidates List",
        "description": "The main area lists all candidates with their name, email, phone, rating, recruitment and job position. Click any row to open the full candidate profile — resume, interview history, survey responses and offer letter status.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Candidate",
        "description": "Click Create to manually add a new candidate. Fill in their personal details, assign a recruitment and starting stage, and the candidate appears in the pipeline immediately.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Actions Menu",
        "description": "The Actions menu provides bulk operations — Export candidate data to a spreadsheet, send Bulk Mail, create a Document Request, Archive or Un-archive selected candidates, and Delete in bulk. Select candidates using the checkboxes first.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "List & Card Views",
        "description": "Switch between List view for a detailed table and Card view for a visual grid. Use the toggle icons next to the search bar to change the layout. Your last-used view is remembered.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to filter candidates by name. The list updates as you type — useful when you have a large candidate pool and need to locate someone quickly.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow the list by recruitment, stage, hired status, source, department, job position, country and more. You can also use Group By inside the filter to organise results by recruitment, stage or other fields.",
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
            "title": "Candidates",
            "description": "A guided tour of the candidate list — searching, filtering, views and managing candidates.",
            "page_match": "candidate-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "person-outline",
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
        ("horilla_tour", "0010_seed_recruitment_survey_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
