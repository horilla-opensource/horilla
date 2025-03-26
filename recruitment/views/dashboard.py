"""
dashboard.py

This module is used to write dashboard related views
"""

import datetime

from django.core import serializers
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from base.models import Department, JobPosition
from employee.models import EmployeeWorkInformation
from horilla.decorators import login_required
from recruitment.decorators import manager_can_enter
from recruitment.models import Candidate, Recruitment, SkillZone, Stage


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
def dashboard(request):
    """
    This method is used to render dashboard for recruitment module
    """
    candidates = Candidate.objects.all()
    stage_chart_count = 0
    vacancy_chart = Recruitment.objects.filter(closed=False, is_event_based=False)
    if vacancy_chart.exists():
        dep_vacancy = 1
    else:
        dep_vacancy = 0
    employee_info = EmployeeWorkInformation.objects.all()
    joining_list = []
    for rec in employee_info:
        if rec.date_joining != None:
            joining_list.append("OK")
    if joining_list != []:
        joining = 1
    else:
        joining = 0

    jobs = JobPosition.objects.all()
    all_job = []
    for job in jobs:
        jobpos = job.job_position
        all_job.append(jobpos)

    initial = []
    for job in jobs:
        ini = Candidate.objects.filter(
            job_position_id=job, stage_id__stage_type="initial"
        )
        initial.append(ini.count())

    test = []
    for job in jobs:
        tes = Candidate.objects.filter(job_position_id=job, stage_id__stage_type="test")
        test.append(tes.count())

    interview = []
    for job in jobs:
        inter = Candidate.objects.filter(
            job_position_id=job, stage_id__stage_type="interview"
        )
        interview.append(inter.count())

    hired = []
    for job in jobs:
        hire = Candidate.objects.filter(
            job_position_id=job, stage_id__stage_type="hired"
        )
        hired.append(hire.count())
    cancelled = []
    for job in jobs:
        cancelled_candidates = Candidate.objects.filter(
            job_position_id=job, stage_id__stage_type="cancelled"
        )
        cancelled.append(cancelled_candidates.count())

    job_data = list(zip(all_job, initial, test, interview, hired, cancelled))

    recruitment_obj = Recruitment.objects.filter(closed=False)
    ongoing_recruitments = len(recruitment_obj)

    for rec in recruitment_obj:
        data = [stage_type_candidate_count(rec, type[0]) for type in Stage.stage_types]
        for i in data:
            stage_chart_count += i

        if stage_chart_count >= 1:
            stage_chart_count = 1

    accepted = Candidate.objects.filter(offer_letter_status="accepted")
    accepted_count = accepted.count()

    recruitment_manager_mapping = {}

    for rec in recruitment_obj:
        recruitment_title = rec.title
        managers = []

        for manager in rec.recruitment_managers.all():
            name = manager.get_full_name()
            managers.append(name)

        recruitment_manager_mapping[recruitment_title] = managers

    total_vacancy = 0
    for openings in recruitment_obj:
        if openings.vacancy == None:
            pass
        else:
            total_vacancy += openings.vacancy

    hired_candidates = candidates.filter(
        Q(hired=True) | Q(stage_id__stage_type="hired")
    ).distinct()
    total_candidates = len(candidates)
    total_hired_candidates = len(hired_candidates)
    conversion_ratio = 0
    hired_ratio = 0
    total_candidate_ratio = 0
    acceptance_ratio = 0
    if total_candidates != 0:
        conversion_ratio = f"{((total_hired_candidates / total_candidates) * 100):.1f}"
    if total_vacancy != 0:
        hired_ratio = f"{((total_hired_candidates / total_vacancy) * 100):.1f}"
        total_candidate_ratio = f"{((total_candidates / total_vacancy) * 100):.1f}"
    if total_hired_candidates != 0:
        acceptance_ratio = f"{((accepted_count / total_hired_candidates) * 100):.1f}"

    skill_zone = SkillZone.objects.filter(is_active=True)
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "ongoing_recruitments": ongoing_recruitments,
            "total_candidate_ratio": total_candidate_ratio,
            "total_hired_candidates": total_hired_candidates,
            "conversion_ratio": conversion_ratio,
            "acceptance_ratio": acceptance_ratio,
            "onboard_candidates": hired_candidates.filter(
                onboarding_stage__isnull=False
            ),
            "job_data": job_data,
            "total_vacancy": total_vacancy,
            "recruitment_manager_mapping": recruitment_manager_mapping,
            "hired_ratio": hired_ratio,
            "joining": joining,
            "dep_vacancy": dep_vacancy,
            "stage_chart_count": stage_chart_count,
            "onboarding_count": hired_candidates.filter(
                onboarding_stage__isnull=False
            ).count(),
            "total_candidates": total_candidates,
            "skill_zone": skill_zone,
        },
    )


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_pipeline(request):
    """
    This method is used generate recruitment dataset for the dashboard
    """
    recruitment_obj = Recruitment.objects.filter(closed=False)
    data_set = []
    labels = [type[1] for type in Stage.stage_types]
    for rec in recruitment_obj:
        data = [stage_type_candidate_count(rec, type[0]) for type in Stage.stage_types]
        if rec.candidate.all():
            data_set.append(
                {
                    "label": (
                        rec.title
                        if rec.title is not None
                        else f"""{rec.job_position_id}
                    {rec.start_date}"""
                    ),
                    "data": data,
                }
            )
    return JsonResponse(
        {
            "dataSet": data_set,
            "labels": labels,
            "message": _("No records available at the moment."),
        }
    )


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_hiring(request):
    """
    This method is used generate employee joining status for the dashboard
    """

    selected_year = request.GET.get("id")

    employee_info = EmployeeWorkInformation.objects.filter(
        date_joining__year=selected_year
    )

    # Create a list to store the count of employees for each month
    employee_count_per_month = [0] * 12  # Initialize with zeros for all months

    # Count the number of employees who joined in each month for the selected year
    for info in employee_info:
        if isinstance(info.date_joining, datetime.date):
            month_index = info.date_joining.month - 1  # Month index is zero-based
            employee_count_per_month[
                month_index
            ] += 1  # Increment the count for the corresponding month

    labels = [
        _("January"),
        _("February"),
        _("March"),
        _("April"),
        _("May"),
        _("June"),
        _("July"),
        _("August"),
        _("September"),
        _("October"),
        _("November"),
        _("December"),
    ]

    data_set = [
        {
            "label": _("Employees joined in %(year)s") % {"year": selected_year},
            "data": employee_count_per_month,
            "backgroundColor": "rgba(236, 131, 25)",
        }
    ]

    return JsonResponse({"dataSet": data_set, "labels": labels})


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard_vacancy(_request):
    """
    This method is used to generate a recruitment vacancy chart for the dashboard
    """

    recruitment_obj = Recruitment.objects.filter(closed=False, is_event_based=False)
    department = Department.objects.all()
    label = []
    data_set = [{"label": _("Openings"), "data": []}]

    for dep in department:
        vacancies_for_department = recruitment_obj.filter(
            job_position_id__department_id=dep
        )
        for rec in vacancies_for_department:
            if rec.vacancy is not None:
                label.append(dep.department)

        vacancies = [
            int(rec.vacancy) if rec.vacancy is not None else 0
            for rec in vacancies_for_department
        ]

        data_set[0]["data"].append([sum(vacancies)])

    return JsonResponse({"dataSet": data_set, "labels": label})


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


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def candidate_status(_request):
    """
    This method is used to generate a CAndidate status chart for the dashboard
    """

    not_sent_candidates = Candidate.objects.filter(
        offer_letter_status="not_sent"
    ).count()
    sent_candidates = Candidate.objects.filter(offer_letter_status="sent").count()
    accepted_candidates = Candidate.objects.filter(
        offer_letter_status="accepted"
    ).count()
    rejected_candidates = Candidate.objects.filter(
        offer_letter_status="rejected"
    ).count()
    joined_candidates = Candidate.objects.filter(offer_letter_status="joined").count()

    data_set = []
    labels = ["Not Sent", "Sent", "Accepted", "Rejected", "Joined"]
    data = [
        not_sent_candidates,
        sent_candidates,
        accepted_candidates,
        rejected_candidates,
        joined_candidates,
    ]

    for i in range(len(data)):

        data_set.append({"label": labels[i], "data": data[i]})

    # for i in range(len(data)):
    #     if data[i] != 0:
    #         data_set.append({
    #             "label": labels[i],
    #             "data": data[i]
    #         })

    # # Remove labels corresponding to data points with value 0
    # labels = [label for label, d in zip(labels, data) if d != 0]

    return JsonResponse({"dataSet": data_set, "labels": labels})
