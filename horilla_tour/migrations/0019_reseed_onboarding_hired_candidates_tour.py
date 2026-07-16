from django.db import migrations


SLUG = "onboarding-hired-candidates-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Hired Candidates",
        "description": "The Hired Candidates page lists every candidate who has been marked as hired and is currently going through onboarding. From here you can manage their joining date, probation period, portal access and offer letter — all in one place.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Candidates List",
        "description": "Each row shows a hired candidate with their name, email, joining date, probation end date, job position, recruitment and offer letter status. Click any row to open the candidate's full onboarding profile.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Hired Candidate",
        "description": "Click Create to manually add a hired candidate to the onboarding list. Set their personal details, assign a recruitment and joining date so they appear in the pipeline immediately.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Send Portal Link",
        "description": "Click the portal link icon on any candidate row to send them their onboarding self-service portal link. They can log in to complete tasks, upload documents and track their own onboarding progress without involving HR for every step.",
        "element_selector": "a[title*=\"Send Portal\"]",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Start Onboarding",
        "description": "Each candidate row has two action icons — the + (Start Onboarding) icon adds the candidate to the onboarding pipeline so tasks and stages can be assigned. Once added, the icon changes to a teal colour indicating they are already in the pipeline.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Toggle Columns",
        "description": "Click the column settings button at the top-right of the table to show or hide columns — Email, Joining Date, Probation End, Offer Letter and more — to focus on the data relevant to your workflow.",
        "element_selector": "button.oh-sticky-dropdown_btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Type in the search box to filter hired candidates by name. The list updates as you type — useful when managing a large onboarding cohort and need to locate someone quickly.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow the list by recruitment, job position, joining date range, probation period, portal sent status or offer letter status. Use Group By to organise candidates by recruitment or department.",
        "element_selector": "#filterForm .dropdown-wrapper",
        "side": "bottom",
        "align": "start",
    },
]


def reseed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    Tour.objects.filter(slug=SLUG).delete()

    tour = Tour.objects.create(
        slug=SLUG,
        title="Hired Candidates",
        description="A guided tour of the onboarding hired candidates list — portal links, joining dates, offer letters and converting to employee.",
        page_match="candidates-view",
        match_type="url_name",
        audience="managers",
        trigger="auto_once",
        priority=50,
        icon="person-add-outline",
        is_published=True,
    )
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
        ("horilla_tour", "0018_seed_onboarding_hired_candidates_tour"),
    ]

    operations = [
        migrations.RunPython(reseed, unseed),
    ]
