from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _

from base.models import JobPosition
from hydra_people.recruitment_selectors import recruitments_for_user
from recruitment.models import Recruitment


MAX_IMPORT_BYTES = 5 * 1024 * 1024


class CandidateImportUploadForm(forms.Form):
    recruitment = forms.ModelChoiceField(
        queryset=Recruitment.objects.none(),
        label=_("Recruitment"),
    )
    job_position = forms.ModelChoiceField(
        queryset=JobPosition.objects.none(),
        label=_("Job position"),
    )
    workbook = forms.FileField(
        label=_("Candidate workbook"),
        help_text=_("Upload an .xlsx file up to 5 MB. Formulas are not accepted."),
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        allowed_recruitments = recruitments_for_user(
            user=actor,
            permission="view_recruitment",
        ).filter(closed=False, is_active=True)
        self.fields["recruitment"].queryset = allowed_recruitments.order_by(
            "title", "pk"
        )
        self.fields["job_position"].queryset = (
            JobPosition._base_manager.filter(open_positions__in=allowed_recruitments)
            .distinct()
            .order_by("job_position", "pk")
        )
        recruitment_id = self.data.get("recruitment")
        try:
            recruitment = allowed_recruitments.get(pk=recruitment_id)
        except (Recruitment.DoesNotExist, TypeError, ValueError):
            recruitment = None
        if recruitment:
            self.fields["job_position"].queryset = recruitment.open_positions.order_by(
                "job_position", "pk"
            )

        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                css_class = "oh-select oh-select-2 w-100"
            else:
                css_class = "oh-input w-100"
            field.widget.attrs["class"] = css_class

    def clean_workbook(self):
        workbook = self.cleaned_data["workbook"]
        if Path(workbook.name).suffix.lower() != ".xlsx":
            raise forms.ValidationError(_("Upload an .xlsx workbook."))
        if workbook.size > MAX_IMPORT_BYTES:
            raise forms.ValidationError(_("The workbook exceeds the 5 MB limit."))
        return workbook

    def clean(self):
        cleaned_data = super().clean()
        recruitment = cleaned_data.get("recruitment")
        job_position = cleaned_data.get("job_position")
        if recruitment and job_position and not recruitment.open_positions.filter(
            pk=job_position.pk
        ).exists():
            self.add_error(
                "job_position",
                _("Choose a position from this recruitment."),
            )
        return cleaned_data
