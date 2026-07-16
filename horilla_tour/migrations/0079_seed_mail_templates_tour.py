from django.db import migrations


SLUG = "mail-templates-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Mail Templates",
        "description": "The Mail Templates page lets you create and manage reusable email templates used throughout the system — for leave approvals, onboarding messages, payroll notifications and more. Templates support dynamic placeholders so each email is personalised with the recipient's data.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Templates Gallery",
        "description": "Each card in the gallery represents one mail template. The card shows the template name and a preview of the body content. Scroll through the gallery to browse all available templates at a glance.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Template",
        "description": "Click Create to add a new mail template. Give it a title, write the body using the rich-text editor, and insert dynamic placeholders by typing '{' to auto-complete with sender or receiver fields such as name, department or leave dates.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Template Card",
        "description": "Each card displays the template name and a scrollable preview of its body. The preview gives you a quick visual check of the layout and content before you open it for editing.",
        "element_selector": "#listContainer div.rounded-md.border",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "View & Edit Template",
        "description": "Click 'View Template' on any card to open the template in a modal editor. You can update the title, rewrite the body, adjust the company scope and save your changes. The rich-text editor supports formatting and the '{' shortcut for inserting data placeholders.",
        "element_selector": "button[hx-get*='mail-template-edit-form']",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Duplicate & Delete",
        "description": "Use the icons in the top-right corner of each card to duplicate or delete a template. Duplicate copies the template so you can customise a variant without starting from scratch. Delete permanently removes the template — confirm the prompt before proceeding.",
        "element_selector": "a[title='Duplicate']",
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
            "title": "Mail Templates",
            "description": "A guided tour of the Mail Templates page — creating reusable email templates with dynamic placeholders, editing existing ones and managing duplicates.",
            "page_match": "view-mail-templates",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "mail-outline",
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
        ("horilla_tour", "0078_seed_multiple_approval_condition_form_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
