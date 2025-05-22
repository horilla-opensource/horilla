"""
filters.py

This page is used to register filter for employee models

"""

import django_filters
from django import forms
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

    search = CharFilter(field_name="title", lookup_expr="icontains")
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
        ("employee_id", "Owner"),
        ("ticket_type", "Ticket Type"),
        ("status", "Status"),
        ("priority", "Priority"),
        ("tags", "Tags"),
        ("assigned_to", "Assigner"),
        ("employee_id__employee_work_info__company_id", "Company"),
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
