from django.db import migrations


SLUG = "recruitment-survey"

STEPS = [
    {
        "sequence": 1,
        "title": "Survey Templates",
        "description": "The Survey Templates page lets you build reusable question banks and template groups that are sent to candidates during recruitment. Organise your questions into named templates — for example, Technical Screen or Culture Fit — and assign them to any recruitment pipeline.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Tabs Overview",
        "description": "The page is split into two tabs: Templates groups your questions under named headings, and Questions holds the individual reusable questions that make up those templates.",
        "element_selector": "#surveyTabsWrapper",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Templates Tab",
        "description": "The Templates tab lists all your named template groups. Each group accordion shows which questions belong to it and how many. Click a group to expand it and see its questions.",
        "element_selector": ".oh-tabs__tab:first-child",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Create Template Group",
        "description": "Click the + button in the Templates tab to create a new template group. Give it a title — this becomes the group name that you'll assign to a recruitment pipeline.",
        "element_selector": ".oh-tabs__tab:first-child button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Template Group",
        "description": "Each accordion row is one template group. It shows the group name and the count of questions attached to it. Expand it to review the individual questions inside.",
        "element_selector": ".oh-accordion-meta",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Template Actions",
        "description": "Click the ellipsis (⋮) button on any template group to access its actions — Preview the full survey as a candidate would see it, Add Questions from your question bank, Edit the group name, or Delete the group entirely.",
        "element_selector": ".oh-accordion-meta__btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Questions Tab",
        "description": "The Questions tab is your reusable question bank. Each card is one question — text, multiple choice, rating or file upload — that can be added to any template group.",
        "element_selector": ".oh-tabs__tab:last-child",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Create Question",
        "description": "Click the + button in the Questions tab to create a new individual question. Set the question text, choose the answer type and optionally mark it as required. Once saved it appears in the bank ready to be added to templates.",
        "element_selector": ".oh-tabs__tab:last-child button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Search",
        "description": "Use the search box to filter questions by name. The list updates as you type — handy when your question bank grows large and you need to locate a specific question quickly.",
        "element_selector": "input[name='question']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 10,
        "title": "Filter",
        "description": "Click Filter to narrow the question list by answer type or recruitment. Use this to review all questions of a particular type or to see which questions are linked to a specific recruitment pipeline.",
        "element_selector": "button.oh-btn.ml-2",
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
            "title": "Recruitment Survey",
            "description": "A guided tour of survey templates, question banks and how surveys are linked to recruitments.",
            "page_match": "recruitment-survey-question-template-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "document-text-outline",
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
        ("horilla_tour", "0009_seed_recruitment_dashboard_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
