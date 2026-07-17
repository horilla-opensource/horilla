from django import forms
from django.utils.translation import gettext_lazy as _

from base.models import Company
from hydra_coordination.selectors import company_ids_for_user
from hydra_documents.models import (
    SUPPORTED_PRIVATE_CONTENT_TYPES,
    PrivateDocument,
    PrivateDocumentType,
)


CONTENT_TYPE_CHOICES = (
    ("application/pdf", _("PDF")),
    ("image/jpeg", _("JPEG image")),
    ("image/png", _("PNG image")),
)


class PrivateDocumentUploadForm(forms.Form):
    document_type = forms.ModelChoiceField(
        queryset=PrivateDocumentType.objects.none(),
        to_field_name="uuid",
        label=_("Logical document type"),
    )
    title = forms.CharField(
        max_length=160,
        required=False,
        label=_("Display title"),
        help_text=_("Optional; the logical type name is used when empty."),
    )
    issued_on = forms.DateField(
        required=False,
        label=_("Issue date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    expires_on = forms.DateField(
        required=False,
        label=_("Expiry date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    replaces = forms.ModelChoiceField(
        queryset=PrivateDocument.objects.none(),
        to_field_name="uuid",
        required=False,
        label=_("Current version to replace"),
        help_text=_("Required when the selected single-current type already exists."),
    )
    replacement_reason = forms.CharField(
        max_length=255,
        required=False,
        label=_("Replacement reason"),
    )
    file = forms.FileField(
        label=_("File"),
        help_text=_("Verified PDF, JPEG or PNG; the selected type may be stricter."),
    )

    def __init__(self, *args, document_types=None, replacement_documents=None, **kwargs):
        super().__init__(*args, **kwargs)
        if document_types is not None:
            self.fields["document_type"].queryset = document_types
        if replacement_documents is not None:
            self.fields["replaces"].queryset = replacement_documents
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )

    def clean(self):
        cleaned = super().clean()
        document_type = cleaned.get("document_type")
        predecessor = cleaned.get("replaces")
        reason = " ".join((cleaned.get("replacement_reason") or "").split())
        cleaned["replacement_reason"] = reason
        if predecessor:
            if len(reason) < 10:
                self.add_error(
                    "replacement_reason",
                    _("Provide a replacement reason of at least 10 characters."),
                )
            if document_type and predecessor.document_type_id != document_type.pk:
                self.add_error(
                    "replaces", _("The replaced version must use the selected type.")
                )
        elif reason:
            self.add_error(
                "replacement_reason", _("Choose a current version to replace.")
            )
        if (
            document_type
            and document_type.requires_expiry_date
            and not cleaned.get("expires_on")
        ):
            self.add_error(
                "expires_on", _("Expiry date is required for this document type.")
            )
        issued_on = cleaned.get("issued_on")
        expires_on = cleaned.get("expires_on")
        if issued_on and expires_on and issued_on > expires_on:
            self.add_error(
                "expires_on", _("Expiry date cannot be earlier than issue date.")
            )
        return cleaned


class PrivateDocumentTypeForm(forms.ModelForm):
    allowed_content_types = forms.MultipleChoiceField(
        choices=CONTENT_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label=_("Allowed file formats"),
    )
    max_size_mb = forms.IntegerField(
        min_value=1,
        label=_("Maximum size (MB)"),
    )

    class Meta:
        model = PrivateDocumentType
        fields = (
            "company",
            "code",
            "name",
            "category",
            "allowed_content_types",
            "max_size_mb",
            "retention_days",
            "requires_expiry_date",
            "single_current",
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
            self.initial["allowed_content_types"] = list(
                self.instance.allowed_content_types
            )
            self.initial["max_size_mb"] = max(
                1, self.instance.max_size_bytes // (1024 * 1024)
            )
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            field.widget.attrs["class"] = (
                "oh-select oh-select-2 w-100"
                if isinstance(field.widget, forms.Select)
                else "oh-input w-100"
            )

    def clean_allowed_content_types(self):
        values = self.cleaned_data["allowed_content_types"]
        if any(value not in SUPPORTED_PRIVATE_CONTENT_TYPES for value in values):
            raise forms.ValidationError(_("Unsupported file format rule."))
        return sorted(set(values))

    def save(self, commit=True):
        self.instance.max_size_bytes = self.cleaned_data["max_size_mb"] * 1024 * 1024
        return super().save(commit=commit)


class DocumentLegalHoldForm(forms.Form):
    action = forms.ChoiceField(choices=(("apply", "apply"), ("release", "release")))
    reason = forms.CharField(max_length=255)


class DocumentDeletionForm(forms.Form):
    reason = forms.CharField(max_length=255)
