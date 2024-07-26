"""
filters.py
Used to register filter for onboarding models
"""

from django import forms
from django_filters import filters

from base.filters import FilterSet
from onboarding.models import CandidateStage, OnboardingStage
from recruitment.models import Candidate


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


class OnboardingStageFilter(FilterSet):
    """
    OnboardingStageFilter
    """

    search_onboarding = filters.CharFilter(
        field_name="stage_title", method="pipeline_search"
    )

    class Meta:
        model = OnboardingStage
        fields = "__all__"

    def pipeline_search(self, queryset, _, value):
        """
        This method is used to search recruitment
        """
        queryset = queryset.filter(stage_title__icontains=value) | queryset.filter(
            candidate__candidate_id__name__icontains=value
        )
        return queryset.distinct()


class OnboardingCandidateFilter(FilterSet):
    """
    OnboardingStageFilter
    """

    search_onboarding = filters.CharFilter(
        field_name="candidate_id__name", lookup_expr="icontains"
    )

    class Meta:
        model = CandidateStage
        fields = "__all__"
