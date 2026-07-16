from django.db import migrations


SLUG = "document-requests-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Document Requests",
        "description": "This page manages document requests raised for employees. HR or managers can request specific documents from employees and track whether they have been uploaded, approved or rejected.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Requests Pipeline",
        "description": "Document requests are grouped by request type. Each group shows how many documents have been uploaded versus the total requested. Click a group header to expand it and see individual employee records.",
        "element_selector": "#view-container",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Request Group Header",
        "description": "Each header shows the document request name and upload progress. Click the header to expand or collapse the employee rows below it. The ellipsis (⋮) button on the right lets you Edit or Delete the request.",
        "element_selector": ".oh-tabs__movable-header",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Edit or Delete a Request",
        "description": "Click the ellipsis (⋮) on a request group to Edit its title and description, or Delete the request entirely. Deleting a request removes all associated employee document records.",
        "element_selector": ".oh-accordion-meta__btn",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Create Document Request",
        "description": "Click Create to raise a new document request. Specify the document type and add a description of what employees need to upload. The request appears as a new group in the pipeline immediately.",
        "element_selector": "a.bg-primary-600",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Bulk Approve or Reject",
        "description": "Click Actions to bulk approve or bulk reject multiple selected document uploads at once. Select employee rows using their checkboxes first, then choose Bulk Approve or Bulk Reject from the menu.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Approve & Reject Individual Uploads",
        "description": "Once an employee uploads a document, expand their request group to see the row. A green tick means approved, red alert means rejected, a file icon means uploaded but not yet reviewed. Use the approve or reject buttons on the row to action it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Search",
        "description": "Type in the search box to filter document requests by employee name. The pipeline updates as you type — useful when managing requests across a large workforce.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 9,
        "title": "Filter",
        "description": "Click Filter to narrow the requests by department, job position, document status or request type. Use this to focus on pending uploads or documents awaiting approval.",
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
            "title": "Document Requests",
            "description": "A guided tour of document requests — raising requests, tracking uploads, and approving or rejecting submitted documents.",
            "page_match": "document-request-view",
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
        ("horilla_tour", "0020_seed_employee_profile_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
