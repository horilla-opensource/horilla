from django.db import migrations


SLUG = "question-template-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Question Template",
        "description": "Question Templates are reusable sets of review questions used in Feedback and Meeting cycles. Instead of typing questions from scratch each time, you define a template once and attach it to any feedback cycle or meeting — keeping your review process consistent across the organisation.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Templates List",
        "description": "Each row shows a question template — its title and the total number of questions it contains. Click any row to open the template detail page where you can view, add or edit individual questions.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Template",
        "description": "Click Create to define a new question template. Give it a descriptive title and save. You can then open the template to add questions — each question can be a text response, a rating, a yes/no or a multiple-choice answer type.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Adding Questions",
        "description": "Click any template row to open its detail page. From there you can add, edit or reorder questions. Each question has a type — short text, long text, rating scale, yes/no or multiple choice — and can be marked as required.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Using Templates",
        "description": "Once created, question templates can be attached to Feedback cycles or Meetings. When a reviewer opens their assigned feedback or meeting, the questions from the template appear automatically for them to answer.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Use the search bar to quickly find question templates by title. The list updates as you type.",
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
            "title": "Question Template",
            "description": "A guided tour of the Question Template page — creating reusable review question sets that can be attached to feedback cycles and meetings.",
            "page_match": "question-template-view",
            "match_type": "url_name",
            "audience": "managers",
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
        ("horilla_tour", "0058_seed_period_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
