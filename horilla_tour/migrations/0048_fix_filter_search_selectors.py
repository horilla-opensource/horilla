from django.db import migrations
from django.db.models import F

GENERIC_FILTER_TITLES = {
    "Filter & Search",
    "Search & Filter",
    "Filter & Group By",
    "Filter, Group By & Export",
}


def fix(apps, schema_editor):
    TourStep = apps.get_model("horilla_tour", "TourStep")

    steps = list(
        TourStep.objects.filter(
            title__in=GENERIC_FILTER_TITLES,
            element_selector="",
        ).order_by("tour_id", "sequence")
    )

    for step in steps:
        original_seq = step.sequence

        # Shift any steps beyond current sequence up by 1 to make room
        TourStep.objects.filter(
            tour_id=step.tour_id,
            sequence__gt=original_seq,
        ).update(sequence=F("sequence") + 1)

        # Update existing step → "Search", pointing to the search input
        step.title = "Search"
        step.description = (
            "Use the search bar to quickly find records by employee name or keyword. "
            "The list updates as you type."
        )
        step.element_selector = "input[name='search']"
        step.side = "bottom"
        step.align = "start"
        step.save()

        # Insert new "Filter" step right after
        TourStep.objects.create(
            tour_id=step.tour_id,
            sequence=original_seq + 1,
            title="Filter",
            description=(
                "Click the Filter button to open the filter panel. "
                "Use the available fields to narrow results by date range, department, "
                "status or other criteria, then click Apply to update the list."
            ),
            element_selector="#filterForm .dropdown-wrapper",
            side="bottom",
            align="start",
        )


def revert(apps, schema_editor):
    TourStep = apps.get_model("horilla_tour", "TourStep")

    filter_steps = list(
        TourStep.objects.filter(
            title="Filter",
            element_selector="#filterForm .dropdown-wrapper",
        ).order_by("tour_id", "-sequence")
    )

    for fstep in filter_steps:
        seq = fstep.sequence
        tour_id = fstep.tour_id
        fstep.delete()

        TourStep.objects.filter(
            tour_id=tour_id,
            sequence__gt=seq,
        ).update(sequence=F("sequence") - 1)

    TourStep.objects.filter(
        title="Search",
        element_selector="input[name='search']",
    ).update(
        title="Filter & Search",
        description=(
            "Use the search bar to find records by name. "
            "Use the Filter button to narrow results by date range, "
            "department, status or other criteria."
        ),
        element_selector="",
        side="over",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0047_seed_reimbursements_tour"),
    ]

    operations = [
        migrations.RunPython(fix, revert),
    ]
