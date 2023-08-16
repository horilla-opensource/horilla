"""
dashboard.py

This module is used to write dashboard related views
"""


from django.core import serializers
from django.http import JsonResponse
from django.shortcuts import render
from horilla.decorators import login_required
from recruitment.decorators import manager_can_enter
from recruitment.models import Candidate, Recruitment, Stage


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard(request):
    """
    This method is used to render individual dashboard for recruitment module
    """
    candidates = Candidate.objects.all()
    hired_candidates = candidates.filter(hired=True)
    total_candidates = len(candidates)
    total_hired_candidates = len(hired_candidates)
    hire_ratio = 0
    if total_candidates != 0:
        hire_ratio = f"{((total_hired_candidates / total_candidates) * 100):.1f}"
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_candidates": total_candidates,
            "total_hired_candidates": total_hired_candidates,
            "hire_ratio": hire_ratio,
            "onboard_candidates": hired_candidates.filter(start_onboard=True),
        },
    )


def stage_type_candidate_count(rec, stage_type):
    """
    This method is used find the count of candidate in recruitment
    """
    candidates_count = 0
    for stage_obj in rec.stage_set.filter(stage_type=stage_type):
        candidates_count = candidates_count + len(
            stage_obj.candidate_set.filter(is_active=True)
        )
    return candidates_count


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_pipeline(_):
    """
    This method is used generate recruitment dataset for the dashboard
    """
    recruitment_obj = Recruitment.objects.filter(closed=False)
    data_set = []
    labels = [type[1] for type in Stage.stage_types]
    for rec in recruitment_obj:
        data = [stage_type_candidate_count(rec, type[0]) for type in Stage.stage_types]
        data_set.append(
            {
                "label": rec.title
                if rec.title is not None
                else f"""{rec.job_position_id}
                 {rec.start_date}""",
                "data": data,
            }
        )
    return JsonResponse({"dataSet": data_set, "labels": labels})


def get_open_position(request):
    """
    This is an ajax method to render the open position to the recruitment

    Returns:
        obj: it returns the list of job positions
    """
    rec_id = request.GET["recId"]
    recruitment_obj = Recruitment.objects.get(id=rec_id)
    queryset = recruitment_obj.open_positions.all()
    job_info = serializers.serialize("json", queryset)
    rec_info = serializers.serialize("json", [recruitment_obj])
    return JsonResponse({"openPositions": job_info, "recruitmentInfo": rec_info})
