from django.db import migrations


SLUG = "automations-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Automations",
        "description": "The Automations page lets you configure automated email and in-app notifications that fire when specific events happen — such as a leave request being approved, a new employee being onboarded, or an attendance record being created. Once set up, automations run silently in the background without any manual action.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Automations List",
        "description": "Each row shows one configured automation — its title, the model it watches, the trigger event, the delivery channel (Email, Notification or both) and the email mapping (who the message is sent to). Click any row to open the full detail view.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Automation",
        "description": "Click Create to define a new automation. Choose the model to watch (e.g. Leave Request), select the trigger event (created, updated, etc.), write the email subject and body using dynamic placeholders, and choose whether to send via email, in-app notification or both.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Automation Detail",
        "description": "Click any automation row to open its detail view. The detail panel shows the full configuration — trigger, conditions, recipients and message body. Use the Edit button to modify the automation or the Delete button to remove it permanently.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Actions",
        "description": "The Actions menu provides two utilities: 'Load Automations' lets you import pre-built automation templates directly into your configuration; 'Refresh Automations' reconnects the automation signal handlers — use this if automations stop firing after a server restart or configuration change.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to filter automations by title or model name. The list updates as you type, making it easy to locate a specific automation when you have many configured.",
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
            "title": "Automations",
            "description": "A guided tour of the Automations page — creating event-driven email and notification rules, loading pre-built templates and managing your automation library.",
            "page_match": "mail-automations",
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
        ("horilla_tour", "0079_seed_mail_templates_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
