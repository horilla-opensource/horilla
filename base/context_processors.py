"""
context_processor.py

This module is used to register context processor`
"""
from django.urls import path
from django.http import HttpResponse
from base.models import Company
from base.urls import urlpatterns


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
