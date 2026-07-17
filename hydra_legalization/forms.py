from datetime import timedelta
from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra_coordination.selectors import company_ids_for_user
from hydra_documents.models import PrivateDocument
from hydra_documents.selectors import document_types_for_user
from hydra_legalization.models import (
    LegalizationAuthority,
    LegalizationAuthorityEvent,
    LegalizationCase,
    LegalizationCaseDelegation,
    LegalizationCaseDocument,
    LegalizationProcedureRequirement,
    LegalizationProcedureType,
)
from hydra_legalization.selectors import (
    authorities_for_case_snapshot,
    available_private_documents_for_case,
    eligible_renewal_predecessors,
    legalization_authorities_for_user,
    legalization_companies_for_person,
    legalization_procedures_for_user,
    visible_private_documents_for_case,
)
from hydra_legalization.services import available_authority_events, available_transitions
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
            "company",
            "procedure_type",
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
        self.fields["company"].queryset = legalization_companies_for_person(
            user=actor, person=person
        )
        self.fields["procedure_type"].queryset = legalization_procedures_for_user(
            user=actor
        )
        users = User.objects.filter(is_active=True)
        users = _users_with_permission(
            users, "hydra_legalization", "view_legalizationcase"
        )
        users = _users_with_permission(users, "hydra_people", "view_person").distinct()
        if self.instance.pk:
            self.fields.pop("responsible")
            self.fields["company"].disabled = True
            self.fields["procedure_type"].disabled = True
        else:
            if not actor.has_perm("hydra_legalization.assign_legalizationcase"):
                users = users.filter(pk=actor.pk)
                self.fields["responsible"].disabled = True
            self.fields["responsible"].queryset = users.order_by("username")
            self.fields["responsible"].initial = actor
        if self.instance.pk and self.instance.status not in {
            LegalizationCase.Status.DRAFT,
            LegalizationCase.Status.COLLECTING_DOCUMENTS,
        }:
            for field_name in (
                "company",
                "procedure_type",
                "reference_number",
                "deadline",
                "valid_from",
                "valid_until",
            ):
                self.fields[field_name].disabled = True
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean_responsible(self):
        if "responsible" not in self.cleaned_data:
            return self.instance.responsible
        responsible = self.cleaned_data["responsible"]
        if not people_for_user(user=responsible).filter(pk=self.person.pk).exists():
            raise forms.ValidationError(
                _("The responsible user cannot access this person.")
            )
        company = self.cleaned_data.get("company")
        if company and not legalization_companies_for_person(
            user=responsible, person=self.person
        ).filter(pk=company.pk).exists():
            raise forms.ValidationError(
                _("The responsible user cannot access the selected company.")
            )
        return responsible

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get("company")
        procedure = cleaned.get("procedure_type")
        if company and procedure and procedure.company_id not in (None, company.pk):
            self.add_error(
                "procedure_type", _("The procedure is outside the selected company.")
            )
        if company and procedure and not self.instance.pk:
            # ModelForm runs model validation before the locked service boundary.
            # Populate a validation-only snapshot; the service replaces it under locks.
            self.instance.case_type = procedure.case_type
            self.instance.procedure_snapshot = procedure.rules_snapshot(
                company_id=company.pk
            )
        return cleaned


class LegalizationAuthorityForm(forms.ModelForm):
    allowed_channels = forms.MultipleChoiceField(
        choices=LegalizationAuthorityEvent.Channel.choices,
        widget=forms.CheckboxSelectMultiple,
        label=_("Allowed channels"),
    )

    class Meta:
        model = LegalizationAuthority
        fields = (
            "company",
            "code",
            "name",
            "jurisdiction",
            "allowed_channels",
            "is_active",
        )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if user.is_superuser:
            self.fields["company"].queryset = Company._base_manager.order_by("company")
            self.fields["company"].required = False
        else:
            self.fields["company"].queryset = Company._base_manager.filter(
                pk__in=company_ids_for_user(user=user)
            ).order_by("company")
            self.fields["company"].required = True
        if self.instance.pk:
            self.initial["allowed_channels"] = list(self.instance.allowed_channels)
            self.fields["company"].disabled = True
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )


class LegalizationProcedureForm(forms.ModelForm):
    enabled_statuses = forms.MultipleChoiceField(
        choices=LegalizationCase.Status.choices,
        widget=forms.CheckboxSelectMultiple,
        label=_("Enabled statuses"),
    )

    class Meta:
        model = LegalizationProcedureType
        fields = (
            "company",
            "code",
            "name",
            "case_type",
            "description",
            "default_deadline_days",
            "renewal_lead_days",
            "requires_authority",
            "authorities",
            "enabled_statuses",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "authorities": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if user.is_superuser:
            self.fields["company"].queryset = Company._base_manager.order_by("company")
            self.fields["company"].required = False
        else:
            self.fields["company"].queryset = Company._base_manager.filter(
                pk__in=company_ids_for_user(user=user)
            ).order_by("company")
            self.fields["company"].required = True
        self.fields["authorities"].queryset = legalization_authorities_for_user(
            user=user
        )
        if self.instance.pk:
            self.fields["company"].disabled = True
            self.initial["enabled_statuses"] = list(
                self.instance.status_rules.filter(is_active=True).values_list(
                    "status", flat=True
                )
            )
        else:
            self.initial["enabled_statuses"] = list(LegalizationCase.Status.values)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )


class LegalizationRequirementForm(forms.ModelForm):
    class Meta:
        model = LegalizationProcedureRequirement
        fields = (
            "procedure",
            "code",
            "name",
            "document_type",
            "required_before_status",
            "sort_order",
            "is_active",
        )

    def __init__(self, *args, user, procedure=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["procedure"].queryset = legalization_procedures_for_user(
            user=user, include_inactive=True
        )
        self.fields["document_type"].queryset = document_types_for_user(
            user=user, include_inactive=True
        )
        if procedure is not None:
            self.fields["procedure"].initial = procedure
            self.fields["procedure"].disabled = True
        if self.instance.pk:
            self.fields["procedure"].disabled = True
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )


def _operational_legalization_users():
    users = User.objects.filter(is_active=True)
    permissions = (
        ("hydra_legalization", "view_legalizationcase"),
        ("hydra_legalization", "change_legalizationcase"),
        ("hydra_legalization", "transition_legalizationcase"),
        ("hydra_legalization", "link_privatedocument"),
        ("hydra_legalization", "view_legalizationauthorityevent"),
        ("hydra_legalization", "record_legalizationauthorityevent"),
        ("hydra_legalization", "view_legalizationproceduretype"),
        ("hydra_legalization", "view_legalizationauthority"),
        ("hydra_legalization", "view_legalizationrenewallink"),
        ("hydra_legalization", "create_legalizationrenewallink"),
        ("hydra_legalization", "add_legalizationcase"),
        ("hydra_legalization", "view_legalizationcasedelegation"),
        ("hydra_legalization", "view_legalizationworkevent"),
        ("hydra_people", "view_person"),
        ("hydra_documents", "view_privatedocument"),
        ("recruitment", "view_candidate"),
    )
    for app_label, codename in permissions:
        users = _users_with_permission(users, app_label, codename)
    return users.distinct().order_by("username")


class LegalizationReassignmentForm(forms.Form):
    new_responsible = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=_("New responsible user"),
    )
    reason = forms.CharField(
        label=_("Transfer reason"),
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, case, **kwargs):
        super().__init__(*args, **kwargs)
        users = User.objects.filter(is_active=True)
        users = _users_with_permission(
            users, "hydra_legalization", "view_legalizationcase"
        )
        users = _users_with_permission(users, "hydra_people", "view_person")
        self.fields["new_responsible"].queryset = users.exclude(
            pk=case.responsible_id
        ).distinct().order_by("username")
        self.fields["new_responsible"].widget.attrs["class"] = (
            "oh-select oh-select-2 w-100"
        )
        self.fields["reason"].widget.attrs["class"] = "oh-input w-100"

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError(_("A transfer reason is required."))
        return reason


class LegalizationDelegationForm(forms.Form):
    deputy = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=_("Deputy"),
    )
    valid_from = forms.DateField(
        label=_("Valid from"),
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    valid_until = forms.DateField(
        label=_("Valid until"),
        initial=lambda: timezone.localdate() + timedelta(days=13),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    reason = forms.CharField(
        label=_("Delegation reason"),
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, case, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deputy"].queryset = _operational_legalization_users().exclude(
            pk=case.responsible_id
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )

    def clean(self):
        cleaned = super().clean()
        valid_from = cleaned.get("valid_from")
        valid_until = cleaned.get("valid_until")
        if valid_from and valid_from < timezone.localdate():
            self.add_error("valid_from", _("A delegation cannot start in the past."))
        if valid_from and valid_until:
            if valid_until < valid_from:
                self.add_error(
                    "valid_until", _("The end date cannot precede the start date.")
                )
            elif (
                valid_until - valid_from
            ).days >= LegalizationCaseDelegation.MAX_DURATION_DAYS:
                self.add_error(
                    "valid_until", _("A delegation cannot exceed 90 calendar days.")
                )
        return cleaned

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError(_("A delegation reason is required."))
        return reason


class LegalizationDelegationRevokeForm(forms.Form):
    reason = forms.CharField(
        label=_("Revocation reason"),
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2, "class": "oh-input w-100"}),
    )

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError(_("A revocation reason is required."))
        return reason


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


class LegalizationAuthorityEventForm(forms.Form):
    event_type = forms.ChoiceField(label=_("Authority event"))
    occurred_on = forms.DateField(
        label=_("Event date"),
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    authority_config = forms.ModelChoiceField(
        queryset=LegalizationAuthority.objects.none(),
        to_field_name="uuid",
        label=_("Authority"),
    )
    channel = forms.ChoiceField(
        label=_("Channel"), choices=LegalizationAuthorityEvent.Channel.choices
    )
    reference_number = forms.CharField(
        label=_("Reference number"), required=False, max_length=100
    )
    response_deadline = forms.DateField(
        label=_("Response deadline"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    valid_from = forms.DateField(
        label=_("Valid from"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    valid_until = forms.DateField(
        label=_("Valid until"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    evidence_document = forms.ModelChoiceField(
        queryset=PrivateDocument.objects.none(),
        label=_("Evidence document"),
    )
    details = forms.CharField(
        label=_("Details"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)

    def __init__(self, *args, actor, case, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_type"].choices = available_authority_events(case)
        self.fields["authority_config"].queryset = authorities_for_case_snapshot(
            user=actor, case=case
        )
        self.fields["evidence_document"].queryset = visible_private_documents_for_case(
            user=actor,
            case=case,
        )
        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean(self):
        cleaned = super().clean()
        event_type = cleaned.get("event_type")
        authority = cleaned.get("authority_config")
        channel = cleaned.get("channel")
        if authority and channel not in authority.allowed_channels:
            self.add_error(
                "channel", _("This channel is not allowed for the selected authority.")
            )
        if event_type == LegalizationAuthorityEvent.EventType.INFORMATION_REQUESTED:
            if not cleaned.get("response_deadline"):
                self.add_error(
                    "response_deadline",
                    _("An information request requires a response deadline."),
                )
        elif cleaned.get("response_deadline"):
            self.add_error(
                "response_deadline",
                _("A response deadline is only valid for an information request."),
            )
        if event_type == LegalizationAuthorityEvent.EventType.APPROVED:
            if not cleaned.get("valid_from") or not cleaned.get("valid_until"):
                self.add_error(
                    "valid_until", _("An approval requires a complete validity period.")
                )
        elif cleaned.get("valid_from") or cleaned.get("valid_until"):
            self.add_error(
                "valid_until", _("Validity dates are only valid for an approval.")
            )
        if (
            event_type == LegalizationAuthorityEvent.EventType.REFERENCE_ASSIGNED
            and not cleaned.get("reference_number")
        ):
            self.add_error(
                "reference_number",
                _("A reference assignment requires a reference number."),
            )
        if (
            event_type == LegalizationAuthorityEvent.EventType.REJECTED
            and not cleaned.get("details", "").strip()
        ):
            self.add_error("details", _("A rejection requires details."))
        return cleaned


class LegalizationRenewalStartForm(forms.Form):
    deadline = forms.DateField(
        label=_("Preparation deadline"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input w-100"}),
    )
    notes = forms.CharField(
        label=_("Renewal notes"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "class": "oh-input w-100"}),
    )

    def clean_deadline(self):
        deadline = self.cleaned_data.get("deadline")
        if deadline and deadline < timezone.localdate():
            raise forms.ValidationError(_("A new renewal deadline cannot be in the past."))
        return deadline


class RenewalPredecessorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        reference = obj.reference_number or str(obj.uuid)
        validity = obj.valid_until.isoformat() if obj.valid_until else "—"
        return f"{reference} · {obj.get_status_display()} · {validity}"


class LegalizationRenewalLinkForm(forms.Form):
    predecessor = RenewalPredecessorChoiceField(
        queryset=LegalizationCase.objects.none(),
        label=_("Previous case"),
    )
    reason = forms.CharField(
        label=_("Historical link reason"),
        max_length=255,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, actor, successor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["predecessor"].queryset = eligible_renewal_predecessors(
            user=actor,
            successor=successor,
        )
        self.fields["predecessor"].widget.attrs["class"] = "oh-select oh-select-2 w-100"
        self.fields["reason"].widget.attrs["class"] = "oh-input w-100"

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError(_("A manual historical link requires a reason."))
        return reason
