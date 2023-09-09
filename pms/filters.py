"""
Module: filters.py

This module contains custom Django filters and filter sets for 
the PMS (Performance Management System) app.
"""
import datetime
import django_filters
from django import forms
from django_filters import DateFilter
from pms.models import EmployeeObjective, Feedback


class DateRangeFilter(django_filters.Filter):
    """
    A custom Django filter for filtering querysets based on date ranges.

    This filter allows you to filter a queryset based on date ranges such as 'today',
    'yesterday', 'week', or 'month' in the 'created_at' field of model.
    """

    def filter(self, qs, value):
        if value:
            if value == "today":
                today = datetime.date.today()
                qs = qs.filter(created_at=today)
            if value == "yesterday":
                today = datetime.date.today()
                yesterday = today - datetime.timedelta(days=1)
                qs = qs.filter(created_at=yesterday)
            if value == "week":
                today = datetime.date.today()
                start_of_week = today - datetime.timedelta(days=today.weekday())
                end_of_week = start_of_week + datetime.timedelta(days=6)
                qs = qs.filter(created_at__range=[start_of_week, end_of_week])
            elif value == "month":
                today = datetime.date.today()
                start_of_month = datetime.date(today.year, today.month, 1)
                end_of_month = start_of_month + datetime.timedelta(days=31)
                qs = qs.filter(created_at__range=[start_of_month, end_of_month])
        return qs


class CustomFilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                filter_widget.field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                filter_widget.field.widget.attrs.update(
                    {"class": "oh-switch__checkbox"}
                )
            elif isinstance(widget, (forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            if isinstance(field, django_filters.CharFilter):
                field.lookup_expr = "icontains"


class ObjectiveFilter(CustomFilterSet):
    """
    Custom filter set for EmployeeObjective records.

    This filter set allows to filter EmployeeObjective records based on various criteria.
    """

    created_at_date_range = DateRangeFilter(field_name="created_at")
    created_at = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    updated_at = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = EmployeeObjective
        fields = [
            "objective",
            "status",
            "employee_id",
            "created_at",
            "start_date",
            "updated_at",
            "end_date",
            "archive",
            "emp_obj_id",
        ]


class FeedbackFilter(CustomFilterSet):
    """
    Custom filter set for Feedback records.

    This filter set allows to filter Feedback records based on various criteria.
    """

    review_cycle = django_filters.CharFilter(lookup_expr="icontains")
    created_at_date_range = DateRangeFilter(field_name="created_at")
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = Feedback
        fields = "__all__"

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super(FeedbackFilter, self).__init__(
            data=data, queryset=queryset, request=request, prefix=prefix
        )
