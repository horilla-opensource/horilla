"""
filters.py
Used to register filter for onboarding models
"""

import django_filters
from django import forms
from django_filters import filters

from base.filters import FilterSet
from horilla.filters import HorillaFilterSet
from onboarding.models import CandidateStage, OnboardingStage, OnboardingTask
from recruitment.filters import RecruitmentFilter
from recruitment.models import Candidate, Recruitment


class RecruitmentFilter(RecruitmentFilter):
    """
    RecruitmentFilter
    """

    search = django_filters.CharFilter(method="filter_by_name")

    class Meta:
        """
        Meta
        """

        model = Recruitment
        fields = "__all__"

    def filter_by_name(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        job_queryset = (
            queryset.filter(open_positions__job_position__icontains=value)
            | queryset.filter(title__icontains=value)
            | queryset.filter(onboarding_stage__stage_title__icontains=value)
            | queryset.filter(
                onboarding_stage__candidate__candidate_id__name__icontains=value
            )
        )
        if first_name and last_name:
            queryset = queryset.filter(
                recruitment_managers__employee_first_name__icontains=first_name,
                recruitment_managers__employee_last_name__icontains=last_name,
            )
        elif first_name:
            queryset = queryset.filter(
                recruitment_managers__employee_first_name__icontains=first_name
            )
        elif last_name:
            queryset = queryset.filter(
                recruitment_managers__employee_last_name__icontains=last_name
            )

        queryset = queryset | job_queryset
        return queryset.distinct()


class PipelineCandidateFilter(FilterSet):
    """
    FilterSet class for Candidate model
    """

    search = django_filters.CharFilter(method="search_by_name", lookup_expr="icontains")

    candidate = django_filters.ModelMultipleChoiceFilter(
        queryset=Candidate.objects.all(),
        field_name="name",
    )

    start_date = django_filters.DateFilter(
        field_name="candidate_id__recruitment_id__start_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="candidate_id__recruitment_id__end_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_from = django_filters.DateFilter(
        field_name="candidate_id__candidate_interview__interview_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end = django_filters.DateFilter(
        field_name="candidate_id__probation_end",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end_till = django_filters.DateFilter(
        field_name="candidate_id__probation_end",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end_from = django_filters.DateFilter(
        field_name="candidate_id__probation_end",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    schedule_date = django_filters.DateFilter(
        field_name="candidate_id__schedule_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    interview_date = django_filters.DateFilter(
        field_name="candidate_id__candidate_interview__interview_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_till = django_filters.DateFilter(
        field_name="candidate_id__candidate_interview__interview_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    recruitment = django_filters.CharFilter(
        field_name="candidate_id__recruitment_id__title", lookup_expr="icontains"
    )

    portal_sent = django_filters.BooleanFilter(
        field_name="onboarding_portal",
        method="filter_mail_sent",
        widget=django_filters.widgets.BooleanWidget(),
    )
    joining_set = django_filters.BooleanFilter(
        field_name="joining_date",
        method="filter_joining_set",
        widget=django_filters.widgets.BooleanWidget(),
    )

    class Meta:
        """
        Meta class to add some additional options
        """

        model = CandidateStage
        fields = "__all__"

    def search_by_name(self, queryset, _, value):
        """
        Search by name
        """
        queryset = (
            queryset.filter(candidate_id__name__icontains=value)
            | queryset.filter(onboarding_stage_id__stage_title__icontains=value)
            | queryset.filter(candidate_id__recruitment_id__title__icontains=value)
        )
        return queryset.distinct()


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
    search = filters.CharFilter(
        method="search_method",
    )

    class Meta:
        model = OnboardingStage
        fields = [
            "recruitment_id",
            "stage_title",
            "employee_id",
            "sequence",
            "is_final_stage",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields["employee_id"].widget.attrs.update({"style": "width:100%;"})

    def search_method(self, queryset, _, value):
        """
        Search by name
        """
        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        recruitment_query = (
            queryset.filter(recruitment_id__title__icontains=value)
            | queryset.filter(candidate__candidate_id__name__icontains=value)
            | queryset.filter(
                recruitment_id__onboarding_stage__candidate__candidate_id__name__icontains=value
            )
        )
        # Filter the queryset by first name and last name
        stage_queryset = queryset.filter(stage_title__icontains=value)
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
            queryset = queryset.filter(
                employee_id__employee_last_name__icontains=last_name
            )

        queryset = queryset | stage_queryset | recruitment_query
        return queryset.distinct()

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
    stage_id = filters.CharFilter(field_name="onboarding_stage_id")

    class Meta:
        model = CandidateStage
        fields = "__all__"


class OnboardingTaskFilter(FilterSet):
    """
    Onboarding task filter
    """

    search_onboarding = filters.CharFilter(
        field_name="task_title", lookup_expr="icontains"
    )

    class Meta:
        model = OnboardingTask
        fields = "__all__"
