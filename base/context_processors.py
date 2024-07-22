"""
context_processor.py

This module is used to register context processor`
"""

from django.http import HttpResponse
from django.urls import path

from attendance.models import AttendanceGeneralSetting
from base.models import Company, TrackLateComeEarlyOut
from base.urls import urlpatterns
from employee.models import EmployeeGeneralSetting
from horilla import horilla_apps
from horilla.decorators import hx_request_required, login_required, permission_required
from offboarding.models import OffboardingGeneralSetting
from payroll.models.models import PayrollGeneralSetting
from recruitment.models import RecruitmentGeneralSetting


class AllCompany:
    """
    Dummy class
    """

    class Urls:
        url = "https://ui-avatars.com/api/?name=All+Company&background=random"

    company = "All Company"
    icon = Urls()
    text = "All companies"
    id = None


def get_companies(request):
    """
    This method will return the history additional field form
    """
    companies = list(
        [company.id, company.company, company.icon.url, False]
        for company in Company.objects.all()
    )
    companies = [
        [
            "all",
            "All Company",
            "https://ui-avatars.com/api/?name=All+Company&background=random",
            False,
        ],
    ] + companies
    selected_company = request.session.get("selected_company")
    company_selected = False
    if selected_company and selected_company == "all":
        companies[0][3] = True
        company_selected = True
    else:
        for company in companies:
            if str(company[0]) == selected_company:
                company[3] = True
                company_selected = True
    return {"all_companies": companies, "company_selected": company_selected}


@login_required
@hx_request_required
@permission_required("base.change_company")
def update_selected_company(request):
    """
    This method is used to update the selected company on the session
    """
    company_id = request.GET.get("company_id")
    request.session["selected_company"] = company_id
    company = (
        AllCompany()
        if company_id == "all"
        else (
            Company.objects.filter(id=company_id).first()
            if Company.objects.filter(id=company_id).first()
            else AllCompany()
        )
    )

    text = "Other Company"
    if company_id == request.user.employee_get.employee_work_info.company_id:
        text = "My Company"
    if company_id == "all":
        text = "All companies"
    company = {
        "company": company.company,
        "icon": company.icon.url,
        "text": text,
        "id": company.id,
    }
    request.session["selected_company_instance"] = company
    return HttpResponse("<script>window.location.reload();</script>")


urlpatterns.append(
    path(
        "update-selected-company",
        update_selected_company,
        name="update-selected-company",
    )
)


def white_labelling_company(request):
    white_labelling = getattr(horilla_apps, "WHITE_LABELLING", False)
    if white_labelling:
        hq = Company.objects.filter(hq=True).last()
        try:
            company = (
                request.user.employee_get.get_company()
                if request.user.employee_get.get_company()
                else hq
            )
        except:
            company = hq

        return {
            "white_label_company_name": company.company if company else "Horilla",
            "white_label_company": company,
        }
    else:
        return {
            "white_label_company_name": "Horilla",
            "white_label_company": None,
        }


def resignation_request_enabled(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    first = OffboardingGeneralSetting.objects.first()
    enabled_resignation_request = False
    if first:
        enabled_resignation_request = first.resignation_request
    return {"enabled_resignation_request": enabled_resignation_request}


def timerunner_enabled(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    first = AttendanceGeneralSetting.objects.first()
    enabled_timerunner = True
    if first:
        enabled_timerunner = first.time_runner
    return {"enabled_timerunner": enabled_timerunner}


def intial_notice_period(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    first = PayrollGeneralSetting.objects.first()
    initial = 30
    if first:
        initial = first.notice_period
    return {"get_initial_notice_period": initial}


def check_candidate_self_tracking(request):
    """
    This method is used to get the candidate self tracking is enabled or not
    """
    first = RecruitmentGeneralSetting.objects.first()
    candidate_self_tracking = False
    if first:
        candidate_self_tracking = first.candidate_self_tracking
    return {"check_candidate_self_tracking": candidate_self_tracking}


def check_candidate_self_tracking_rating(request):
    """
    This method is used to check enabled/disabled of rating option
    """
    first = RecruitmentGeneralSetting.objects.first()
    rating_option = False
    if first:
        rating_option = first.show_overall_rating
    return {"check_candidate_self_tracking_rating": rating_option}


def get_initial_prefix(request):
    """
    This method is used to get the initial prefix
    """
    settings = EmployeeGeneralSetting.objects.first()
    instance_id = None
    prefix = "PEP"
    if settings:
        instance_id = settings.id
        prefix = settings.badge_id_prefix
    return {"get_initial_prefix": prefix, "prefix_instance_id": instance_id}


def biometric_app_exists(request):
    from django.conf import settings

    biometric_app_exists = "biometric" in settings.INSTALLED_APPS
    return {"biometric_app_exists": biometric_app_exists}


def enable_late_come_early_out_tracking(request):
    tracking = TrackLateComeEarlyOut.objects.first()
    enable = tracking.is_enable if tracking else True
    return {"tracking": enable, "late_come_early_out_tracking": enable}
