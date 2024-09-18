"""
filters.py
"""

import uuid

import django_filters
from django import forms
from django.core.paginator import Page, Paginator
from django.db import models
from django_filters.filterset import FILTER_FOR_DBFIELD_DEFAULTS

from base.methods import reload_queryset
from horilla.horilla_middlewares import _thread_locals
from horilla_views.templatetags.generic_template_filters import getattribute

FILTER_FOR_DBFIELD_DEFAULTS[models.ForeignKey][
    "filter_class"
] = django_filters.ModelMultipleChoiceFilter


def filter_by_name(queryset, name, value):
    """
    Filter queryset by first name or last name.
    """
    # Split the search value into first name and last name
    parts = value.split()
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Filter the queryset by first name and last name
    if first_name and last_name:
        queryset = queryset.filter(
            employee_id__employee_first_name__icontains=first_name,
            employee_id__employee_last_name__icontains=last_name,
        )
    elif first_name:
        queryset = queryset.filter(
            employee_id__employee_first_name__icontains=first_name
        )
    elif last_name:
        queryset = queryset.filter(employee_id__employee_last_name__icontains=last_name)

    return queryset


class FilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.form.fields)
        for field_name, field in self.form.fields.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                        "id": uuid.uuid4(),
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})
            elif isinstance(widget, (forms.ModelChoiceField)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )


class HorillaPaginator(Paginator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_count = 0
        self.end_count = 0

    def get_page(self, number):
        self.page = super().get_page(number)
        self.page.start_count = (
            1
            if number == 1 or number is None
            else max((int(number) - 1) * self.per_page + 1, 1)
        )
        self.page.end_count = (
            min(int(number) * self.per_page, self.count)
            if number and int(number) > 1
            else self.per_page
        )
        return self.page


class HorillaFilterSet(FilterSet):
    """
    HorillaFilterSet
    """

    verbose_name: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.verbose_name.items():
            self.form.fields[key].label = value

        request = getattr(_thread_locals, "request", None)
        if request:
            setattr(request, "is_filtering", True)

    def search_in(self, queryset, name, value):
        """
        Search in generic method for filter field
        """
        search = self.data.get("search", "")
        search_field = self.data.get("search_field")
        if not search_field:
            search_field = self.filters[name].field_name

        def _icontains(instance):
            result = str(getattribute(instance, search_field)).lower()
            return instance.pk if search in result else None

        ids = list(filter(None, map(_icontains, queryset)))
        return queryset.filter(id__in=ids)
