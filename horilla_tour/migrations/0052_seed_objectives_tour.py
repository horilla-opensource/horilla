from django.db import migrations


SLUG = "objectives-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Objectives",
        "description": "The Objectives page is where your organisation's OKRs (Objectives and Key Results) are managed. Each objective sets a high-level goal, and Key Results define measurable outcomes that track progress toward it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Assigned Objectives Tab",
        "description": "The Assigned Objectives tab shows all objectives you have been assigned to as an employee or assignee. Use this tab to track your own goals and update the progress of your Key Results.",
        "element_selector": "#objContainer .oh-tabs__tab[data-tab-index='0']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "All Objectives Tab",
        "description": "The All Objectives tab lists every objective in the organisation — including those you manage. Managers and admins use this tab to create new objectives, review team progress and manage assignees.",
        "element_selector": "#objContainer .oh-tabs__tab[data-tab-index='1']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Objectives List",
        "description": "Each row shows one objective — its title, assigned managers, the number of Key Results, the list of assignees, the duration and a short description. Click any row to expand it and view the Key Results underneath.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Progress Bar",
        "description": "The progress bar on each objective row shows the overall completion percentage, calculated automatically from the progress of all linked Key Results. As employees update their Key Result values, the bar updates in real time.",
        "element_selector": ".oh-progress-container.progress_bar_objective",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Create Objective",
        "description": "Click Create to define a new objective. Set the title, add a description, assign managers and employees, set the start and end dates, and add Key Results that will measure success.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Add Key Results",
        "description": "Click the + button on any objective row to add a Key Result to it. Each Key Result has a title, a target value, a unit of measurement (number, percentage, currency) and start and end dates. Progress is updated by entering the current value.",
        "element_selector": "button.oh-btn--secondary-outline[data-toggle='oh-modal-toggle']",
        "side": "left",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Row Actions",
        "description": "Each objective row has action buttons — View (eye icon) to open the full detail, Activity (newspaper icon) to see the change log, and the three-dot menu to Edit, Archive or Delete the objective.",
        "element_selector": ".oh-btn-group .oh-dropdown > button.oh-btn--transparent",
        "side": "left",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Search",
        "description": "Use the search bar to quickly find objectives by title. The list updates as you type.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 10,
        "title": "Filter",
        "description": "Click Filter to narrow objectives by assignee, key result, date range, status or progress percentage. A second section lets you filter by Key Result dates and due status.",
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
            "title": "Objectives",
            "description": "A guided tour of the Objectives page — creating objectives, adding Key Results, tracking progress and managing OKRs across your organisation.",
            "page_match": "objective-list-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "flag-outline",
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
        ("horilla_tour", "0049_fix_actions_button_selectors"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
