from django.db import migrations


SLUG = "onboarding-pipeline-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Onboarding Pipeline",
        "description": "The Onboarding Pipeline guides new hires from offer acceptance through to becoming a fully active employee. Each active recruitment appears as a tab, and within each tab candidates move through customisable onboarding stages represented as columns.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Pipeline Board",
        "description": "The pipeline board shows all active onboarding recruitments as tabs. Switch between List view and Card (kanban) view using the toggle buttons to change how the stage columns are displayed.",
        "element_selector": "#pipelineContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Recruitment Tabs",
        "description": "Each tab represents one active recruitment whose candidates are being onboarded. Click a tab to focus on that pipeline — its onboarding stage columns and candidate cards load below. The badge shows how many stages that recruitment has.",
        "element_selector": ".oh-tabs__tab",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Stage Actions",
        "description": "Click the ellipsis (⋮) on any recruitment tab to access stage management — Add Stage to create a new onboarding step, or Manage Stage Order to resequence the columns in the pipeline.",
        "element_selector": ".oh-tabs__tab .oh-accordion-meta__btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Stage Column",
        "description": "Each column is one onboarding stage — such as Document Signing, Equipment Setup or Induction. In list view click the header to collapse or expand the stage. In card view, candidate cards show task progress and joining date at a glance.",
        "element_selector": ".oh-tabs__movable-header",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "List & Card Views",
        "description": "Use the view toggle to switch between List view — a table of candidates per stage — and Card view — a kanban board where you can drag candidates between stages. Both views update in real time.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Search",
        "description": "Type in the search box to filter candidates across all onboarding stages by name. The pipeline updates as you type — useful when managing a large cohort of new joiners.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Filter",
        "description": "Click Filter to narrow the pipeline by recruitment, department, joining date or onboarding stage. Use this to focus on a specific team's new joiners or to review candidates at a particular stage.",
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
            "title": "Onboarding Pipeline",
            "description": "A guided tour of the onboarding pipeline — stages, candidate cards, tasks and converting to employee.",
            "page_match": "cbv-pipeline-onboarding",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "rocket-outline",
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
        ("horilla_tour", "0016_seed_skill_zone_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
