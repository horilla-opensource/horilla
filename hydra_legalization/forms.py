from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from hydra_documents.models import PrivateDocument
from hydra_legalization.models import LegalizationCase, LegalizationCaseDocument
from hydra_legalization.selectors import available_private_documents_for_case
from hydra_legalization.services import available_transitions
from hydra_people.selectors import people_for_user


User = get_user_model()


def _users_with_permission(queryset, app_label, codename):
    return queryset.filter(
        Q(is_superuser=True)
        | Q(
            user_permissions__content_type__app_label=app_label,
            user_permissions__codename=codename,
        )
        | Q(
            groups__permissions__content_type__app_label=app_label,
            groups__permissions__codename=codename,
        )
    )


class LegalizationCaseForm(forms.ModelForm):
    class Meta:
        model = LegalizationCase
        fields = (
            "case_type",
            "responsible",
            "reference_number",
            "deadline",
            "valid_from",
            "valid_until",
            "notes",
        )
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, actor, person, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.person = person
        users = User.objects.filter(is_active=True)
        users = _users_with_permission(
            users, "hydra_legalization", "view_legalizationcase"
        )
        users = _users_with_permission(users, "hydra_people", "view_person").distinct()
        if not actor.has_perm("hydra_legalization.assign_legalizationcase"):
            allowed_ids = [actor.pk]
            if self.instance.pk:
                allowed_ids.append(self.instance.responsible_id)
            users = users.filter(pk__in=allowed_ids)
            self.fields["responsible"].disabled = True
        self.fields["responsible"].queryset = users.order_by("username")
        if not self.instance.pk:
            self.fields["responsible"].initial = actor
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean_responsible(self):
        responsible = self.cleaned_data["responsible"]
        if not people_for_user(user=responsible).filter(pk=self.person.pk).exists():
            raise forms.ValidationError(
                _("The responsible user cannot access this person.")
            )
        return responsible


class LegalizationTransitionForm(forms.Form):
    target_status = forms.ChoiceField(label=_("New status"))
    reason = forms.CharField(
        label=_("Reason"),
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2, "class": "oh-input w-100"}),
    )

    def __init__(self, *args, case, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_status"].choices = available_transitions(case)
        self.fields["target_status"].widget.attrs["class"] = "oh-select w-100"


class LegalizationDocumentForm(forms.Form):
    document = forms.ModelChoiceField(
        queryset=PrivateDocument.objects.none(), label=_("Private document")
    )
    role = forms.ChoiceField(
        choices=LegalizationCaseDocument.Role.choices, label=_("Document role")
    )

    def __init__(self, *args, actor, case, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document"].queryset = available_private_documents_for_case(
            user=actor, case=case
        )
        self.fields["document"].widget.attrs["class"] = "oh-select w-100"
        self.fields["role"].widget.attrs["class"] = "oh-select w-100"
