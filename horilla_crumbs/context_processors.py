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

    path = path or self.path
    path = path.strip("/")
    parts = path.split("/") if path else []

    if parts and parts[0] in ("static", "media"):
        return []

    return parts


BREADCRUMB_URL_NAMES = {
    "ess": "Employee",
    "offboarding": "Offboarding",
    "helpdesk": "Helpdesk",
    "policies-discipline": "Policies & Discipline",
    "work-schedules": "Work Schedules",
    "requests": "Work Requests",
    "work-structure": "Work Structure",
    "recruitment-settings-view": "Configuration",
    "helpdesk-settings-view": "Configuration",
    "leave-settings-view": "Configuration",
    "payroll-settings-view": "Configuration",
    "performance-settings-view": "Configuration",
}

sidebar_urls = [
    "dashboard",
    "ess",
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
    "asset-category-view",
    "asset-request-allocation-view",
    "settings",
    "attendance-settings",
    "geo-face-config",
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
    "audit-history-view",
    "ticket-type-view",
    "mail-server-conf",
    "mail-templates-view",
    "multiple-approval-condition",
    "multiple-approval-rules-view",
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
    "roster",
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
    "mail-automations-view",
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
    "task-all",
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
    "linkedin-integration-setting",
    "ldap-settings",
    "gmeet-setting",
    "whatsapp-credential-view",
    "cbv-pipeline",
    "gmeet-view",
    "color-theme-view",
    "survey-template-preview",
    "system-preferences-view",
    "attendance-rule-view",
    "leave-rules-view",
    "restrict-leaves-view",
    "holidays-view",
    "company-leaves-view",
    "offboarding-rules-view",
    "grace-time-view",
    "audit-history",
    "policies-discipline",
    "work-schedules",
    "requests",
    "work-structure",
    "recruitment-settings-view",
    "helpdesk-settings-view",
    "leave-settings-view",
    "payroll-settings-view",
    "performance-settings-view",
    "tours",
    "templates-periods",
]
remove_urls = [
    "feedback-detailed-view",
    "question-template-detailed-view",
    "employee-view-new",
    "objective-detailed-view",
    "ticket-detail",
    "faq-view",
    "get-job-positions",
    "task-view",
    "dashboard",
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

        if len(parts) == 1 and parts[0] in sidebar_urls:
            first_path = breadcrumbs[0]
            request.session["breadcrumbs"].clear()
            request.session["breadcrumbs"].append(first_path)

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

            clickable = True
            if found and not request.user.is_superuser:
                view_func = resolver_match.func
                required_perms = getattr(view_func, "_required_perms", [])
                if not required_perms:
                    redirect_to = getattr(view_func, "_redirect_to", None)
                    if redirect_to:
                        try:
                            dest_path = reverse(redirect_to)
                            dest_match = resolve(dest_path)
                            required_perms = getattr(
                                dest_match.func, "_required_perms", []
                            )
                        except Exception:
                            pass
                if required_perms:
                    clickable = all(request.user.has_perm(p) for p in required_perms)

            new_dict = {
                "url": path,
                "name": BREADCRUMB_URL_NAMES.get(item, item),
                "found": found,
                "clickable": clickable,
            }

            if item == "attendance":
                from base.templatetags.basefilters import is_reportingmanager

                new_dict["clickable"] = (
                    request.user.is_superuser
                    or request.user.has_perm("attendance.view_attendance")
                    or is_reportingmanager(request.user)
                )

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
            sidebar_nav_key = "HTTP_HX_SIDEBAR_NAV"
            names = [d["name"] for d in breadcrumbs]
            if (
                new_dict not in breadcrumbs
                and new_dict["name"] not in remove_urls + names
                and (
                    key not in request.META.keys()
                    or request.META.get(sidebar_nav_key) == "true"
                )
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


def _section_redirect(url_name):
    """Return a named redirect view that stores its destination for breadcrumb permission checks."""

    def _redirect(request):
        return redirect(url_name)

    _redirect._redirect_to = url_name
    return _redirect


def _leave_redirect(request):
    return redirect(reverse("leave-employee-dashboard") + "?dashboard=true")


def _attendance_redirect(request):
    from base.templatetags.basefilters import is_reportingmanager

    if (
        request.user.is_superuser
        or request.user.has_perm("attendance.view_attendance")
        or is_reportingmanager(request.user)
    ):
        return redirect("attendance-dashboard")
    return redirect("attendance-view")


urlpatterns.append(path("recruitment/", _section_redirect("recruitment-dashboard")))
urlpatterns.append(
    path("onboarding/", _section_redirect("onboarding-modern-dashboard"))
)
urlpatterns.append(path("employee/", _section_redirect("ess-dashboard")))
urlpatterns.append(path("attendance/", _attendance_redirect))
urlpatterns.append(path("leave/", _leave_redirect))
urlpatterns.append(path("payroll/", _section_redirect("view-payroll-dashboard")))
urlpatterns.append(path("pms/", _section_redirect("dashboard-view")))
urlpatterns.append(path("asset/", _section_redirect("asset-dashboard")))
urlpatterns.append(path("project/", _section_redirect("project-dashboard-view")))
urlpatterns.append(path("helpdesk/", _section_redirect("helpdesk-dashboard")))
