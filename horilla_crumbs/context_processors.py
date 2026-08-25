import re
import uuid
from urllib.parse import urlparse

from django.apps import apps
from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, path, resolve, reverse
from django.utils.translation import gettext as _trans
from django.utils.translation import gettext_lazy as _

from base.context_processors import white_labelling_company
from employee.models import Employee
from horilla.urls import urlpatterns

# Final path segment that looks like a file, e.g. "logo.png", "app.min.js.map".
_FILE_SEGMENT = re.compile(r"\.[A-Za-z0-9]{1,5}$")


def is_asset_request(request):
    """
    True for static/media or file URLs — these are not navigable pages.

    A missing asset 404s, and the 404 page still renders this processor, which
    would otherwise push path segments like "static / images / ui / xx.png"
    (or sourcemap probes such as "app.min.js.map") into the breadcrumb trail.
    """
    path_info = request.path
    for prefix in (settings.STATIC_URL, settings.MEDIA_URL):
        if prefix and path_info.startswith(prefix):
            return True
    last_segment = path_info.rstrip("/").rsplit("/", 1)[-1]
    return bool(_FILE_SEGMENT.search(last_segment))


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


def _resolve_menu_section(path, menus):
    """
    Find the top-level sidebar section (a MENU entry from some app's
    sidebar.py) that owns a submenu whose redirect matches the given path,
    either exactly or as a parent path (e.g. an employee detail page under
    the Employees list submenu). Returns (section_label, submenu_redirect)
    for the longest/most specific matching submenu, or None if nothing
    matches (e.g. settings pages, which aren't part of the main sidebar).
    """
    best = None
    for menu in menus or []:
        for submenu in menu.get("submenu", []):
            redirect = submenu.get("redirect") or ""
            if not redirect:
                continue
            if path == redirect or path.startswith(redirect):
                if best is None or len(redirect) > len(best[1]):
                    best = (str(menu.get("menu", "")), redirect)
    if best is not None:
        return best

    # No submenu redirect is a prefix of this path - typical for a detail
    # page reached from a list view rather than the list view's own URL
    # (e.g. project's "task-view/<id>" vs. its list page "project-view").
    # Fall back to matching on the shared leading URL segment so the page
    # still resolves to its app's own top-level menu label instead of
    # falling through to the raw path segment, which produces a second,
    # differently-cased duplicate of the same section in the breadcrumb.
    path_root = path.strip("/").split("/")[0] if path.strip("/") else ""
    if not path_root:
        return None
    for menu in menus or []:
        for submenu in menu.get("submenu", []):
            redirect = submenu.get("redirect") or ""
            redirect_root = redirect.strip("/").split("/")[0] if redirect else ""
            if redirect_root and redirect_root == path_root:
                return (str(menu.get("menu", "")), redirect)
    return None


BREADCRUMB_URL_NAMES = {
    "monthly-summary": _("Monthly Summary"),
    "ess": "Employee",
    "offboarding": "Offboarding",
    "helpdesk": "Helpdesk",
    "policies-discipline": "Policies & Discipline",
    "work-schedules": "Work Schedules",
    "requests": "Requests",
    "employee-settings-view": "Configuration",
    "recruitment-settings-view": "Configuration",
    "helpdesk-settings-view": "Configuration",
    "leave-settings-view": "Configuration",
    "payroll-settings-view": "Configuration",
    "performance-settings-view": "Configuration",
    "user-group-view": "Roles and Permissions",
    "employee-permission-assign": "Roles and Permissions",
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
    "monthly-summary",
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
    "default-export-access",
    "encashment-settings-view",
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
    "employee-settings-view",
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
            {
                "url": base_url,
                "name": company,
                "found": True,
                "clickable": True,
            }
        ]

    # Drop asset entries an earlier release may have stored in the session.
    cleaned = [
        crumb
        for crumb in request.session["breadcrumbs"]
        if not _FILE_SEGMENT.search(crumb.get("name", ""))
    ]
    if len(cleaned) != len(request.session["breadcrumbs"]):
        request.session["breadcrumbs"] = cleaned

    # An asset request must never extend the trail (see is_asset_request).
    if is_asset_request(request):
        return {"breadcrumbs": request.session["breadcrumbs"]}

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

        # Section-aware breadcrumb: instead of guessing the top-level label from
        # the raw first URL segment, look it up in the same sidebar MENU/SUBMENUS
        # registry that drives the actual left nav (see any app's sidebar.py).
        # The one exception is the main Dashboard: it isn't a "section" of its
        # own, so when the user actually came from there (via HTTP_REFERER,
        # rather than a one-off query marker) we show "Dashboard" instead of
        # whatever section the destination page belongs to.
        menus = getattr(request, "MENUS", None)
        if menus is None:
            try:
                from horilla.config import sidebar as _build_sidebar_menus

                _build_sidebar_menus(request)
                menus = getattr(request, "MENUS", [])
            except Exception:
                menus = []

        current_section = _resolve_menu_section(request.path, menus)

        section_override = None
        try:
            dashboard_path = reverse("dashboard")
        except Exception:
            dashboard_path = None

        referer = request.META.get("HTTP_REFERER")
        if referer and dashboard_path:
            referer_path = urlparse(referer).path
            if referer_path.rstrip("/") == dashboard_path.rstrip("/"):
                section_override = {"name": _trans("Dashboard"), "url": dashboard_path}

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
                # str() resolves any gettext_lazy() entries to a plain string
                # now, in the request's own active locale, since breadcrumbs
                # get JSON-serialized into the session (a lazy translation
                # proxy isn't JSON-serializable and would 500 the request).
                "name": str(BREADCRUMB_URL_NAMES.get(item, item)),
                "found": found,
                "clickable": clickable,
            }

            if i == 0:
                if section_override:
                    new_dict["name"] = section_override["name"]
                    new_dict["url"] = base_url.rstrip("/") + section_override["url"]
                    new_dict["found"] = True
                elif current_section:
                    new_dict["name"] = current_section[0]

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
