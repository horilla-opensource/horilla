from django.db import migrations


SLUG = "faq-view-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "FAQ View",
        "description": "This page shows all the Frequently Asked Questions within this category. Employees can browse and expand questions to read the answers. Managers can add new FAQs, filter by tags and delete or edit existing entries.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "FAQ List",
        "description": "Each row is one FAQ. Click a row to expand it and read the full answer. The question is shown in the header and the answer appears below along with any tags that categorise it further.",
        "element_selector": "#faqList",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create FAQ",
        "description": "Click Create to add a new question and answer to this category. Write the question, add a rich-text answer and optionally assign tags to make it easier to filter. Published FAQs are immediately visible to all employees.",
        "element_selector": "button.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Filter by Tag",
        "description": "Click Filter to narrow the FAQ list by tag. Tags help organise FAQs within a category — for example by policy area or topic. Select one or more tags and apply the filter to show only matching questions.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Use the search bar to find FAQs by keyword. As you type the list updates to show matching questions from this category. This is the fastest way to locate a specific answer without scrolling through all entries.",
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
            "title": "FAQ View",
            "description": "A guided tour of the FAQ View page — browsing questions and answers, creating new FAQs and filtering by tag within a category.",
            "page_match": "faq-view",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "chatbubble-ellipses-outline",
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
        ("horilla_tour", "0086_seed_objective_detailed_view_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
