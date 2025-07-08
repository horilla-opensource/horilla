"""
filters.py

This page is used to register filter for recruitment models

"""

import uuid

import django_filters
from django import forms
from django.utils.translation import gettext_lazy as _

from base.filters import FilterSet
from recruitment.models import (
    Candidate,
    InterviewSchedule,
    LinkedInAccount,
    Recruitment,
    RecruitmentSurvey,
    SkillZone,
    SkillZoneCandidate,
    Stage,
    SurveyTemplate,
)

# from django.forms.widgets import Boo


class CandidateFilter(FilterSet):
    """
    Filter set class for Candidate model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    start_onboard = django_filters.CharFilter(
        method="start_onboard_method", lookup_expr="icontains"
    )

    candidate = django_filters.ModelMultipleChoiceFilter(
        queryset=Candidate.objects.all(),
        field_name="name",
    )

    candidate_name = django_filters.CharFilter(
        method="pipeline_search", lookup_expr="icontains"
    )
    start_date = django_filters.DateFilter(
        field_name="recruitment_id__start_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="recruitment_id__end_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_from = django_filters.DateFilter(
        field_name="candidate_interview__interview_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end = django_filters.DateFilter(
        field_name="probation_end",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end_till = django_filters.DateFilter(
        field_name="probation_end",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end_from = django_filters.DateFilter(
        field_name="probation_end",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    schedule_date = django_filters.DateFilter(
        field_name="schedule_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hired_date = django_filters.DateFilter(
        field_name="hired_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    interview_date = django_filters.DateFilter(
        field_name="candidate_interview__interview_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_till = django_filters.DateFilter(
        field_name="candidate_interview__interview_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    recruitment = django_filters.CharFilter(
        field_name="recruitment_id__title", lookup_expr="icontains"
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

    def pipeline_search(self, queryset, _, value):
        """
        This method is used to include the candidates when they in the recruitment/stages
        """
        queryset = (
            queryset.filter(name__icontains=value)
            | queryset.filter(stage_id__stage__icontains=value)
            | queryset.filter(stage_id__recruitment_id__title__icontains=value)
        ).distinct()
        return queryset

    def start_onboard_method(self, queryset, _, value):
        """
        This method will include the candidates whether they are on the onboarding pipline stage
        """

        return queryset.filter(onboarding_stage__isnull=False)

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Candidate
        fields = [
            "recruitment",
            "recruitment_id",
            "stage_id",
            "schedule_date",
            "candidate_interview__interview_date",
            "email",
            "mobile",
            "country",
            "state",
            "city",
            "zip",
            "gender",
            "start_onboard",
            "hired",
            "converted",
            "canceled",
            "is_active",
            "recruitment_id__company_id",
            "job_position_id",
            "recruitment_id__closed",
            "recruitment_id__is_active",
            "job_position_id__department_id",
            "recruitment_id__recruitment_managers",
            "stage_id__stage_managers",
            "stage_id__stage_type",
            "joining_date",
            "skillzonecandidate_set__skill_zone_id",
            "skillzonecandidate_set__candidate_id",
            "portal_sent",
            "joining_set",
            "rejected_candidate__reject_reason_id",
            "offer_letter_status",
            "candidate_rating__rating",
            "candidate_interview__employee_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        form_fields = self.form.fields
        form_fields["is_active"].initial = True

        for field in form_fields:
            form_fields[field].widget.attrs["id"] = str(uuid.uuid4())

        self._update_field_labels(form_fields)

    def _update_field_labels(self, form_fields):
        """Helper method to update field labels from model verbose names"""

        models = {
            "recruitment": Recruitment(),
            "interview": InterviewSchedule(),
            "skill_zone": SkillZoneCandidate(),
        }

        interview_date_label = (
            models["interview"]._meta.get_field("interview_date").verbose_name
        )

        field_label_map = {
            "interview_date": interview_date_label,
            "scheduled_from": f"{interview_date_label} From",
            "scheduled_till": f"{interview_date_label} Till",
            "rejected_candidate__reject_reason_id": _("Reject Reason"),
            "job_position_id__department_id": _("Department"),
            "stage_id__stage_type": _("Stage Type"),
            "stage_id__stage_managers": _("Stage Managers"),
            "skillzonecandidate_set__skill_zone_id": models["skill_zone"]
            ._meta.get_field("skill_zone_id")
            .verbose_name,
            "start_date": models["recruitment"]
            ._meta.get_field("start_date")
            .verbose_name,
            "end_date": models["recruitment"]._meta.get_field("end_date").verbose_name,
            "recruitment_id__company_id": models["recruitment"]
            ._meta.get_field("company_id")
            .verbose_name,
            "recruitment_id__closed": models["recruitment"]
            ._meta.get_field("closed")
            .verbose_name,
            "recruitment_id__recruitment_managers": models["recruitment"]
            ._meta.get_field("recruitment_managers")
            .verbose_name,
        }

        for field_name, label in field_label_map.items():
            if field_name in form_fields:
                form_fields[field_name].label = label

    def filter_mail_sent(self, queryset, name, value):
        return queryset.filter(onboarding_portal__isnull=(not value))

    def filter_joining_set(self, queryset, name, value):
        return queryset.filter(joining_date__isnull=(not value))


BOOLEAN_CHOICES = (
    ("", ""),
    ("false", "False"),
    ("true", "True"),
)


class RecruitmentFilter(FilterSet):
    """
    Filter set class for Recruitment model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    candidate_name = django_filters.CharFilter(
        field_name="title", method="pipeline_search"
    )
    search_onboarding = django_filters.CharFilter(
        field_name="title", method="onboarding_search"
    )
    description = django_filters.CharFilter(lookup_expr="icontains")
    start_date = django_filters.DateFilter(
        field_name="start_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = django_filters.DateFilter(
        field_name="end_date", widget=forms.DateInput(attrs={"type": "date"})
    )
    start_from = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_till = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    search = django_filters.CharFilter(method="filter_by_name")
    is_active = django_filters.ChoiceFilter(
        choices=[
            (True, "Yes"),
            (False, "No"),
        ]
    )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Recruitment
        fields = [
            "recruitment_managers",
            "company_id",
            "title",
            "is_event_based",
            "start_date",
            "end_date",
            "closed",
            "is_active",
            "is_published",
            "job_position_id",
            "open_positions",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        start_date_verbose = self.Meta.model._meta.get_field("start_date").verbose_name
        end_date_verbose = self.Meta.model._meta.get_field("end_date").verbose_name
        self.form.fields["start_from"].label = f"{start_date_verbose} From"
        self.form.fields["end_till"].label = f"{end_date_verbose} Till"

    def filter_by_name(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        job_queryset = queryset.filter(
            open_positions__job_position__icontains=value
        ) | queryset.filter(title__icontains=value)
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

    def pipeline_search(self, queryset, _, value):
        """
        This method is used to search recruitment
        """
        queryset = (
            queryset.filter(title__icontains=value)
            | queryset.filter(stage_set__stage__icontains=value)
            | queryset.filter(candidate__name__icontains=value)
        )
        return queryset.distinct()

    def onboarding_search(self, queryset, _, value):
        """
        This method is used to search recruitment
        """
        queryset = (
            queryset.filter(title__icontains=value)
            | queryset.filter(onboarding_stage__stage_title__icontains=value)
            | queryset.filter(
                candidate__onboarding_stage__candidate_id__name__icontains=value
            )
        )
        return queryset.distinct()


class StageFilter(FilterSet):
    """
    Filter set class for Stage model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(method="filter_by_name")
    candidate_name = django_filters.CharFilter(method="pipeline_search")

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Stage
        fields = [
            "recruitment_id",
            "recruitment_id__job_position_id",
            "recruitment_id__job_position_id__department_id",
            "recruitment_id__company_id",
            "recruitment_id__recruitment_managers",
            "stage_managers",
            "stage_type",
        ]

    def filter_by_name(self, queryset, _, value):
        """
        Filter queryset by first name or last name.
        """
        # Split the search value into first name and last name
        parts = value.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        recruitment_query = queryset.filter(recruitment_id__title__icontains=value)
        # Filter the queryset by first name and last name
        stage_queryset = queryset.filter(stage__icontains=value)
        if first_name and last_name:
            queryset = queryset.filter(
                stage_managers__employee_first_name__icontains=first_name,
                stage_managers__employee_last_name__icontains=last_name,
            )
        elif first_name:
            queryset = queryset.filter(
                stage_managers__employee_first_name__icontains=first_name
            )
        elif last_name:
            queryset = queryset.filter(
                stage_managers__employee_last_name__icontains=last_name
            )

        queryset = queryset | stage_queryset | recruitment_query
        return queryset

    def pipeline_search(self, queryset, _, value):
        """
        This method is used to search recruitment
        """
        queryset = (
            queryset.filter(stage__icontains=value)
            | queryset.filter(candidate__name__icontains=value)
            | queryset.filter(recruitment_id__title__icontains=value)
        )
        return queryset.distinct()


class SurveyFilter(FilterSet):
    """
    SurveyFIlter
    """

    options = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Options",
        field_name="options",
    )

    question = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Question",
        field_name="question",
    )

    class Meta:
        """
        class Meta for additional options
        """

        model = RecruitmentSurvey
        fields = "__all__"
        exclude = [
            "sequence",
        ]


class SurveyTemplateFilter(django_filters.FilterSet):
    """
    SurveyTemplateFilter
    """

    question = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Title",
        field_name="title",
    )

    class Meta:
        model = SurveyTemplate
        fields = "__all__"


class CandidateReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("recruitment_id", "Recruitment"),
        ("job_position_id", "Job Position"),
        ("hired", "Hired"),
        ("country", "Country"),
        ("stage_id", "Stage"),
        ("joining_date", "Date Joining"),
        ("probation_end", "Probation End"),
        ("offer_letter_status", "Offer Letter Status"),
        ("rejected_candidate__reject_reason_id", "Reject Reason"),
        ("skillzonecandidate_set__skill_zone_id", "Skill Zone"),
    ]


class SkillZoneFilter(FilterSet):
    """
    Skillzone Filter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        """
        class Meta for additional options
        """

        model = SkillZone
        fields = [
            "is_active",
            "skillzonecandidate_set__candidate_id",
            "skillzonecandidate_set__candidate_id__recruitment_id",
            "skillzonecandidate_set__candidate_id__job_position_id",
            "skillzonecandidate_set__candidate_id__stage_id__stage_type",
        ]


class SkillZoneCandFilter(FilterSet):
    """
    Skillzone Candidate FIlter
    """

    search = django_filters.CharFilter(
        field_name="candidate_id__name", method="cand_search"
    )
    start_date = django_filters.DateFilter(
        field_name="candidate__id__recruitment_id__start_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="candidate__id__recruitment_id__end_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_from = django_filters.DateFilter(
        field_name="candidate__id__joining_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Joining From"),
    )
    probation_end = django_filters.DateFilter(
        field_name="candidate__id__probation_end",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    probation_end_till = django_filters.DateFilter(
        field_name="candidate__id__probation_end",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Probation Till"),
    )
    probation_end_from = django_filters.DateFilter(
        field_name="candidate__id__probation_end",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Probation From"),
    )
    schedule_date = django_filters.DateFilter(
        field_name="candidate__id__schedule_date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_till = django_filters.DateFilter(
        field_name="candidate__id__joining_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Joining Till"),
    )
    recruitment = django_filters.CharFilter(
        field_name="candidate__id__recruitment_id__title", lookup_expr="icontains"
    )

    portal_sent = django_filters.BooleanFilter(
        field_name="candidate__id__onboarding_portal",
        method="filter_mail_sent",
        widget=django_filters.widgets.BooleanWidget(),
        label=_("Portal Sent"),
    )
    joining_set = django_filters.BooleanFilter(
        field_name="candidate__id__joining_date",
        method="filter_joining_set",
        widget=django_filters.widgets.BooleanWidget(),
        label=_("Joining Set"),
    )

    class Meta:
        """
        class Meta for additional options
        """

        model = SkillZoneCandidate
        fields = [
            "is_active",
            "candidate_id",
            "candidate_id__recruitment_id",
            "candidate_id__stage_id",
            "candidate_id__schedule_date",
            "candidate_id__email",
            "candidate_id__mobile",
            "candidate_id__country",
            "candidate_id__state",
            "candidate_id__city",
            "candidate_id__zip",
            "candidate_id__gender",
            "candidate_id__start_onboard",
            "candidate_id__hired",
            "candidate_id__canceled",
            "candidate_id__is_active",
            "candidate_id__recruitment_id__company_id",
            "candidate_id__job_position_id",
            "candidate_id__recruitment_id__closed",
            "candidate_id__recruitment_id__is_active",
            "candidate_id__job_position_id__department_id",
            "candidate_id__recruitment_id__recruitment_managers",
            "candidate_id__stage_id__stage_managers",
            "candidate_id__stage_id__stage_type",
            "candidate_id__joining_date",
            "candidate_id__skillzonecandidate_set__skill_zone_id",
            "candidate_id__skillzonecandidate_set__candidate_id",
            "candidate_id__rejected_candidate__reject_reason_id",
            "candidate_id__offer_letter_status",
            "candidate_id__candidate_rating__rating",
        ]
        exclude = [
            "reason",
            "objects",
        ]

    def cand_search(self, queryset, _, value):
        """
        This method to include candidate when search skill zone
        """
        return (
            queryset.filter(candidate_id__name__icontains=value)
            | queryset.filter(skill_zone_id__title__icontains=value)
        ).distinct()


class InterviewFilter(FilterSet):
    """
    Filter set class for Candidate model

    Args:
        FilterSet (class): custom filter set class to apply styling
    """

    search = django_filters.CharFilter(
        field_name="candidate_id__name", lookup_expr="icontains"
    )

    scheduled_from = django_filters.DateFilter(
        field_name="interview_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    scheduled_till = django_filters.DateFilter(
        field_name="interview_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        """
        Meta class to add the additional info
        """

        model = InterviewSchedule
        fields = [
            "candidate_id",
            "employee_id",
            "interview_date",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form["scheduled_from"].label = (
            f"{self.Meta.model()._meta.get_field('interview_date').verbose_name} From"
        )
        self.form["scheduled_till"].label = (
            f"{self.Meta.model()._meta.get_field('interview_date').verbose_name} Till"
        )


class LinkedInAccountFilter(FilterSet):
    """LinkedInAccount filter"""

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = LinkedInAccount
        fields = ["username", "email", "company_id"]

    def search_method(self, queryset, _, value: str):
        """Method is used to search through LinkedInAccount"""
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = (
                empty
                | (queryset.filter(username__icontains=split))
                | (queryset.filter(email__icontains=split))
            )
        return empty.distinct()
