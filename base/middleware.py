"""
middleware.py
"""

from django.apps import apps
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render

from base.context_processors import AllCompany
from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company, ShiftRequest, WorkTypeRequest
from employee.models import (
    DisciplinaryAction,
    Employee,
    EmployeeBankDetails,
    EmployeeWorkInformation,
)
from horilla.horilla_settings import APPS
from horilla.methods import get_horilla_model_class
from horilla_documents.models import DocumentRequest


class CompanyMiddleware:
    """
    company middleware class
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the current user's company_id from the request
        if getattr(request, "user", False) and not request.user.is_anonymous:
            company_id = None
            try:

                company_id = getattr(
                    request.user.employee_get.employee_work_info, "company_id", None
                )
            except:
                pass
            if (
                request.session.get("selected_company")
                and request.session.get("selected_company") != "all"
            ):
                company_id = Company.objects.filter(
                    id=request.session.get("selected_company")
                ).first()
            elif company_id and request.session.get("selected_company") != "all":
                request.session["selected_company"] = company_id.id
                request.session["selected_company_instance"] = {
                    "company": company_id.company,
                    "icon": company_id.icon.url,
                    "text": "My company",
                    "id": company_id.id,
                }
            elif not company_id:
                request.session["selected_company"] = "all"
                all_company = AllCompany()
                request.session["selected_company_instance"] = {
                    "company": all_company.company,
                    "icon": all_company.icon.url,
                    "text": all_company.text,
                    "id": all_company.id,
                }

            app_models = [
                model for model in apps.get_models() if model._meta.app_label in APPS
            ]

            company_models = [
                Employee,
                ShiftRequest,
                WorkTypeRequest,
                DocumentRequest,
                DisciplinaryAction,
                EmployeeBankDetails,
                EmployeeWorkInformation,
            ]

            app_model_mappings = {
                "recruitment": ["recruitment", "candidate"],
                "leave": [
                    "leaverequest",
                    "restrictleave",
                    "availableleave",
                    "leaveallocationrequest",
                    "compensatoryleaverequest",
                ],
                "asset": ["assetassignment", "assetrequest"],
                "attendance": [
                    "attendance",
                    "attendanceactivity",
                    "attendanceovertime",
                    "workrecords",
                ],
                "payroll": [
                    "contract",
                    "loanaccount",
                    "payslip",
                    "reimbursement",
                    "workrecord",
                ],
                "helpdesk": ["ticket"],
                "offboarding": ["offboarding"],
                "pms": ["employeeobjective"],
            }

            # Dynamically add models if their respective apps are installed

            for app_label, models in app_model_mappings.items():
                if apps.is_installed(app_label):
                    company_models.extend(
                        [get_horilla_model_class(app_label, model) for model in models]
                    )
            if company_id:
                for model in app_models:
                    is_company_model = model in company_models
                    company_field = getattr(model, "company_id", None)
                    is_horilla_manager = isinstance(
                        model.objects, HorillaCompanyManager
                    )
                    related_company_field = getattr(
                        model.objects, "related_company_field", None
                    )

                    if is_company_model:
                        if company_field:
                            model.add_to_class(
                                "company_filter", Q(company_id=company_id)
                            )
                        elif is_horilla_manager and related_company_field:
                            model.add_to_class(
                                "company_filter",
                                Q(**{related_company_field: company_id}),
                            )
                    else:
                        if company_field:
                            model.add_to_class(
                                "company_filter",
                                Q(company_id=company_id) | Q(company_id__isnull=True),
                            )
                        elif is_horilla_manager and related_company_field:
                            model.add_to_class(
                                "company_filter",
                                Q(**{related_company_field: company_id})
                                | Q(**{f"{related_company_field}__isnull": True}),
                            )

        response = self.get_response(request)
        return response


# MIDDLEWARE TO CHECK IF EMPLOYEE IS NEW USER OR NOT
class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude specific paths from redirection
        excluded_paths = ["/change-password", "/login", "/logout"]
        if request.path.rstrip("/") in excluded_paths:
            return self.get_response(request)

        # Check if employee is a new employee
        if hasattr(request, "user") and request.user.is_authenticated:
            if getattr(request.user, "is_new_employee", True):
                return redirect("change-password")  # Adjust to match your URL name

        return self.get_response(request)
