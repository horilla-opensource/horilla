from django.db import migrations


SLUG = "multiple-approval-condition-form-tour"

STEPS = [
    {
        "sequence": 1,
        "title": "Multiple Approval Condition Form",
        "description": "This form lets you define a rule that routes specific requests through multiple approvers in sequence. Fill in the condition criteria to specify which requests are affected, then choose the managers who must approve them in order.",
        "element_selector": "",
        "side": "over",
        "align": "start",
    },
    {
        "sequence": 2,
        "title": "Department",
        "description": "Select the department this approval condition applies to. Leave it blank to apply the condition across all departments. When a department is selected, only requests from employees in that department will be routed through this approval chain.",
        "element_selector": "label[for='id_department']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 3,
        "title": "Condition Field",
        "description": "Choose the employee attribute to evaluate — for example, Job Position, Work Type or Employee Type. The condition will check this field on the requesting employee to decide whether the multi-level approval chain applies.",
        "element_selector": "label[for='id_condition_field']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 4,
        "title": "Condition Operator & Value",
        "description": "Set the operator (equals, contains, etc.) and the value to match against the Condition Field. For example, Condition Field = Job Position, Operator = equals, Value = Manager. Requests from employees matching this rule will be routed through the approval chain.",
        "element_selector": "#conditionValueDiv",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 5,
        "title": "Company",
        "description": "Optionally restrict this condition to a specific company. In multi-company setups, this ensures the approval chain only applies to employees in the selected company. Leave blank to apply the condition company-wide.",
        "element_selector": "label[for='id_company_id']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 6,
        "title": "Approval Managers",
        "description": "Select the first-level approver for this condition. This manager will receive the approval request first. Once they approve, the request moves to the next level if one is configured.",
        "element_selector": "label[for='id_multi_approval_manager']",
        "side": "bottom",
        "align": "start",
    },
    {
        "sequence": 7,
        "title": "Add More Managers",
        "description": "Click 'Add more managers' to add additional approval levels. Each level adds another manager who must approve the request in sequence — the request only completes when every level has approved it. Use this to build a full multi-level hierarchy.",
        "element_selector": "a[hx-get*='add-more-approval-managers']",
        "side": "top",
        "align": "start",
    },
    {
        "sequence": 8,
        "title": "Apply",
        "description": "Click Apply to save the condition. From this point on, any request that matches the criteria you defined will be automatically routed through the configured approval chain — in the order the managers were added.",
        "element_selector": "button[type='submit'].oh-btn--secondary",
        "side": "top",
        "align": "start",
    },
]


def seed(apps, schema_editor):
    Tour = apps.get_model("horilla_tour", "Tour")
    TourStep = apps.get_model("horilla_tour", "TourStep")

    tour, created = Tour.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Approval Condition Form",
            "description": "A guided tour of the Multiple Approval Condition form — setting criteria, choosing approvers and building a multi-level approval chain.",
            "page_match": "multiple-approval-condition",
            "match_type": "url_name",
            "audience": "managers",
            "trigger": "manual",
            "priority": 40,
            "icon": "git-merge-outline",
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
        ("horilla_tour", "0077_seed_multiple_approval_condition_tour"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
