from django.db import migrations

# Steps that describe Export / Import / Actions-menu features but currently have no
# element_selector.  All of them are triggered from the Actions dropdown button in
# horilla_nav.html — a <button class="... border-primary-500 ..."> that sits outside
# #filterForm (unlike the filter trigger which is a <span>).
ACTIONS_STEPS = [
    ("assigned-leaves-tour", "Import & Export"),
    ("attendance-activity-tour", "Import Activity Data"),
    ("attendance-activity-tour", "Export Activity Data"),
    ("attendances-tour", "Import Attendance"),
    ("candidate-view-tour", "Actions Menu"),
    ("contracts-tour", "Export"),
    ("hour-account-tour", "Export"),
    ("late-come-early-out-tour", "Export"),
    ("leave-requests-tour", "Export"),
    ("payslip-tour", "Generate Bulk Payslips"),
    ("payslip-tour", "Send for Review & Confirm"),
    ("payslip-tour", "Send via Mail & Export"),
]

ACTIONS_SELECTOR = "button.border-primary-500"


def fix(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    for slug, title in ACTIONS_STEPS:
        try:
            tour = Tour.objects.get(slug=slug)
        except Tour.DoesNotExist:
            continue
        TourStep.objects.filter(
            tour=tour,
            title=title,
            element_selector="",
        ).update(
            element_selector=ACTIONS_SELECTOR,
            side="bottom",
            align="start",
        )


def revert(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    for slug, title in ACTIONS_STEPS:
        try:
            tour = Tour.objects.get(slug=slug)
        except Tour.DoesNotExist:
            continue
        TourStep.objects.filter(
            tour=tour,
            title=title,
            element_selector=ACTIONS_SELECTOR,
        ).update(
            element_selector="",
            side="over",
            align="start",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0048_fix_filter_search_selectors"),
    ]

    operations = [
        migrations.RunPython(fix, revert),
    ]
