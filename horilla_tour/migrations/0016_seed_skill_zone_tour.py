from django.db import migrations


SLUG = "skill-zone-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Skill Zone",
        "description": "Skill Zone is a talent pool — a place to park strong candidates who were not hired this time but should be considered for future openings. Organised by skill or role, not by recruitment.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Skill Zone Groups",
        "description": "Each skill zone is a named group — for example 'Python Developers' or 'Sales Talent'. Click any group row to expand it and see the candidates stored inside.",
        "element_selector": "#skill_zone_container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Candidates Inside a Skill Zone",
        "description": "Expanded rows show each candidate's name, reason for adding them, date added and a link to their resume. Click a candidate row to open their full profile.",
        "element_selector": "#skill_zone_container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Search & Filter",
        "description": "Search by candidate name or use the Filter button to narrow by candidate, recruitment, job position, reject reason, offer letter status and more.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Create a Skill Zone",
        "description": "Click Create to add a new skill zone group — give it a title and description that reflects the skill set or role you want to pool candidates for.",
        "element_selector": "a.oh-btn--secondary.oh-btn--shadow",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Add Candidates to a Skill Zone",
        "description": "Use the person+ icon on any skill zone row to add a candidate to that pool. You can also add candidates directly from the pipeline when rejecting or archiving them.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Edit & Archive Skill Zones",
        "description": "Use the edit icon to rename a skill zone, the archive icon to hide it without deleting, and the trash icon to permanently remove it.",
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
            "title": "Skill Zone",
            "description": "A guided tour of Skill Zone — talent pools for storing strong candidates for future recruitments.",
            "page_match": "skill-zone-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "flash-outline",
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
        ("horilla_tour", "0015_fix_stage_create_button_selector"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
