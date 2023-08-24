"""
dashboard.py

This module is used to write dashboard related views
"""

import datetime
from django.core import serializers
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from base.models import Department
from horilla.decorators import login_required
from recruitment.decorators import manager_can_enter
from recruitment.models import Candidate, Recruitment, Stage
from base.models import Department, JobPosition
from employee.models import Employee, EmployeeWorkInformation


@login_required
@manager_can_enter(perm="recruitment.view_recruitment")
def dashboard(request):
    """
    This method is used to render dashboard for recruitment module
    """
    candidates = Candidate.objects.all()
    onboard_candidates = Candidate.objects.filter(start_onboard=True)

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
        te = Candidate.objects.filter(job_position_id=job, stage_id__stage_type="test")
        test.append(te.count())

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

    job_data = list(zip(all_job, initial, test, interview, hired))

    recruitment_obj = Recruitment.objects.filter(closed=False)
    # print(recruitment_obj)

    recruitment_manager_mapping = {}

    for rec in recruitment_obj:
        recruitment_title = rec.title
        managers = []

        for manager in rec.recruitment_managers.all():
            name = manager.employee_first_name + " " + manager.employee_last_name
            managers.append(name)

        recruitment_manager_mapping[recruitment_title] = managers

    total_vacancy = 0
    for openings in recruitment_obj:
        total_vacancy += openings.vacancy

    hired_candidates = candidates.filter(hired=True)
    total_candidates = len(candidates)
    total_hired_candidates = len(hired_candidates)
    conversion_ratio = 0
    acceptance_ratio = 0
    if total_candidates != 0:
        acceptance_ratio = f"{((total_hired_candidates / total_candidates) * 100):.1f}"

    if total_vacancy != 0:
        conversion_ratio = f"{((total_hired_candidates / total_vacancy) * 100):.1f}"
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_candidates": total_candidates,
            "total_hired_candidates": total_hired_candidates,
            "conversion_ratio": conversion_ratio,
            "onboard_candidates": hired_candidates.filter(start_onboard=True),
            "job_data": job_data,
            "onboard_candidates": onboard_candidates,
            "total_vacancy": total_vacancy,
            "recruitment_manager_mapping": recruitment_manager_mapping,
            "acceptance_ratio": acceptance_ratio,
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
def dashboard_vacancy(request):
    """
    This method is used to generate a recruitment vacancy chart for the dashboard
    """

    recruitment_obj = Recruitment.objects.filter(closed=False, is_event_based=False)
    department = Department.objects.all()
    label = []
    data_set = [{"label": _("Openings"), "data": []}]

    for dep in department:
        department_title = dep.department
        label.append(department_title)

        vacancies_for_department = recruitment_obj.filter(
            job_position_id__department_id=dep
        )
        vacancies = [int(rec.vacancy) for rec in vacancies_for_department]

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
