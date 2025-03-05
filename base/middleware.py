"""
middleware.py
"""

from django.apps import apps
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import redirect

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

CACHE_KEY = "horilla_company_models_cache_key"


class CompanyMiddleware:
    """
    Middleware to handle company-specific filtering for models.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_company_id(self, request):
        """
        Retrieve the company ID from the request or session.
        """
        if getattr(request, "user", False) and not request.user.is_anonymous:
            try:
                if com_id := request.session.get("selected_company", None):
                    return (
                        Company.objects.filter(id=com_id).first()
                        if com_id != "all"
                        else None
                    )
                else:
                    return getattr(
                        request.user.employee_get.employee_work_info, "company_id", None
                    )
            except AttributeError:
                pass
        return None

    def _set_company_session(self, request, company_id):
        """
        Set the company session data based on the company ID.
        """
        if company_id and request.session.get("selected_company") != "all":
            request.session["selected_company"] = str(company_id.id)
            request.session["selected_company_instance"] = {
                "company": company_id.company,
                "icon": company_id.icon.url,
                "text": "My company",
                "id": company_id.id,
            }
        else:
            request.session["selected_company"] = "all"
            all_company = AllCompany()
            request.session["selected_company_instance"] = {
                "company": all_company.company,
                "icon": all_company.icon.url,
                "text": all_company.text,
                "id": all_company.id,
            }

    def _add_company_filter(self, model, company_id):
        """
        Add company filter to the model if applicable.
        """
        is_company_model = model in self._get_company_models()
        company_field = getattr(model, "company_id", None)
        is_horilla_manager = isinstance(model.objects, HorillaCompanyManager)
        related_company_field = getattr(model.objects, "related_company_field", None)

        if is_company_model:
            if company_field:
                model.add_to_class("company_filter", Q(company_id=company_id))
            elif is_horilla_manager and related_company_field:
                model.add_to_class(
                    "company_filter", Q(**{related_company_field: company_id})
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

    def _get_company_models(self):
        """
        Retrieve the list of models that are company-specific.
        """
        company_models = cache.get(CACHE_KEY)

        if company_models is None:
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
                ],
                "helpdesk": ["ticket"],
                "offboarding": ["offboarding"],
                "pms": ["employeeobjective"],
            }

            for app_label, models in app_model_mappings.items():
                if apps.is_installed(app_label):
                    company_models.extend(
                        [get_horilla_model_class(app_label, model) for model in models]
                    )

            cache.set(CACHE_KEY, company_models)

        return company_models

    def __call__(self, request):
        if getattr(request, "user", False) and not request.user.is_anonymous:
            company_id = self._get_company_id(request)
            self._set_company_session(request, company_id)

            app_models = [
                model for model in apps.get_models() if model._meta.app_label in APPS
            ]
            for model in app_models:
                self._add_company_filter(model, company_id)

        response = self.get_response(request)
        return response


class ForcePasswordChangeMiddleware:
    """
    Middleware to force password change for new employees.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        excluded_paths = ["/change-password", "/login", "/logout"]
        if request.path.rstrip("/") in excluded_paths:
            return self.get_response(request)

        if hasattr(request, "user") and request.user.is_authenticated:
            if getattr(request.user, "is_new_employee", True):
                return redirect("change-password")

        return self.get_response(request)
