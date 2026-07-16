from django.db import migrations


SLUG = "tickets-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Tickets",
        "description": "The Tickets page is a kanban-style helpdesk board where employees raise support requests and managers track their resolution. Tickets are organised into status columns — New, In Progress, Resolved and so on — so the whole team can see what is open, what is being worked on and what is done.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Ticket Pipeline",
        "description": "The pipeline board shows tickets as cards arranged in status columns. Drag a ticket card from one column to another to update its status instantly. Click any card to open the full ticket detail — including the description, attachments, assigned agent and activity log.",
        "element_selector": "#pipelineContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "My Tickets",
        "description": "The My Tickets tab shows only the tickets you have raised. Use this tab to track the status of your own support requests and to follow up on tickets that are waiting for a response from you.",
        "element_selector": ".oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Suggested Tickets",
        "description": "The Suggested Tickets tab surfaces tickets that are relevant to you based on your role, department or expertise — tickets you can help resolve even if they were not assigned to you directly.",
        "element_selector": ".oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "All Tickets",
        "description": "The All Tickets tab gives managers and helpdesk administrators a full view of every ticket in the system regardless of who raised it or who it is assigned to. Use this tab to monitor overall workload, reassign tickets and ensure nothing falls through the cracks.",
        "element_selector": ".oh-tabs__tab[data-tab-index='2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Create Ticket",
        "description": "Click Create to raise a new support ticket. Fill in the title, select the ticket type and priority, add a description and optionally attach files. The ticket appears on the board immediately in the New column and is visible to the relevant team.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Ticket Actions",
        "description": "The Actions menu lets managers perform bulk operations on selected tickets — Archive closed tickets to keep the board clean, Unarchive tickets that need to be reopened, or Delete tickets that were created in error.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "List & Card Views",
        "description": "Toggle between the kanban Card view and the tabular List view using the view switcher. The card view is ideal for visualising workflow across statuses; the list view is better for sorting and scanning many tickets at once.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Filter",
        "description": "Click Filter to narrow tickets by status, priority, ticket type, assigned agent, department, raised-by employee or date range. Combine filters to focus on exactly the tickets you need to review.",
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
            "title": "Tickets",
            "description": "A guided tour of the Tickets helpdesk board — raising tickets, tracking status through the pipeline, managing assignments and using filters to stay on top of open requests.",
            "page_match": "ticket-view",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "ticket-outline",
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
        ("horilla_tour", "0065_seed_faq_categories_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
