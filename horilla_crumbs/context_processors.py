import uuid
from urllib.parse import urlparse

from django.apps import apps
from django.shortcuts import redirect
from django.urls import Resolver404, path, resolve, reverse

from base.context_processors import white_labelling_company
from employee.models import Employee
from horilla.urls import urlpatterns


def is_valid_uuid(uuid_string):
    try:
        uuid.UUID(uuid_string, version=4)
        return True
    except ValueError:
        return False


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
    "project-dashboard-view",
    "project-view",
    "view-time-sheet",
    "templates",
    "sidebar.html",
    "objective-detailed-view",
    "mail-automations",
    "faq-view",
    "auto-payslip-settings-view",
    "bonus-point-setting",
    "employee-past-leave-restriction",
    "track-late-come-early-out",
    "enable-biometric-attendance",
    "allowed-ips",
    "self-tracking-feature",
    "candidate-reject-reasons",
    "skills-view",
    "employee-bonus-point",
    "mail-automations",
    "check-in-check-out-setting",
    "user-accessibility",
    "asset-batch-view",
    "task-all",
    "gdrive",
    "color-settings",
    "employee-report",
    "employee-pivot",
    "recruitment-report",
    "recruitment-pivot",
    "attendance-report",
    "attendance-pivot",
    "leave-report",
    "leave-pivot",
    "payroll-report",
    "payroll-pivot",
    "asset-report",
    "asset-pivot",
    "pms-report",
    "pms-pivot",
]
remove_urls = [
    "feedback-detailed-view",
    "question-template-detailed-view",
    "employee-view-new",
    "objective-detailed-view",
    "ticket-detail",
    "faq-view",
    "get-job-positions",
]

user_breadcrumbs = {}


def breadcrumbs(request):
    base_url = request.build_absolute_uri("/")
    company = white_labelling_company(request)["white_label_company_name"]

    # Initialize breadcrumbs in the session if not already present
    if "breadcrumbs" not in request.session:
        request.session["breadcrumbs"] = [
            {"url": base_url, "name": company, "found": True}
        ]

    try:
        breadcrumbs = request.session["breadcrumbs"]

        qs = request.META.get("QUERY_STRING", "")
        pairs = qs.split("&")
        filtered_pairs = [pair for pair in pairs if "=" in pair and pair.split("=")[1]]
        filtered_query_string = "&".join(filtered_pairs)
        emp_query_string = None

        for item in breadcrumbs:
            if item["name"] in ["employee-view", "candidate-view"]:
                items = item["url"].split("?", 1)
                if len(items) > 1:
                    emp_query_string = items[1]
                    break

        parts = _split_path(request)
        path = base_url

        if apps.is_installed("recruitment"):
            from recruitment.models import Candidate

            candidates = Candidate.objects.filter(is_active=True)

        else:
            candidates = None

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
            request.session["breadcrumbs"].clear()
            breadcrumbs.append({"url": base_url, "name": company, "found": True})

        if len(parts) > 1:
            last_path = parts[-1]
            if (
                last_path in sidebar_urls
                or parts[-2] == "employee-view"
                or parts[-2] == "candidate-view"
                or parts[-2] == "view-payslip"
            ):
                first_path = breadcrumbs[0]
                request.session["breadcrumbs"].clear()
                request.session["breadcrumbs"].append(first_path)
        for i, item in enumerate(parts):
            path = path + item + "/"
            parsed_url = urlparse(path)
            check_path = parsed_url.path
            try:
                resolver_match = resolve(check_path)
                found = True
            except Resolver404:
                found = False

            new_dict = {"url": path, "name": item, "found": found}

            if item.isdigit() or is_valid_uuid(item):
                # Handle the case when item is a digit (e.g., an ID)
                current_url = resolve(request.path_info)
                url_kwargs = current_url.kwargs
                model_value = url_kwargs.get("model")

                if model_value:
                    try:
                        obj = model_value.objects.get(id=item)  # completed
                        new_dict["name"] = str(obj)
                    except:
                        pass

            key = "HTTP_HX_REQUEST"
            names = [d["name"] for d in breadcrumbs]
            if (
                new_dict not in breadcrumbs
                and new_dict["name"] not in remove_urls + names
                and key not in request.META.keys()
                and not new_dict["name"].isdigit()
            ):
                if new_dict["name"] in ["employee-view", "candidate-view"]:
                    new_dict["url"] = f'{new_dict["url"]}?{emp_query_string}'

                breadcrumbs.append(new_dict)

        try:
            prev_url = breadcrumbs[-1]
            prev_url["url"] = prev_url["url"].split("?")[0]
            if filtered_query_string:
                prev_url["url"] = f'{prev_url["url"]}?{filtered_query_string}'
            else:
                prev_url["url"] = f'{prev_url["url"]}'
        except:
            pass

        request.session["breadcrumbs"] = breadcrumbs

    except Exception as e:
        request.session["breadcrumbs"] = [
            {"url": base_url, "name": company, "found": True}
        ]
    return {"breadcrumbs": request.session["breadcrumbs"]}


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
urlpatterns.append(path("asset/", lambda request: redirect("asset-dashboard")))
urlpatterns.append(path("project/", lambda request: redirect("project-dashboard-view")))
