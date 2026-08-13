"""
Access matrix helpers for standard reports (Phase 5).

Empty matrix → fall back to ReportDefinition.permission / has_export_access.
Matching matrix rows gate view / export / subscribe.
"""

from __future__ import annotations

from typing import Optional

from django.apps import apps
from django.db.models import Q

from base.methods import has_export_access
from report.models import ReportAccess
from report.personalization import session_company_id
from report.registry import ReportDefinition


def _user_group_ids(user) -> set[int]:
    if not user or not user.is_authenticated:
        return set()
    try:
        return set(user.groups.values_list("id", flat=True))
    except Exception:
        return set()


def _rule_matches_report(rule: ReportAccess, slug: str, domain: str) -> bool:
    slug = slug or ""
    domain = domain or ""
    rule_slug = (rule.report_slug or "").strip()
    rule_domain = (rule.domain or "").strip()
    if rule_slug:
        return rule_slug == slug
    if rule_domain:
        return rule_domain == domain
    # Both blank → global rule
    return True


def _rule_applies_to_user(rule: ReportAccess, user) -> bool:
    if rule.group_id:
        if rule.group_id not in _user_group_ids(user):
            return False
    perm = (rule.permission or "").strip()
    if perm and not user.has_perm(perm):
        return False
    return True


def matching_access_rules(
    user,
    definition: ReportDefinition,
    company_id: Optional[int] = None,
) -> list[ReportAccess]:
    """Return active matrix rows that apply to this user + report."""
    if not user or not user.is_authenticated:
        return []

    qs = ReportAccess.objects.filter(is_active=True)
    if company_id is not None:
        qs = qs.filter(Q(company_id_id=company_id) | Q(company_id__isnull=True))
    else:
        qs = qs.filter(company_id__isnull=True)

    # Prefetch candidates that could match slug or domain or global
    qs = qs.filter(
        Q(report_slug=definition.slug)
        | Q(report_slug="", domain=definition.domain)
        | Q(report_slug="", domain="")
    ).select_related("group")

    matched = []
    for rule in qs:
        if not _rule_matches_report(rule, definition.slug, definition.domain):
            continue
        if not _rule_applies_to_user(rule, user):
            continue
        matched.append(rule)
    return matched


def _matrix_allows(rules: list[ReportAccess], flag: str) -> Optional[bool]:
    """
    None → no matrix opinion (caller should fallback).
    True/False → matrix decision.
    """
    if not rules:
        return None
    return any(bool(getattr(rule, flag, False)) for rule in rules)


def user_can_view_report(
    user,
    definition: ReportDefinition,
    *,
    company_id: Optional[int] = None,
) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    decision = _matrix_allows(
        matching_access_rules(user, definition, company_id), "can_view"
    )
    if decision is not None:
        return decision
    return definition.user_has_permission(user)


def user_can_export_report(
    user,
    definition: ReportDefinition,
    *,
    request=None,
    company_id: Optional[int] = None,
) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user_can_view_report(user, definition, company_id=company_id):
        return False

    decision = _matrix_allows(
        matching_access_rules(user, definition, company_id), "can_export"
    )
    if decision is False:
        return False

    # Fallback / additional gate: model export permission when configured
    if definition.export_model and request is not None:
        try:
            app_label, model_name = definition.export_model.split(".")
            model = apps.get_model(app_label, model_name)
            if not has_export_access(request, model):
                return False
        except (ValueError, LookupError):
            pass
    elif decision is None and definition.export_model and request is None:
        # No request (scheduler) — rely on matrix or view perm already checked
        pass

    if decision is True:
        return True
    # No matrix export opinion: allow if they can view (export model gate above)
    return True


def user_can_subscribe_report(
    user,
    definition: ReportDefinition,
    *,
    company_id: Optional[int] = None,
) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user_can_view_report(user, definition, company_id=company_id):
        return False
    decision = _matrix_allows(
        matching_access_rules(user, definition, company_id), "can_subscribe"
    )
    if decision is not None:
        return decision
    return True


def company_id_from_request(request) -> Optional[int]:
    return session_company_id(request) if request is not None else None
