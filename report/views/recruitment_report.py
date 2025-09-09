from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import render

if apps.is_installed("recruitment"):

    from base.models import Company
    from horilla.decorators import login_required, permission_required
    from onboarding.filters import OnboardingStageFilter
    from onboarding.models import OnboardingStage
    from recruitment.filters import CandidateFilter, RecruitmentFilter
    from recruitment.models import Candidate, Recruitment

    @login_required
    @permission_required(perm="recruitment.view_recruitment")
    def recruitment_report(request):
        company = "all"
        selected_company = request.session.get("selected_company")
        if selected_company != "all":
            company = Company.objects.filter(id=selected_company).first()
        return render(
            request,
            "report/recruitment_report.html",
            {
                "company": company,
                "f": CandidateFilter(),
                "fr": RecruitmentFilter(),
                "fo": OnboardingStageFilter(),
            },
        )

    @login_required
    @permission_required(perm="recruitment.view_recruitment")
    def recruitment_pivot(request):
        model_type = request.GET.get("model", "candidate")  # Default to Candidate

        if model_type == "candidate":
            qs = Candidate.objects.all()
            filter_obj = CandidateFilter(request.GET, queryset=qs)
            qs = filter_obj.qs

            data = list(
                qs.values(
                    "name",
                    "recruitment_id__title",
                    "job_position_id__job_position",
                    "stage_id__stage",
                    "email",
                    "mobile",
                    "gender",
                    "offer_letter_status",
                    "recruitment_id__closed",
                    "recruitment_id__vacancy",
                    "country",
                    "recruitment_id__company_id__company",
                    "address",
                    "dob",
                    "state",
                    "city",
                    "source",
                    "job_position_id__department_id__department",
                )
            )
            choice_gender = {
                "male": "Male",
                "female": "Female",
                "other": "Other",
            }
            OFFER_LETTER_STATUS = {
                "not_sent": "Not Sent",
                "sent": "Sent",
                "accepted": "Accepted",
                "rejected": "Rejected",
                "joined": "Joined",
            }
            SOURCE_CHOICE = {
                "application": "Application Form",
                "software": "Inside Software",
                "other": "Other",
            }

            data_list = [
                {
                    "Candidate": item["name"],
                    "Email": item["email"],
                    "Phone": item["mobile"],
                    "Gender": choice_gender.get(item["gender"]),
                    "Address": item["address"],
                    "Date Of Birth": item["dob"],
                    "Country": item["country"] if item["country"] else "-",
                    "State": item["state"] if item["state"] else "-",
                    "City": item["city"] if item["city"] else "-",
                    "Source": (
                        SOURCE_CHOICE.get(item["source"]) if item["source"] else "-"
                    ),
                    "Job Position": item["job_position_id__job_position"],
                    "Department": item["job_position_id__department_id__department"],
                    "Offer Letter": OFFER_LETTER_STATUS.get(
                        item["offer_letter_status"]
                    ),
                    "Recruitment": item["recruitment_id__title"],
                    "Current Stage": item["stage_id__stage"],
                    "Recruitment Status": (
                        "Closed" if item["recruitment_id__closed"] else "Open"
                    ),
                    "Vacancy": item["recruitment_id__vacancy"],
                    "Company": item["recruitment_id__company_id__company"],
                }
                for item in data
            ]
        elif model_type == "recruitment":
            qs = Recruitment.objects.all()
            filter_obj = RecruitmentFilter(request.GET, queryset=qs)
            qs = filter_obj.qs
            data = list(
                qs.values(
                    "title",
                    "vacancy",
                    "closed",
                    "open_positions__job_position",
                    "start_date",
                    "end_date",
                    "is_published",
                    "recruitment_managers__employee_first_name",
                    "recruitment_managers__employee_last_name",
                    "company_id__company",
                )
            )
            data_list = [
                {
                    "Recruitment": item["title"],
                    "Manager": f"{item['recruitment_managers__employee_first_name']} {item['recruitment_managers__employee_last_name']}",
                    "Is Closed": "Closed" if item["closed"] else "Open",
                    "Status": "Published" if item["is_published"] else "Not Published",
                    "Start Date": item["start_date"],
                    "End Date": item["end_date"],
                    "Job Position": item["open_positions__job_position"],
                    "Vacancy": item["vacancy"],
                    "Company": item["company_id__company"],
                }
                for item in data
            ]
        elif model_type == "onboarding":
            qs = OnboardingStage.objects.all()
            filter_obj = OnboardingStageFilter(request.GET, queryset=qs)
            qs = filter_obj.qs

            data = list(
                qs.values(
                    "stage_title",
                    "recruitment_id__title",
                    "employee_id__employee_first_name",
                    "employee_id__employee_last_name",
                    "onboarding_task__task_title",
                    "onboarding_task__employee_id__employee_first_name",
                    "onboarding_task__employee_id__employee_last_name",
                    "onboarding_task__candidates__name",
                    "recruitment_id__company_id__company",
                )
            )

            data_list = [
                {
                    "Recruitment": item["recruitment_id__title"],
                    "Stage": item["stage_title"],
                    "Stage Manager": (
                        f"{item['employee_id__employee_first_name']} {item['employee_id__employee_last_name']}"
                        if item["employee_id__employee_first_name"]
                        else "-"
                    ),
                    "Task": (
                        item["onboarding_task__task_title"]
                        if item["onboarding_task__task_title"]
                        else "-"
                    ),
                    "Task Manager": (
                        f"{item['onboarding_task__employee_id__employee_first_name']} {item['onboarding_task__employee_id__employee_last_name']}"
                        if item["onboarding_task__employee_id__employee_first_name"]
                        else "-"
                    ),
                    "Candidates": (
                        item["onboarding_task__candidates__name"]
                        if item["onboarding_task__candidates__name"]
                        else "-"
                    ),
                    "Company": (
                        item["recruitment_id__company_id__company"]
                        if item["recruitment_id__company_id__company"]
                        else "-"
                    ),
                }
                for item in data
            ]
        else:
            data_list = []
        return JsonResponse(data_list, safe=False)
