from django.db import migrations


SLUG = "exit-process-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Exit Process",
        "description": "The Exit Process page manages employee offboarding through a structured pipeline. Each pipeline you define represents a specific offboarding workflow — for example an IT department offboarding or a permanent exit — with custom stages that employees move through from their last day to clearance.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Pipeline View",
        "description": "The pipeline area shows all active offboarding workflows as tabs. Select a tab to see the stages within that pipeline and the employees currently at each stage. Use the list view for a compact table layout or switch to card view for a visual Kanban board.",
        "element_selector": "#pipelineContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Pipeline Tabs",
        "description": "Each tab at the top represents one offboarding pipeline — for example IT Offboarding or Full Exit. Click a tab to load its stages and see the employees currently moving through that pipeline.",
        "element_selector": "button.oh-tabs__tab",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Pipeline Actions",
        "description": "Each pipeline tab has an Actions menu. Use it to add a new stage to the pipeline, manage the stage order, update the pipeline settings or delete it.",
        "element_selector": ".oh-accordion-meta__btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Create Offboarding Pipeline",
        "description": "Click Create to define a new offboarding pipeline. Give it a title, set the responsible managers and configure whether it is active. Once created, you can add stages to it and start assigning employees who are going through that offboarding process.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Pipeline Stages",
        "description": "Each pipeline is divided into stages — sequential steps an employee moves through during offboarding, such as Notice Period, Documentation, Asset Return and Final Clearance. You can add, reorder and edit stages from the stage's Actions menu. Stages are displayed as columns in card view or as grouped sections in list view.",
        "element_selector": ".oh-tabs__movable-header",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Adding Employees",
        "description": "To start an employee's offboarding, click Add Employee on the relevant pipeline stage. Select the employee and set their last working day and notice period end date. The employee record then appears in that stage and moves forward as the offboarding progresses.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Employee Tasks & Notes",
        "description": "Each employee in the pipeline can be assigned tasks — specific actions they or HR must complete before moving to the next stage, such as returning equipment or signing documents. You can also add notes and send emails directly from the employee's offboarding card.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "List & Card Views",
        "description": "Use the view toggle to switch between List view (a compact table of employees grouped by stage) and Card view (a visual Kanban board with drag-and-drop stage movement). Both views show the same data — choose the layout that suits your workflow.",
        "element_selector": ".nav-view-btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 10,
        "title": "Filter",
        "description": "Click Filter to narrow the pipeline view by offboarding pipeline, stage, employee, department, job position or notice period dates. Filters are combined — you can stack multiple criteria to focus on exactly the employees you need.",
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
            "title": "Exit Process",
            "description": "A guided tour of the Exit Process page — setting up offboarding pipelines, managing stages, assigning employees and tracking tasks through to final clearance.",
            "page_match": "offboarding-pipeline",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "log-out-outline",
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
        ("horilla_tour", "0059_seed_question_template_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
