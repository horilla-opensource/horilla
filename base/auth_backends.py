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
- no company context (API/JWT without session, shells, schedulers)
                             -> user's work-info company; if none, the union
                                of all their per-company assignments
- "all companies" selected   -> union of the user's per-company assignments
                                (defense in depth; the switcher restricts
                                "all" to superusers)

The union fallbacks never grant anything beyond what the user already holds
in at least one of their companies, so they cannot escalate privileges while
preventing accidental lockouts on session-less code paths.
"""

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission

from horilla.horilla_middlewares import get_selected_company


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


def get_allowed_company_ids(user):
    """
    Companies a user may select: any company where they hold a group
    assignment, plus their work-info company.
    """
    from base.models import CompanyGroupAssignment

    ids = set(
        CompanyGroupAssignment.objects.filter(user=user).values_list(
            "company_id", flat=True
        )
    )
    try:
        work_company_id = user.employee_get.employee_work_info.company_id_id
        if work_company_id:
            ids.add(work_company_id)
    except Exception:
        pass
    return ids
