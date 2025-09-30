"""
horilla_views/forms.py
"""

import os

from django import forms
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.safestring import SafeText
from django.utils.translation import gettext_lazy as _

from horilla.horilla_middlewares import _thread_locals
from horilla_views import models
from horilla_views.cbv_methods import (
    BOOLEAN_CHOICES,
    FIELD_WIDGET_MAP,
    MODEL_FORM_FIELD_MAP,
    get_field_class_map,
    get_original_model_field,
    structured,
)
from horilla_views.templatetags.generic_template_filters import getattribute


class ToggleColumnForm(forms.Form):
    """
    Toggle column form
    """

    def __init__(
        self,
        columns,
        default_columns,
        hidden_fields: list,
        *args,
        **kwargs,
    ):
        request = getattr(_thread_locals, "request", {})
        self.request = request
        super().__init__(*args, **kwargs)
        for column in columns:
            initial = True
            if column[1] in hidden_fields:
                initial = False
            if not hidden_fields:
                if default_columns and column not in default_columns:
                    initial = False
            self.fields[column[1]] = forms.BooleanField(
                label=column[0], initial=initial
            )

    def as_list(self) -> SafeText:
        """
        Render the form fields as HTML table rows with.
        """
        context = {"form": self, "request": self.request}
        table_html = render_to_string("generic/as_list.html", context)
        return table_html


class SavedFilterForm(forms.ModelForm):
    """
    SavedFilterForm
    """

    color = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "oh-input w-100",
                "type": "color",
                "placeholder": "Choose a color",
            }
        )
    )

    class Meta:
        model = models.SavedFilter
        fields = ["title", "is_default", "color"]

    def structured(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        request = getattr(_thread_locals, "request", None)
        context = {
            "form": self,
            "request": request,
        }
        table_html = render_to_string("common_form.html", context)
        return table_html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attrs = self.fields["title"].widget.attrs
        attrs["class"] = "oh-input w-100"
        attrs["placeholder"] = "Saved filter title"
        if self.instance.pk:
            self.verbose_name = self.instance.title


class DynamicBulkUpdateForm(forms.Form):
    """
    DynamicBulkUpdateForm
    """

    verbose_name = _("Bulk Update")

    def __init__(
        self,
        *args,
        root_model: models.models.Model = None,
        bulk_update_fields: list = [],
        ids: list = [],
        **kwargs,
    ):
        self.ids = ids
        self.root_model = root_model
        self.bulk_update_fields = sorted(
            bulk_update_fields, key=lambda x: x.count("__")
        )
        self.structured = structured
        mappings = get_field_class_map(root_model, bulk_update_fields)
        self.request = getattribute(_thread_locals, "request")

        super().__init__(*args, **kwargs)
        for key, val in mappings.items():
            widget = FIELD_WIDGET_MAP.get(type(val))
            field = MODEL_FORM_FIELD_MAP.get(type(val))
            if widget and field:
                if isinstance(val, models.models.BooleanField):
                    self.fields[key] = forms.ChoiceField(
                        choices=BOOLEAN_CHOICES,
                        widget=widget,
                        label=val.verbose_name.capitalize(),
                        required=False,
                    )
                    self.fields[key].widget.option_template_name = (
                        "horilla_widgets/select_option.html",
                    )
                    continue
                elif not getattribute(val, "related_model"):
                    if isinstance(val, models.models.CharField) and val.choices:
                        self.fields[key] = forms.ChoiceField(
                            choices=[("", "--------")]
                            + [choice for choice in val.choices if choice[0] != ""],
                            widget=forms.Select(
                                attrs={"class": "oh-select oh-select-2 w-100"}
                            ),
                            label=val.verbose_name.capitalize(),
                            required=False,
                        )
                        self.fields[key].widget.option_template_name = (
                            "horilla_widgets/select_option.html",
                        )
                        continue
                    self.fields[key] = field(
                        widget=widget,
                        label=val.verbose_name.capitalize(),
                        required=False,
                    )
                    self.fields[key].widget.option_template_name = (
                        "horilla_widgets/select_option.html",
                    )
                    continue
                queryset = val.related_model.objects.all()
                self.fields[key] = field(
                    widget=widget,
                    queryset=queryset,
                    label=val.verbose_name,
                    required=False,
                )
                self.fields[key].widget.option_template_name = (
                    "horilla_widgets/select_option.html",
                )

    def is_valid(self):
        valid = True
        try:
            with transaction.atomic():
                # Perform bulk update
                self.save()
                # Simulate error check
                raise Exception("no_errors")
        except Exception as e:
            # Handle errors or validation issues
            if not "no_errors" in str(e):
                valid = False
                self.add_error(None, f"Form not valid: {str(e)}")
        return valid

    def save(self, *args, **kwargs):
        """
        Bulk save method
        """
        mappings = get_field_class_map(self.root_model, self.bulk_update_fields)
        data_mapp = {}
        data_m2m_mapp = {}
        relation_mapp = {}
        map_queryset = {}
        fiels_mapping = {}
        parent_model = self.root_model
        for key, val in mappings.items():
            if val.model.__name__.startswith("Historical"):
                val.model = get_original_model_field(val.model)
            field = MODEL_FORM_FIELD_MAP.get(type(val))
            if field:
                if not fiels_mapping.get(val.model):
                    fiels_mapping[val.model] = {}
                if not data_m2m_mapp.get(val.model):
                    data_m2m_mapp[val.model] = {}
                if not data_mapp.get(val.model):
                    data_mapp[val.model] = {}
                    if not relation_mapp.get(val.model):
                        if val.model == self.root_model:
                            relation_mapp[val.model] = "id__in"
                        else:
                            related_key = key.split("__")[-2]
                            field = getattribute(parent_model, related_key)
                            if not hasattr(field, "related"):
                                continue
                            relation_mapp[val.model] = (
                                field.related.field.name
                                + "__"
                                + relation_mapp[parent_model]
                            )
                            parent_model = val.model
                files = self.files.getlist(key)
                value = self.data.getlist(key)
                if (not value or not value[0]) and not files:
                    continue
                key = key.split("__")[-1]
                model_field = getattribute(val.model, key).field
                if isinstance(model_field, models.models.ManyToManyField):
                    data_m2m_mapp[val.model][key] = value
                    continue
                if files and isinstance(
                    model_field,
                    (
                        models.models.FileField,
                        models.models.ImageField,
                    ),
                ):
                    file_path = os.path.join(model_field.upload_to, files[0].name)

                    data_mapp[val.model][key] = file_path
                    fiels_mapping[val.model][model_field] = files[0]
                    continue
                data_mapp[val.model][key] = value[0]

        for model, data in data_mapp.items():
            if not model in relation_mapp:
                continue
            queryset = model.objects.filter(**{relation_mapp[model]: self.ids})
            # here fields, files, and related fields-
            # get updated but need to save the files manually
            queryset.update(**data)
            map_queryset[model] = queryset
            m2m_data = data_m2m_mapp[model]
            # saving m2m
            if m2m_data:
                for field, ids in m2m_data.items():
                    related_objects = getattr(
                        model, field
                    ).field.related_model.objects.filter(id__in=ids)
                    for instance in queryset:
                        getattr(instance, field).set(related_objects)
        for model, files in fiels_mapping.items():
            if files:
                for field, file in files.items():
                    file_path = os.path.join(field.upload_to, file.name)
                    default_storage.save(file_path, ContentFile(file.read()))
