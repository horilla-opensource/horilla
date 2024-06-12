"""
middleware.py
"""

from django.apps import apps
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed

from base.context_processors import AllCompany
from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company


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
                "helpdesk",
                "offboarding",
                "horilla_documents",
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


class MethodNotAllowedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed):
            html_content = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Method Not Allowed</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f8f9fa;
                        color: #333;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        text-align: center;
                        background: #fff;
                        padding: 20px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    }
                    h1 {
                        font-size: 24px;
                        margin-bottom: 10px;
                    }
                    p {
                        font-size: 18px;
                        margin-bottom: 20px;
                    }
                    a {
                        color: #007bff;
                        text-decoration: none;
                        font-weight: bold;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>405 Method Not Allowed</h1>
                    <p>The request method is not allowed. Please make sure you are sending a proper request.</p>
                    <a href="/">Go Back to Home</a>
                </div>
            </body>
            </html>
            """
            return HttpResponse(html_content, content_type="text/html", status=405)
        return response
