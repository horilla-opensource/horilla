"""
Company-scoped permission backend.

Replaces django.contrib.auth.backends.ModelBackend in AUTHENTICATION_BACKENDS.
While settings.COMPANY_SCOPED_PERMISSIONS is False this behaves exactly like
ModelBackend (global group permissions). When True, group permissions are
resolved from base.models.CompanyGroupAssignment for the company selected in
the current request (set by base.middleware.CompanyMiddleware into a
ContextVar before any view or template runs).

Resolution rules (flag on, non-superusers — superusers bypass backends):
- specific company selected  -> permissions from groups assigned for that company
- "all" / "All my companies" -> union of the user's per-company assignments
  (data layer still limits rows to those companies via HorillaCompanyManager)
- no company context (API/JWT without session, shells, schedulers)
                             -> user's work-info company; if none, the union
                                of all their per-company assignments

The union fallbacks never grant anything beyond what the user already holds
in at least one of their companies, so they cannot escalate privileges while
preventing accidental lockouts on session-less code paths.
"""

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission

from horilla.horilla_middlewares import _thread_locals, get_selected_company


class CompanyScopedBackend(ModelBackend):
    """ModelBackend with per-company group permission resolution."""

    def _get_group_permissions(self, user_obj):
        if not getattr(settings, "COMPANY_SCOPED_PERMISSIONS", False):
            return super()._get_group_permissions(user_obj)

        company_id = self._resolve_company_id(user_obj)
        assignments = user_obj.company_group_assignments.all()
        if company_id is not None:
            assignments = assignments.filter(company_id=company_id)
        return Permission.objects.filter(
            group__company_assignments__in=assignments
        ).distinct()

    @staticmethod
    def _resolve_company_id(user_obj):
        """
        Return the company id to scope permissions to, or None for
        "union of the user's assigned companies".
        """
        company = get_selected_company()
        if company and company != "all":
            return company
        if company == "all":
            return None
        # No request context: prefer the user's work-info company.
        try:
            work_info_company_id = (
                user_obj.employee_get.employee_work_info.company_id_id
            )
        except Exception:
            work_info_company_id = None
        return work_info_company_id


def company_scoped_active():
    """True when per-company permission scoping is enabled."""
    return bool(getattr(settings, "COMPANY_SCOPED_PERMISSIONS", False))


def get_assigned_company_ids(user):
    """
    Companies where the user holds a CompanyGroupAssignment (role grant).
    Used for All-my-companies data scope and permission unions.
    """
    from base.models import CompanyGroupAssignment

    return set(
        CompanyGroupAssignment.objects.filter(user=user).values_list(
            "company_id", flat=True
        )
    )


def get_allowed_company_ids(user):
    """
    Companies the user may select in the switcher: assignment companies
    plus their work-info company (so they can return to their home company
    even when they only hold a role elsewhere).
    """
    ids = get_assigned_company_ids(user)
    try:
        work_company_id = user.employee_get.employee_work_info.company_id_id
        if work_company_id:
            ids.add(work_company_id)
    except Exception:
        pass
    return ids


def get_write_company_id(user):
    """
    Company to stamp on new records when the session is "All my companies".

    Prefers the user's work-info company when it is an *assignment* company;
    otherwise the first assigned company. Falls back to allowed (work) only
    if they have no assignments.
    """
    assigned = get_assigned_company_ids(user)
    pool = assigned or get_allowed_company_ids(user)
    if not pool:
        return None
    try:
        work_company_id = user.employee_get.employee_work_info.company_id_id
        if work_company_id in pool:
            return work_company_id
    except Exception:
        pass
    return sorted(pool)[0]


def resolve_company_id_for_new_record(request=None):
    """
    Concrete company id for creating/saving rows.

    - Specific company selected -> that id
    - Superuser on "all" -> None (leave unset / form chooses)
    - Non-superuser on "all" -> write company (work-info or first allowed)
    """
    request = request or getattr(_thread_locals, "request", None)
    company = get_selected_company()
    if company and company != "all":
        try:
            return int(company)
        except (TypeError, ValueError):
            return company
    if not request or not getattr(request, "user", None):
        return None
    if not request.user.is_authenticated or request.user.is_superuser:
        return None
    if company_scoped_active():
        return get_write_company_id(request.user)
    return None


def stamp_company_on_create(instance, attr="company_id"):
    """
    If ``instance`` is new and ``attr`` is unset, assign the company from
    ``resolve_company_id_for_new_record`` (supports All my companies writes).

    Returns True when a company was stamped.
    """
    if getattr(instance, "pk", None):
        return False
    fk_id_attr = f"{attr}_id"
    if getattr(instance, fk_id_attr, None):
        return False
    company_id = resolve_company_id_for_new_record()
    if not company_id:
        return False
    from base.models import Company

    company = Company.find(company_id)
    if not company:
        return False
    setattr(instance, attr, company)
    return True


def _normalize_company_id(company_id=None):
    """
    Resolve company id for permission/group display.

    None  -> current selected company from context
    "all" -> None (union of assignment companies)
    int/str id -> that company
    """
    if company_id is None:
        company_id = get_selected_company()
    if company_id in (None, "", "all"):
        return None
    try:
        return int(company_id)
    except (TypeError, ValueError):
        return company_id


def get_user_groups_for_company(user, company_id=None):
    """
    Groups the user holds via CompanyGroupAssignment for ``company_id``.

    When company scoping is off, returns ``user.groups``.
    When ``company_id`` is None/"all", returns the union of all assignment groups.
    """
    from django.contrib.auth.models import Group

    if not user:
        return Group.objects.none()
    if not company_scoped_active():
        return user.groups.all()

    company_id = _normalize_company_id(company_id)
    assignments = user.company_group_assignments.all()
    if company_id is not None:
        assignments = assignments.filter(company_id=company_id)
    return Group.objects.filter(
        id__in=assignments.values_list("group_id", flat=True)
    ).distinct()


def get_effective_permission_codenames(user, company_id=None, include_direct=True):
    """
    Codenames the user effectively has for a company.

    - Direct ``user_permissions`` are included when ``include_direct`` (global).
    - Group permissions come from CompanyGroupAssignment for that company
      (or the union when company is "all"/None).
    """
    if not user:
        return []

    codenames = set()
    if include_direct:
        codenames.update(user.user_permissions.values_list("codename", flat=True))

    if not company_scoped_active():
        codenames.update(
            Permission.objects.filter(group__user=user).values_list(
                "codename", flat=True
            )
        )
        return sorted(codenames)

    company_id = _normalize_company_id(company_id)
    assignments = user.company_group_assignments.all()
    if company_id is not None:
        assignments = assignments.filter(company_id=company_id)
    codenames.update(
        Permission.objects.filter(
            group__company_assignments__in=assignments
        ).values_list("codename", flat=True)
    )
    return sorted(set(codenames))


def get_permission_company_label(company_id=None):
    """Human-readable label for the company used in permission display."""
    from base.models import Company

    company_id = _normalize_company_id(company_id)
    if company_id is None:
        selected = get_selected_company()
        if selected == "all":
            return "All my companies"
        return None
    company = Company.objects.filter(id=company_id).first()
    return company.company if company else None
