from django.db import migrations


SLUG = "recruitment-dashboard"

STEPS = [
    {
        "sequence": 1,
        "title": "Recruitment Dashboard",
        "description": "This dashboard gives you a real-time view of your entire hiring operation — vacancies, candidates, pipeline health and interview schedule all in one place.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "KPI Cards",
        "description": "Total vacancies, ongoing recruitments, candidates hired, conversion rate and offer acceptance rate — your key hiring metrics updated live.",
        "element_selector": "#rd-kpi-grid",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Stage Conversion Funnel",
        "description": "See how many candidates move through each hiring stage and where drop-offs happen. Click a bar to drill into that stage's candidates.",
        "element_selector": "#chart-conversion-funnel",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Candidates by Stage",
        "description": "A breakdown of all active candidates across your pipeline stages — Initial, Test, Interview, Hired and Cancelled.",
        "element_selector": "#chart-stage-summary",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Offer Letter Status",
        "description": "Track how many offer letters are pending, accepted or rejected across all candidates at a glance.",
        "element_selector": "#chart-offer-status",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Source of Hire",
        "description": "Understand where your successful candidates come from — application form, referrals, internal or other sources.",
        "element_selector": "#chart-source-hire",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Hiring Pipeline Table",
        "description": "A full breakdown of every active recruitment — showing candidate counts per stage so you can spot bottlenecks instantly.",
        "element_selector": "#rd-pipeline-table",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Interviews Panel",
        "description": "All interviews scheduled within the selected period are listed here — candidate name, stage and time at a glance.",
        "element_selector": "#rd-interviews",
        "side": "left",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Filter by Period",
        "description": "Use the period picker to focus on this month, last month, the quarter, or any custom date range. All charts and KPIs update instantly.",
        "element_selector": "#rd-open-customize",
        "side": "left",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Recruitment Dashboard",
            "description": "A guided tour of the recruitment dashboard — KPIs, pipeline, charts and interview schedule.",
            "page_match": "recruitment-dashboard",
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
        ("horilla_tour", "0008_fix_create_button_selector"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
