from django.db import migrations


SLUG = "multiple-approval-condition-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Multiple Approval Condition",
        "description": "The Multiple Approval Condition page lets you define rules that require more than one approver for specific requests — such as leave, overtime or expenses — based on conditions like department, employee type or amount. Once configured, requests matching a condition are automatically routed through the multi-level approval chain.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Conditions List",
        "description": "Each row shows one approval condition — the condition name, the module it applies to (Leave, Attendance, etc.), the criteria that trigger it and the number of approval levels required. Click any row to view the full condition detail including the ordered list of approvers.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Condition",
        "description": "Click Create to define a new multiple approval condition. Select the module, set the criteria (such as department or employee type), then add the ordered approvers for each level. Requests that match the condition will require sign-off from every approver in sequence before they are approved.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Condition Detail",
        "description": "Click any condition row to open its detail view. Here you can review the full approval chain — each level's approver, the criteria that trigger the condition and the module it applies to. Use this view to verify that the routing is set up correctly before it goes live.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Search",
        "description": "Use the search bar to quickly locate an approval condition by name or module. The list updates as you type, making it easy to find a specific condition when you have many configured.",
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
            "title": "Multiple Approval Condition",
            "description": "A guided tour of the Multiple Approval Condition page — creating multi-level approval rules, defining criteria and reviewing approval chains.",
            "page_match": "multiple-approval-condition",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "git-merge-outline",
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
        ("horilla_tour", "0076_seed_pms_report_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
