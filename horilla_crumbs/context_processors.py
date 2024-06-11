from urllib.parse import urlparse

from django.shortcuts import redirect
from django.urls import Resolver404, path, resolve, reverse

from employee.models import Employee
from horilla.urls import urlpatterns
from recruitment.models import Candidate


def _split_path(self, path=None):
    """Returns a list of the path components between slashes"""
    if not path:
        path = self.path
    if path.endswith("/"):
        path = path[:-1]
    if path.startswith("/"):
        path = path[1:]
    if path == "":
        return list()

    result = path.split("/")
    return result


sidebar_urls = [
    "dashboard",
    "pipeline",
    "recruitment-survey-question-template-view",
    "candidate-view",
    "recruitment-view",
    "stage-view",
    "view-onboarding-dashboard",
    "onboarding-view",
    "candidates-view",
    "employee-profile",
    "employee-view",
    "shift-request-view",
    "work-type-request-view",
    "rotating-shift-assign",
    "rotating-work-type-assign",
    "view-payroll-dashboard",
    "view-contract",
    "view-allowance",
    "view-deduction",
    "view-payslip",
    "filing-status-view",
    "attendance-view",
    "work-records",
    "request-attendance-view",
    "attendance-overtime-view",
    "attendance-activity-view",
    "late-come-early-out-view",
    "view-my-attendance",
    "leave-dashboard",
    "leave-employee-dashboard",
    "user-leave",
    "user-request-view",
    "leave-allocation-request-view",
    "type-view",
    "assign-view",
    "request-view",
    "holiday-view",
    "company-leave-view",
    "dashboard-view",
    "objective-list-view",
    "feedback-view",
    "period-view",
    "question-template-view",
    "asset-category-view",
    "asset-request-allocation-view",
    "settings",
    "attendance-settings",
    "employee-permission-assign",
    "user-group-assign",
    "currency",
    "department-view",
    "job-position-view",
    "job-role-view",
    "work-type-view",
    "rotating-work-type-view",
    "employee-type-view",
    "employee-shift-view",
    "employee-shift-schedule-view",
    "rotating-shift-view",
    "attendance-settings-view",
    "user-group-view",
    "company-view",
    "document-request-view",
    "faq-category-view",
    "ticket-view",
    "tag-view",
    "ticket-type-view",
    "mail-server-conf",
    "multiple-approval-condition",
    "skill-zone-view",
    "view-mail-templates",
    "view-loan",
    "view-reimbursement",
    "department-manager-view",
    "date-settings",
    "offboarding-pipeline",
    "pagination-settings-view",
    "organisation-chart",
    "disciplinary-actions",
    "view-policies",
    "resignation-requests-view",
    "action-type",
    "general-settings",
    "view-biometric-devices",
    "employee-tag-view",
    "grace-settings-view",
    "helpdesk-tag-view",
    "restrict-view",
    "asset-history",
    "view-key-result",
    "view-meetings",
    "interview-view",
    "view-compensatory-leave",
    "compensatory-leave-settings-view",
]
remove_urls = [
    "feedback-detailed-view",
    "question-template-detailed-view",
    "employee-view-new",
]

user_breadcrumbs = {}


def breadcrumbs(request):
    base_url = request.build_absolute_uri("/")
    user_id = str(request.user)

    if user_id not in user_breadcrumbs:
        user_breadcrumbs[user_id] = [
            {"url": base_url, "name": "Horilla", "found": True}
        ]

    try:
        user_breadcrumb = user_breadcrumbs[user_id]

        parts = _split_path(request)
        path = base_url

        candidates = Candidate.objects.filter(is_active=True)
        employees = Employee.objects.all()

        if len(parts) > 1:

            if "recruitment" in parts:
                if "search-candidate" in parts:
                    pass
                elif "candidate-view" in parts:
                    pass
                elif "get-mail-log-rec" in parts:
                    pass
                else:
                    # Store the candidates in the session
                    request.session["filtered_candidates"] = [
                        candidate.id for candidate in candidates
                    ]

            if "employee-filter-view" in parts:
                pass
            elif "employee-view" in parts:
                pass
            elif "view-penalties" in parts:
                pass
            elif parts[0] == "employee" and parts[-1].isdigit():
                pass
            else:
                # Store the employees in the session
                request.session["filtered_employees"] = [
                    employee.id for employee in employees
                ]

        if len(parts) == 0:
            user_breadcrumbs[user_id].clear()
            user_breadcrumb.append({"url": base_url, "name": "Horilla", "found": True})

        if len(parts) > 1:
            last_path = parts[-1]
            if (
                last_path in sidebar_urls
                or parts[-2] == "employee-view"
                or parts[-2] == "candidate-view"
            ):
                breadcrumbs = user_breadcrumbs[user_id]
                first_path = breadcrumbs[0]
                user_breadcrumbs[user_id].clear()
                user_breadcrumbs[user_id].append(first_path)
        for i, item in enumerate(parts):
            path = path + item + "/"
            parsed_url = urlparse(path)
            check_path = parsed_url.path
            try:
                resolver_match = resolve(check_path)
                found = True
            except Resolver404 as e:
                found = False

            new_dict = {"url": path, "name": item, "found": found}

            if item.isdigit():
                # Handle the case when item is a digit (e.g., an ID)
                current_url = resolve(request.path_info)
                url_kwargs = current_url.kwargs
                model_value = url_kwargs.get("model")

                if model_value:
                    try:
                        object = model_value.objects.get(id=item)
                        new_dict["name"] = str(object)
                    except:
                        pass

            key = "HTTP_HX_REQUEST"
            if (
                new_dict not in user_breadcrumb
                and new_dict["name"] not in remove_urls
                and key not in request.META.keys()
                and not new_dict["name"].isdigit()
            ):
                user_breadcrumb.append(new_dict)

        user_breadcrumbs[user_id] = user_breadcrumb

    except Exception as e:
        user_breadcrumb[user_id].clear()
        user_breadcrumbs[user_id] = [
            {"url": base_url, "name": "Horilla", "found": True}
        ]
    return {"breadcrumbs": user_breadcrumbs[user_id]}


urlpatterns.append(
    path("recruitment/", lambda request: redirect("recruitment-dashboard"))
)
urlpatterns.append(
    path("onboarding/", lambda request: redirect("view-onboarding-dashboard"))
)
urlpatterns.append(path("employee/", lambda request: redirect("employee-view")))
urlpatterns.append(
    path("attendance/", lambda request: redirect("attendance-dashboard"))
)
urlpatterns.append(
    path(
        "leave/",
        lambda request: redirect(
            reverse("leave-employee-dashboard") + "?dashboard=true"
        ),
    )
)
urlpatterns.append(path("payroll/", lambda request: redirect("view-payroll-dashboard")))
urlpatterns.append(path("pms/", lambda request: redirect("dashboard-view")))
