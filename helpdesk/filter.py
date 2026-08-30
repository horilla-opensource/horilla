"""
filters.py

This page is used to register filter for employee models

"""

from datetime import date

import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _
from django_filters import CharFilter, DateFilter

from base.models import Tags
from helpdesk.models import FAQ, DepartmentManager, FAQCategory, Ticket, TicketType
from horilla.filters import FilterSet, HorillaFilterSet


class FAQFilter(FilterSet):
    """
    Filter set class for FAQ model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = CharFilter(field_name="question", lookup_expr="icontains")

    class Meta:
        """
        Meta class to add the additional info
        """

        model = FAQ
        fields = [
            "search",
            "tags",
        ]


class FAQCategoryFilter(FilterSet):
    """
    Filter set class for FAQ category model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        """
        Meta class to add the additional info
        """

        model = FAQCategory
        fields = [
            "search",
        ]


class TicketFilter(FilterSet):
    """
    Filter set class for Ticket model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = CharFilter(method="search_method")
    from_date = DateFilter(
        field_name="deadline",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    to_date = DateFilter(
        field_name="deadline",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    pipeline_status = django_filters.CharFilter(
        field_name="status",
    )
    is_open = django_filters.BooleanFilter(
        method="filter_is_open",
        widget=django_filters.widgets.BooleanWidget(),
    )
    is_overdue = django_filters.BooleanFilter(
        method="filter_is_overdue",
        widget=django_filters.widgets.BooleanWidget(),
    )
    department = django_filters.NumberFilter(
        field_name="employee_id__employee_work_info__department_id",
    )

    def filter_is_open(self, queryset, name, value):
        """
        Matches the dashboard's "Open Tickets" KPI, which combines three
        statuses (new/in_progress/on_hold) into one count -- there's no
        single `status` value that represents that, so this is a separate
        method filter rather than reusing the plain `status` field.
        """
        if value:
            return queryset.filter(status__in=["new", "in_progress", "on_hold"])
        return queryset

    def filter_is_overdue(self, queryset, name, value):
        """
        Matches the dashboard's "Overdue" KPI: past deadline AND still in
        one of the open statuses (from_date/to_date above are plain
        gte/lte comparisons, not this specific combination).
        """
        if value:
            return queryset.filter(
                deadline__lt=date.today(),
                status__in=["new", "in_progress", "on_hold"],
            )
        return queryset

    def search_method(self, queryset, name, value):
        """
        Search by ticket title or the owning employee's name.
        """
        value = (value or "").strip()
        if not value:
            return queryset
        return (
            queryset.filter(title__icontains=value)
            | queryset.filter(employee_id__employee_first_name__icontains=value)
            | queryset.filter(employee_id__employee_last_name__icontains=value)
        ).distinct()

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Ticket
        fields = [
            "title",
            "tags",
            "employee_id",
            "ticket_type",
            "priority",
            "deadline",
            "assigned_to",
            "status",
            "is_active",
        ]


class TicketReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "Select"),
        ("employee_id", _("Owner")),
        ("ticket_type", _("Ticket Type")),
        ("status", _("Status")),
        ("priority", _("Priority")),
        ("tags", _("Tags")),
        ("assigned_to", _("Assigner")),
        ("employee_id__employee_work_info__company_id", _("Company")),
    ]


class TicketTypeFilter(FilterSet):

    search = CharFilter(method="search_method")

    def search_method(self, queryset, _, value):
        """
        This method is used to search employees and objective
        """

        return (
            queryset.filter(title__icontains=value)
            | queryset.filter(type__icontains=value)
            | queryset.filter(prefix__icontains=value)
        ).distinct()

    class Meta:
        model = TicketType
        fields = ["title", "type", "prefix"]


class TagsFilter(FilterSet):

    search = CharFilter(method="search_method")

    def search_method(self, queryset, _, value):
        """
        This method is used to search employees and objective
        """

        return (queryset.filter(title__icontains=value)).distinct()

    class Meta:
        model = Tags
        fields = [
            "title",
        ]


class DepartmentManagerFilter(HorillaFilterSet):

    search = django_filters.CharFilter(method="search_method")
    search_field = django_filters.CharFilter(method="search_in")

    class Meta:
        model = DepartmentManager
        fields = ["department", "manager"]

    def search_method(self, queryset, _, value):
        """
        This method is used to search employees and objective
        """

        return (
            (queryset.filter(department__department__icontains=value))
            | queryset.filter(manager__employee_first_name__icontains=value)
        ).distinct()


class FaqSearch(FilterSet):
    search = CharFilter(method="search_method", lookup_expr="icontains")

    class Meta:
        model = FAQ
        fields = ["search"]

    def search_method(self, queryset, _, value):
        """
        This method is used to add custom search condition
        """
        return (
            queryset.filter(question__icontains=value)
            | queryset.filter(answer__icontains=value)
            | queryset.filter(tags__title__icontains=value)
        ).distinct()
