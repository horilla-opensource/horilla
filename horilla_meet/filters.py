"""
horilla_mail/filters.py
"""

from django import forms

from horilla.filters import HorillaFilterSet, django_filters
from horilla_meet.models import GoogleMeeting


class GoogleMeetingFilter(HorillaFilterSet):
    """
    AutomationFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    from_date = django_filters.DateFilter(
        field_name="start_time",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    to_date = django_filters.DateFilter(
        field_name="start_time",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = GoogleMeeting
        fields = "__all__"
        exclude = ["attendees"]
