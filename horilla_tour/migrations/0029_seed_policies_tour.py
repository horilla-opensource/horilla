from django.db import migrations


SLUG = "policies-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Policies",
        "description": "This page stores and manages your organisation's HR policies — such as leave policy, code of conduct, remote work guidelines and more. Policies can be shared with all employees or restricted to specific groups.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Policy Cards",
        "description": "Each card represents one policy document. A green dot means the policy is visible to all employees; a red dot means it is restricted. Click View Policy on any card to read the full content.",
        "element_selector": "#policyContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create a Policy",
        "description": "Click Create to add a new policy. Give it a title, write or paste the content, attach any related documents such as PDFs or Word files, and choose whether it should be visible to all employees or only specific ones.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Visibility Control",
        "description": "Each policy card shows a coloured dot — green means all employees can see it from their self-service portal, red means it is restricted. Update visibility at any time by editing the policy.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Edit & Delete",
        "description": "Each card has an edit icon to update the policy content, title or visibility, and a delete icon to permanently remove it. Changes take effect immediately for all employees who can see the policy.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to filter policies by title. The cards update as you type — useful when you have many policies and need to locate one quickly.",
        "element_selector": "input[name='search']",
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
            "title": "Policies",
            "description": "A guided tour of the Policies page — creating, managing and sharing HR policy documents with employees.",
            "page_match": "view-policies",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "document-outline",
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
        ("horilla_tour", "0028_seed_disciplinary_actions_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
