from django.db import migrations


SLUG = "holidays-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Holidays",
        "description": "The Holidays page lets you manage the company's official holiday calendar. Define one-off or recurring holidays with start and end dates, and the system will automatically block leave deductions and attendance expectations on those days for all employees.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Holidays List",
        "description": "The table lists all configured holidays with their name, start date, end date and whether they recur annually. Click any column header to sort the list. Use the checkboxes to select individual holidays or select all for bulk actions.",
        "element_selector": "#listContainer",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Create Holiday",
        "description": "Click Create to add a new holiday. Enter the holiday name, set the start and end dates, choose whether it recurs every year, and optionally restrict it to specific companies. Once saved, the holiday appears in all employee leave and attendance calculations.",
        "element_selector": "a.bg-primary-600[data-toggle='oh-modal-toggle']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Holiday Detail",
        "description": "Click any holiday row to open its detail view. The detail panel shows the full record — name, start and end dates, recurring status and company. Use the Edit button inside the panel to update the holiday or the Delete button to remove it.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Actions",
        "description": "The Actions menu provides bulk operations — Import to upload a spreadsheet of holidays, Export to download the list, and Delete to remove all selected holidays at once. Tick the checkboxes in the list first before using a bulk action.",
        "element_selector": "button.border-primary-500",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Search",
        "description": "Type in the search box to instantly filter holidays by name. The list updates as you type — useful when you have a large number of holidays configured across multiple companies or regions.",
        "element_selector": "input[name='search']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Filter",
        "description": "Click Filter to narrow the list by holiday name, date range, company or whether the holiday is recurring. Apply multiple criteria together to focus on a specific subset — for example, all recurring holidays for a particular company.",
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
            "title": "Holidays",
            "description": "A guided tour of the Holidays page — creating and managing the company holiday calendar, importing or exporting holiday data, and using search and filter to find specific holidays.",
            "page_match": "holiday-view",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "calendar-outline",
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
        ("horilla_tour", "0080_seed_automations_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
