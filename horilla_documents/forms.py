from django import forms
from django.template.loader import render_to_string

from base.forms import ModelForm
from base.methods import reload_queryset
from employee.filters import EmployeeFilter
from employee.models import Employee
from horilla_documents.models import Document, DocumentRequest
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget


class DocumentRequestForm(ModelForm):
    """form to create a new Document Request"""

    class Meta:
        model = DocumentRequest
        fields = "__all__"
        exclude = ["is_active"]

    def clean(self):
        cleaned_data = super().clean()
        if isinstance(self.fields["employee_id"], HorillaMultiSelectField):
            self.errors.pop("employee_id", None)
            if len(self.data.getlist("employee_id")) < 1:
                raise forms.ValidationError({"employee_id": "This field is required"})

            employee_data = self.fields["employee_id"].queryset.filter(
                id__in=self.data.getlist("employee_id")
            )
            cleaned_data["employee_id"] = employee_data

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"] = HorillaMultiSelectField(
            queryset=Employee.objects.all(),
            widget=HorillaMultiSelectWidget(
                filter_route_name="employee-widget-filter",
                filter_class=EmployeeFilter,
                filter_instance_contex_name="f",
                filter_template_path="employee_filters.html",
                required=True,
                instance=self.instance,
            ),
            label="Employee",
        )
        reload_queryset(self.fields)


class DocumentForm(ModelForm):
    """form to create a new Document"""

    class Meta:
        model = Document
        fields = "__all__"
        exclude = ["document_request_id", "status", "reject_reason", "is_active"]
        widgets = {
            "employee_id": forms.HiddenInput(),
            "issue_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expiry_date"].widget.attrs.update(
            {
                "hx-target": "#id_notify_before_parent_div",
                "hx-trigger": "load,change",
                "hx-swap": "innerHTML",
                "hx-get": "/employee/get-notify-field/",
            }
        )


class DocumentUpdateForm(ModelForm):
    """form to Update a Document"""

    cols = {"document": 12}

    verbose_name = "Document"

    class Meta:
        model = Document
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "issue_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"type": "date", "class": "oh-input  w-100"}
            ),
        }


class DocumentRejectCbvForm(ModelForm):
    """form to add rejection reason while rejecting a Document"""

    cols = {"reject_reason": 12}

    class Meta:
        model = Document
        fields = ["reject_reason"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reject_reason"].widget.attrs["required"] = True


class DocumentRejectForm(ModelForm):
    verbose_name = Document()._meta.get_field("reject_reason").verbose_name

    class Meta:
        model = Document
        fields = ["reject_reason"]
