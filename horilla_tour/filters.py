"""Filters for the tour admin list views."""

import django_filters

from horilla.filters import HorillaFilterSet
from horilla_tour.models import Tour


class TourFilter(HorillaFilterSet):
    """Search + faceted filtering for the Tours settings list."""

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = Tour
        fields = ["audience", "trigger", "is_published", "match_type"]

    def search_method(self, queryset, _, value):
        """Free-text search across title, key and target page."""
        return (
            queryset.filter(title__icontains=value)
            | queryset.filter(slug__icontains=value)
            | queryset.filter(page_match__icontains=value)
        ).distinct()
