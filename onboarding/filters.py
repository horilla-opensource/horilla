"""
filters.py
Used to register filter for onboarding models
"""
from django import forms
from django_filters import  filters
from onboarding.models import Candidate
from base.filters import FilterSet


class CandidateFilter(FilterSet):
    """
    FilterSet class for Candidate model
    """

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        """
        Meta class to add some additional options
        """

        model = Candidate
        fields = {}
