from django.db import migrations


SLUG = "employee-profile-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Your Employee Profile",
        "description": "This is your personal employee profile — a single place where you can view and manage all your work information, leave balances, attendance records, documents and more.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Profile Photo & Basic Info",
        "description": "Your profile photo, name, email, phone and gender are shown at the top. This information is pulled from your employee record and is visible to your manager and HR.",
        "element_selector": ".avatar-thumb",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Profile Tabs",
        "description": "Use the tabs to navigate between different sections of your profile — About, Work Type & Shift, Attendance, Leave, Payroll, Documents, Performance and more.",
        "element_selector": ".usertablist",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "About Tab",
        "description": "The About tab shows your personal details, work information, emergency contacts and bank account details. Click any field to edit it inline if you have permission.",
        "element_selector": ".usertablist li:first-child button",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Actions Menu",
        "description": "Click the gear icon to access profile actions — reset your password, block or unblock account access, and other admin actions depending on your permissions.",
        "element_selector": "button[title='Actions']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Leave & Attendance",
        "description": "Switch to the Leave tab to see your leave balances, request history and approvals. The Attendance tab shows your check-in/out records and any late or early-out flags.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Documents & Payroll",
        "description": "The Documents tab holds your uploaded files and HR-shared documents. The Payroll tab shows your payslips, allowances, deductions and bonus points — all in one place.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Employee Profile",
            "description": "A guided tour of your employee profile — photo, tabs, leave, attendance, documents and payroll.",
            "page_match": "employee-profile",
            "match_type": "url_name",
            "audience": "all",
            "trigger": "auto_once",
            "priority": 50,
            "icon": "person-circle-outline",
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
        ("horilla_tour", "0019_reseed_onboarding_hired_candidates_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
