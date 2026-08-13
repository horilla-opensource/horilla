"""CRUD for named Standard-Reports saved views (catalog sidebar collections)."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from horilla.decorators import login_required
from report.models import ReportSavedView
from report.personalization import saved_views_for_user, session_company_id


def _parse_json_body(request) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _serialize(view: ReportSavedView) -> dict:
    return {"id": view.id, "name": view.name, "report_slugs": view.report_slugs or []}


def _owned_views(request):
    return ReportSavedView.objects.filter(owner=request.user, is_active=True)


@login_required
@require_http_methods(["GET", "POST"])
def report_saved_views(request):
    if request.method == "GET":
        return JsonResponse(
            {"views": [_serialize(v) for v in saved_views_for_user(request)]}
        )

    body = _parse_json_body(request)
    name = (body.get("name") or "").strip()
    slugs = body.get("report_slugs") or []
    if not name:
        return JsonResponse({"error": _("View name is required.")}, status=400)
    if not isinstance(slugs, list):
        return JsonResponse({"error": _("Invalid report list.")}, status=400)

    company_id = session_company_id(request)
    if _owned_views(request).filter(name=name, company_id_id=company_id).exists():
        return JsonResponse(
            {"error": _("You already have a saved view with that name.")}, status=400
        )

    view = ReportSavedView.objects.create(
        name=name,
        report_slugs=slugs,
        owner=request.user,
        company_id_id=company_id,
    )
    return JsonResponse(
        {
            "ok": True,
            "view": _serialize(view),
            "views": [_serialize(v) for v in saved_views_for_user(request)],
        }
    )


@login_required
@require_http_methods(["POST"])
def report_saved_view_add_reports(request, view_id):
    view = get_object_or_404(_owned_views(request), pk=view_id)
    body = _parse_json_body(request)
    slugs = body.get("report_slugs") or []
    if not isinstance(slugs, list):
        return JsonResponse({"error": _("Invalid report list.")}, status=400)
    view.add_slugs(slugs)
    return JsonResponse({"ok": True, "view": _serialize(view)})


@login_required
@require_http_methods(["POST", "DELETE"])
def report_saved_view_remove_report(request, view_id, slug):
    view = get_object_or_404(_owned_views(request), pk=view_id)
    view.remove_slug(slug)
    return JsonResponse({"ok": True, "view": _serialize(view)})


@login_required
@require_http_methods(["POST", "DELETE"])
def report_saved_view_delete(request, view_id):
    view = get_object_or_404(_owned_views(request), pk=view_id)
    view.delete()
    return JsonResponse(
        {"ok": True, "views": [_serialize(v) for v in saved_views_for_user(request)]}
    )
