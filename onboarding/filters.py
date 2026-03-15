"""
filters.py
Used to register filter for onboarding models
"""

from django import forms
from django_filters import filters

from base.filters import FilterSet
from base.models import Company
from employee.models import Employee
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

    employee_id = filters.ModelChoiceFilter(
        queryset=Employee.objects.all(), label="Stage Manager"
    )

    onboarding_task__task_title = filters.CharFilter(
        field_name="onboarding_task__task_title", lookup_expr="icontains", label="Task"
    )

    onboarding_task__employee_id = filters.ModelChoiceFilter(
        field_name="onboarding_task__employee_id",
        queryset=Employee.objects.all(),
        label="Task Manager",
    )

    recruitment_id__company_id = filters.ModelChoiceFilter(
        field_name="recruitment_id__company_id",
        queryset=Company.objects.all(),
        label="Company",
    )

    onboarding_task__candidates = filters.ModelChoiceFilter(
        field_name="onboarding_task__candidates",
        queryset=Candidate.objects.all(),
        label="Candidates",
    )

    class Meta:
        model = OnboardingStage
        fields = "__all__"

    def pipeline_search(self, queryset, _, value):
        """
        This method is used to search recruitment
        """
        queryset = (
            queryset.filter(stage_title__icontains=value)
            | queryset.filter(candidate__candidate_id__name__icontains=value)
            | queryset.filter(recruitment_id__title__icontains=value)
        )
        return queryset.distinct()


class OnboardingCandidateFilter(FilterSet):
    """
    OnboardingStageFilter
    """

    search_onboarding = filters.CharFilter(
        field_name="candidate_id__name", method="pipeline_search"
    )

    class Meta:
        model = CandidateStage
        fields = [
            "candidate_id",
            "onboarding_stage_id",
            "sequence",
            "onboarding_end_date",
        ]

    def pipeline_search(self, queryset, _, value):
        """
        This method is used to search recruitment
        """
        queryset = (
            queryset.filter(onboarding_stage_id__stage_title__icontains=value)
            | queryset.filter(candidate_id__name__icontains=value)
            | queryset.filter(
                onboarding_stage_id__recruitment_id__title__icontains=value
            )
        )
        return queryset.distinct()
