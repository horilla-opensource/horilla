from django.db import migrations


SLUG = "onboarding-hired-candidates-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Hired Candidates",
        "description": "This page lists all candidates who have been hired and are currently going through the onboarding process. You can manage their joining date, probation period, portal access and offer letter from here.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Candidates List",
        "description": "Each row shows a hired candidate along with their recruitment, joining date, probation end date, portal link status and offer letter status.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Send Portal Link",
        "description": "Use the Send Portal Link action to email the onboarding self-service portal link to candidates. They can log in to complete tasks, upload documents and track their own onboarding progress.",
        "element_selector": "#trigger-onboarding",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Joining Date & Probation",
        "description": "Set or update each candidate's joining date and probation end date directly from the list. These dates are used to track their employment timeline.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Offer Letter Status",
        "description": "Track whether the offer letter has been sent, accepted or rejected for each candidate. You can resend or update the offer letter from the actions menu.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Filter Candidates",
        "description": "Use the Filter button to narrow the list by recruitment, job position, joining date range, probation period, portal sent status or offer letter status.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Convert to Employee",
        "description": "Once onboarding is complete, use the Convert to Employee option on a candidate to create their full employee profile — payroll, attendance and leave modules will all be ready for them.",
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
            "title": "Hired Candidates",
            "description": "A guided tour of the onboarding hired candidates list — portal links, joining dates, offer letters and converting to employee.",
            "page_match": "candidates-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "person-add-outline",
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
        ("horilla_tour", "0017_seed_onboarding_pipeline_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
