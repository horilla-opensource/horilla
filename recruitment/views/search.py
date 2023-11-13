"""
search.py

This module is used to register search/filter views methods
"""


import json
from urllib.parse import parse_qs
from django.shortcuts import render
from django.core.paginator import Paginator
from horilla.decorators import login_required, permission_required
from base.methods import sortby, get_key_instances
from recruitment.filters import (
    CandidateFilter,
    RecruitmentFilter,
    StageFilter,
    SurveyFilter,
)
from recruitment.models import Candidate, Recruitment, Stage, RecruitmentSurvey
from recruitment.views.paginator_qry import paginator_qry


@login_required
@permission_required(perm="recruitment.view_recruitment")
def recruitment_search(request):
    """
    This method is used to search recruitment
    """
    filter_obj = RecruitmentFilter(request.GET)
    previous_data = request.GET.urlencode()
    recruitment_obj = sortby(request, filter_obj.qs, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(Recruitment, data_dict)

    return render(
        request,
        "recruitment/recruitment_component.html",
        {
            "data": paginator_qry(recruitment_obj, request.GET.get("page")),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@permission_required(perm="recruitment.view_stage")
def stage_search(request):
    """
    This method is used to search stage
    """
    stages = StageFilter(request.GET).qs
    previous_data = request.GET.urlencode()
    stages = sortby(request, stages, "orderby")
    data_dict = parse_qs(previous_data)
    get_key_instances(Stage, data_dict)
    return render(
        request,
        "stage/stage_component.html",
        {
            "data": paginator_qry(stages, request.GET.get("page")),
            "pd": previous_data,
            "filter_dict": data_dict,
        },
    )


@login_required
@permission_required(perm="recruitment.view_candidate")
def candidate_search(request):
    """
    This method is used to search candidate model and return matching objects
    """
    previous_data = request.GET.urlencode()
    search = request.GET.get("search")
    if search is None:
        search = ""
    candidates = Candidate.objects.filter(name__icontains=search)
    candidates = CandidateFilter(request.GET, queryset=candidates).qs
    data_dict = []
    if not request.GET.get("dashboard"):
        data_dict = parse_qs(previous_data)
        get_key_instances(Candidate, data_dict)

    template = "candidate/candidate_card.html"
    if request.GET.get("view") == "list":
        template = "candidate/candidate_list.html"
    candidates = sortby(request, candidates, "orderby")
            
    field = request.GET.get("field")
    if field != "" and field is not None:
        field_copy = field.replace(".", "__")
        candidates = candidates.order_by(field_copy)
        template = "candidate/group_by.html"

    candidates = paginator_qry(candidates, request.GET.get("page"))
    return render(
        request,
        template,
        {
            "data": candidates,
            "pd": previous_data,
            "filter_dict": data_dict,
            "field":field,
        },
    )


@login_required
@permission_required(perm="recruitment.view_candidate")
def pipeline_candidate_search(request):
    """
    This method is used to search  candidate
    """
    template = "pipeline/pipeline_components/kanban_tabs.html"
    if request.GET.get("view") == "card":
        template = "pipeline/pipeline_components/kanban_tabs.html"
    return render(request, template)


@login_required
@permission_required(perm="recruitment.view_candidate")
def candidate_filter_view(request):
    """
    This method is used for filter,pagination and search candidate.
    """
    candidates = Candidate.objects.filter(is_active=True)
    template = "candidate/candidate_card.html"
    if request.GET.get('view') == 'list':
        template = "candidate/candidate_list.html"

    previous_data = request.GET.urlencode()
    filter_obj = CandidateFilter(
        request.GET, queryset=candidates
    )
    paginator = Paginator(filter_obj.qs, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        template,
        {"data": page_obj, "pd": previous_data},
    )


@login_required
@permission_required(perm="recruitment.view_recruitmentsurvey")
def filter_survey(request):
    """
    This method is used to filter/search the recruitment surveys
    """
    previous_data = request.GET.urlencode()
    filter_obj = SurveyFilter(request.GET)
    questions = filter_obj.qs
    requests_ids = json.dumps([instance.id for instance in paginator_qry(questions, request.GET.get("page")).object_list])
    data_dict = parse_qs(previous_data)
    get_key_instances(RecruitmentSurvey, data_dict)
    return render(
        request,
        "survey/survey_card.html",
        {
            "questions": paginator_qry(questions, request.GET.get("page")),
            "pd": previous_data,
            "filter_dict": data_dict,
            "requests_ids":requests_ids,
        },
    )
