from uuid import uuid4

from django import forms
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra_tasks.models import HydraTask
from hydra_tasks.selectors import (
    companies_for_task_person,
    eligible_task_assignees,
)
from hydra_tasks.targets import targets_for_user


DATETIME_INPUT_FORMATS = ("%Y-%m-%dT%H:%M",)


class TaskCreateForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company._base_manager.none())
    assignee = forms.ModelChoiceField(
        queryset=HydraTask._meta.get_field("assignee").remote_field.model.objects.none()
    )
    target_reference = forms.ChoiceField(label=_("Linked record"))
    title = forms.CharField(max_length=180)
    description = forms.CharField(
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    priority = forms.ChoiceField(choices=HydraTask.Priority.choices)
    due_at = forms.DateTimeField(
        required=False,
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(
            format=DATETIME_INPUT_FORMATS[0],
            attrs={"type": "datetime-local"},
        ),
    )
    request_key = forms.UUIDField(widget=forms.HiddenInput())

    def __init__(self, *args, user, person, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.person = person
        companies = companies_for_task_person(user=user, person=person)
        self.fields["company"].queryset = companies
        self.fields["request_key"].initial = uuid4()
        company_rows = list(companies)
        if company_rows:
            self.fields["company"].initial = company_rows[0]
        assignee_ids = set()
        target_choices = []
        for company in company_rows:
            assignee_ids.update(
                eligible_task_assignees(
                    person=person,
                    company=company,
                ).values_list("pk", flat=True)
            )
            target_choices.extend(
                (
                    f"{company.pk}:{target.value}",
                    f"{company.company} / {target.label}",
                )
                for target in targets_for_user(
                    user=user,
                    person=person,
                    company=company,
                )
            )
        self.fields["assignee"].queryset = (
            self.fields["assignee"].queryset.model.objects.filter(
                pk__in=assignee_ids
            ).order_by("username")
        )
        self.fields["target_reference"].choices = target_choices

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get("company")
        reference = cleaned.get("target_reference")
        if company is None or not reference:
            return cleaned
        try:
            company_id, target_reference = reference.split(":", 1)
        except ValueError:
            self.add_error("target_reference", _("Select a valid linked record."))
            return cleaned
        if str(company.pk) != company_id:
            self.add_error(
                "target_reference",
                _("The linked record must belong to the selected Company."),
            )
            return cleaned
        cleaned["target_reference"] = target_reference
        return cleaned


class TaskUpdateForm(forms.Form):
    title = forms.CharField(max_length=180)
    description = forms.CharField(
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    priority = forms.ChoiceField(choices=HydraTask.Priority.choices)
    due_at = forms.DateTimeField(
        required=False,
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(
            format=DATETIME_INPUT_FORMATS[0],
            attrs={"type": "datetime-local"},
        ),
    )
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput())

    def __init__(self, *args, task, **kwargs):
        if not args and "initial" not in kwargs:
            kwargs["initial"] = {
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "due_at": task.due_at,
                "expected_version": task.version,
            }
        super().__init__(*args, **kwargs)


class TaskReassignForm(forms.Form):
    assignee = forms.ModelChoiceField(
        queryset=HydraTask._meta.get_field("assignee").remote_field.model.objects.none()
    )
    reason = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 3}))
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput())

    def __init__(self, *args, task, **kwargs):
        if not args and "initial" not in kwargs:
            kwargs["initial"] = {"expected_version": task.version}
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = eligible_task_assignees(
            person=task.person,
            company=task.company,
        ).exclude(pk=task.assignee_id)


class TaskTransitionForm(forms.Form):
    to_status = forms.ChoiceField(label=_("New status"))
    reason = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Completion, cancellation and reopening require a reason."),
    )
    expected_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput())

    def __init__(self, *args, task, allowed_statuses, **kwargs):
        if not args and "initial" not in kwargs:
            kwargs["initial"] = {"expected_version": task.version}
        super().__init__(*args, **kwargs)
        labels = dict(HydraTask.Status.choices)
        self.fields["to_status"].choices = [
            (value, labels[value]) for value in allowed_statuses
        ]
