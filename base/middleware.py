"""
middleware.py
"""
from django.apps import apps
from django.db.models import Q
from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from base.context_processors import AllCompany


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

            # for testing here only get recruitment models
            app_labels = [
                "recruitment",
                "employee",
                "onboarding",
                "attendance",
                "leave",
                "payroll",
                "asset",
                "pms",
                "base",
            ]
            app_models = [
                model
                for model in apps.get_models()
                if model._meta.app_label in app_labels
            ]
            # Add company filter to every query
            if company_id:
                for (
                    model
                ) in app_models:  # Replace YourModels with the actual models you have
                    if getattr(model, "company_id", None):
                        model.add_to_class(
                            "company_filter",
                            Q(company_id=company_id) | Q(company_id__isnull=True),
                        )
                    elif (
                        isinstance(model.objects, HorillaCompanyManager)
                        and model.objects.related_company_field
                    ):
                        model.add_to_class(
                            "company_filter",
                            Q(**{model.objects.related_company_field: company_id})
                            | Q(
                                **{
                                    f"{model.objects.related_company_field}__isnull": True
                                }
                            ),
                        )

        response = self.get_response(request)
        return response
