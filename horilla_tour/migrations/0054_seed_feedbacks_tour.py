from django.db import migrations


SLUG = "feedbacks-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Feedbacks",
        "description": "The Feedbacks page is the hub for 360-degree performance reviews. Employees can see their own feedback, managers can review feedback given to their team, and anonymous feedback lets peers share candid insights without attribution.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Self Feedback Tab",
        "description": "The Self Feedback tab shows all feedback cycles assigned to you as the employee being reviewed. Each row shows the review title, status and due date. Click a row to open the full feedback detail and see the questions and answers.",
        "element_selector": ".oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Requested Feedback Tab",
        "description": "The Requested Feedback tab shows feedback requests where you have been asked to give input — as a manager, colleague, subordinate or other reviewer. Click any row to open the feedback form and submit your response.",
        "element_selector": ".oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Feedbacks to Review Tab",
        "description": "The Feedbacks to Review tab is available to managers and admins. It shows all feedback cycles across your direct reports so you can monitor progress, check completion and take action on overdue or at-risk reviews.",
        "element_selector": ".oh-tabs__tab[data-tab-index='2']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Anonymous Feedback Tab",
        "description": "The Anonymous Feedback tab shows feedback submitted without revealing the reviewer's identity. Use the Add Anonymous button to create an anonymous feedback entry for any employee.",
        "element_selector": ".oh-tabs__tab[data-tab-index='3']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Feedback List",
        "description": "Each row shows the employee under review, the review cycle title, the current status (On Track, Behind, At Risk, Closed), the start date and the due date. Click any row to open the full feedback detail.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Feedback Status",
        "description": "Each feedback row has a coloured left border and a status dot — green for On Track, orange for Behind, red for At Risk, blue for Closed and grey for Not Started. Click any status dot in the list header to filter by that status instantly.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Create Feedback",
        "description": "Click Create to set up a new feedback cycle. Select the employee, choose the review period, assign managers, colleagues and subordinates as reviewers, and pick the question template. Once created, the system notifies all reviewers.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Actions",
        "description": "Use the Actions menu to Archive or Un-Archive selected feedback cycles, create Bulk Feedback for multiple employees at once, or Delete selected entries.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 10,
        "title": "Search",
        "description": "Use the search bar to quickly find feedback cycles by employee name or review title. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 11,
        "title": "Filter",
        "description": "Click Filter to narrow feedback cycles by employee, status, date range, reviewer or other criteria.",
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
            "title": "Feedbacks",
            "description": "A guided tour of the Feedbacks page — creating 360-degree review cycles, tracking feedback status, and managing self, requested and anonymous feedback.",
            "page_match": "feedback-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "chatbubbles-outline",
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
        ("horilla_tour", "0053_seed_objective_templates_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
