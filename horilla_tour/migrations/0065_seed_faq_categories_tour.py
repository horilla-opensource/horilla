from django.db import migrations


SLUG = "faq-categories-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "FAQ Categories",
        "description": "The FAQ Categories page organises your company's Frequently Asked Questions into topic-based groups. Employees can search and browse FAQs here to find answers without raising a support ticket. Admins manage the categories and the questions within each one.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Category Cards",
        "description": "Each card represents one FAQ category — showing its title and the questions it contains. Click a category card to expand it and read the FAQs within that topic. Categories keep related questions grouped so employees can browse by subject.",
        "element_selector": "#faqCategoryList",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Category",
        "description": "Click Create to add a new FAQ category. Give it a clear title that describes the topic — for example Payroll, Leave Policy or IT Support. Once created, you can add individual FAQ questions to it.",
        "element_selector": "button[hx-get*='faq-category-create']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Adding FAQs",
        "description": "Click View FAQs on any category card to open that category and manage its questions. Use the Add FAQ button inside to create a new question and rich-text answer. You can add as many FAQs as needed within a category.",
        "element_selector": "a[href*='faq-view']",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Category Actions",
        "description": "Each category card has an actions menu — click the ellipsis icon on the card to Edit the category title or Delete it. Deleting a category removes all the FAQs within it, so make sure to reassign or note any important content before deleting.",
        "element_selector": "a.dropdown-toggle",
        "side": "left",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Use the search bar to find FAQs by keyword across all categories. As you type, matching questions are suggested — select one to jump directly to the answer. This is the fastest way for employees to self-serve answers.",
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
            "title": "FAQ Categories",
            "description": "A guided tour of the FAQ Categories page — creating categories, adding questions, managing content and helping employees find answers quickly.",
            "page_match": "faq-category-view",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "help-circle-outline",
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
        ("horilla_tour", "0064_seed_asset_history_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
