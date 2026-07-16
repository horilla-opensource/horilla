"""
Fix: the Create button in horilla_nav.html is an <a> tag, but two
<button> elements with class oh-btn--secondary appear earlier in the DOM
(the Filter / Apply-Filter buttons).  Driver.js matched the hidden
filter button first.

Fix: change the selector from  .oh-btn--secondary
                         to    a.oh-btn--secondary
which targets only the Create anchor and skips the filter <button>s.
"""
from django.db import migrations


SLUGS = [
    "settings-company",
    "settings-department",
    "settings-job-position",
    "settings-job-role",
    "settings-work-type",
    "settings-employee-type",
    "settings-employee-shift",
]


def fix(apps, schema_editor):
    TourStep = apps.get_model("horilla_tour", "TourStep")
    Tour = apps.get_model("horilla_tour", "Tour")
    for slug in SLUGS:
        try:
            tour = Tour.objects.get(slug=slug)
        except Tour.DoesNotExist:
            continue
        TourStep.objects.filter(
            tour=tour, element_selector=".oh-btn--secondary"
        ).update(element_selector="a.oh-btn--secondary")


def revert(apps, schema_editor):
    TourStep = apps.get_model("horilla_tour", "TourStep")
    Tour = apps.get_model("horilla_tour", "Tour")
    for slug in SLUGS:
        try:
            tour = Tour.objects.get(slug=slug)
        except Tour.DoesNotExist:
            continue
        TourStep.objects.filter(
            tour=tour, element_selector="a.oh-btn--secondary"
        ).update(element_selector=".oh-btn--secondary")


class Migration(migrations.Migration):

    dependencies = [
        ("horilla_tour", "0007_settings_tours_interactive"),
    ]

    operations = [
        migrations.RunPython(fix, revert),
    ]
