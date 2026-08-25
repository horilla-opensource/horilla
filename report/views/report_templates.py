import json

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from horilla.decorators import login_required
from report.models import ReportTemplate


def _visible_templates(request, report_slug):
    """Private (own) + company-shared + system templates for a report slug."""
    user = request.user
    qs = ReportTemplate.objects.filter(report_slug=report_slug).filter(
        Q(visibility=ReportTemplate.VISIBILITY_SYSTEM)
        | Q(visibility=ReportTemplate.VISIBILITY_COMPANY)
        | Q(created_by=user, visibility=ReportTemplate.VISIBILITY_PRIVATE)
        | Q(created_by=user)  # legacy rows without visibility awareness
    )
    return qs


@login_required
@require_http_methods(["GET"])
def list_report_templates(request):
    """
    List templates visible to the current user for a given report slug.
    Includes private, company-shared, and system layouts.
    """
    report_slug = request.GET.get("report_slug")
    templates = _visible_templates(request, report_slug).values(
        "id", "name", "visibility", "is_standard"
    )
    return JsonResponse({"templates": list(templates)})


@login_required
@require_http_methods(["POST"])
def save_report_template(request):
    """
    Save (or overwrite) a named template. Optional visibility: private|company.
    System templates cannot be overwritten by end users.
    """
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    report_slug = body.get("report_slug")
    name = (body.get("name") or "").strip()
    config = body.get("config")
    visibility = body.get("visibility") or ReportTemplate.VISIBILITY_PRIVATE
    if visibility not in (
        ReportTemplate.VISIBILITY_PRIVATE,
        ReportTemplate.VISIBILITY_COMPANY,
    ):
        visibility = ReportTemplate.VISIBILITY_PRIVATE

    if not report_slug or not name or config is None:
        messages.error(request, _("report_slug, name and config are all required."))
        return JsonResponse(
            {"error": "report_slug, name and config are all required."}, status=400
        )

    existing = ReportTemplate.objects.filter(
        report_slug=report_slug,
        name=name,
        created_by=request.user,
    ).first()
    if existing and existing.visibility == ReportTemplate.VISIBILITY_SYSTEM:
        return JsonResponse({"error": "Cannot overwrite system templates."}, status=403)

    template, _created = ReportTemplate.objects.update_or_create(
        report_slug=report_slug,
        name=name,
        created_by=request.user,
        defaults={"config": config, "visibility": visibility, "is_standard": False},
    )
    messages.success(request, _("Template saved."))
    return JsonResponse(
        {
            "id": template.id,
            "name": template.name,
            "visibility": template.visibility,
        }
    )


@login_required
@require_http_methods(["GET"])
def get_report_template(request, template_id):
    """
    Fetch a saved template's field arrangement so it can be re-applied to
    the pivot table.
    """
    template = (
        _visible_templates(request, request.GET.get("report_slug") or "")
        .filter(id=template_id)
        .first()
    )
    if not template:
        # Fallback: allow fetch by id if visible under any slug
        template = (
            ReportTemplate.objects.filter(id=template_id)
            .filter(
                Q(visibility=ReportTemplate.VISIBILITY_SYSTEM)
                | Q(visibility=ReportTemplate.VISIBILITY_COMPANY)
                | Q(created_by=request.user)
            )
            .first()
        )
    if not template:
        return JsonResponse({"error": "Template not found."}, status=404)
    return JsonResponse(
        {
            "id": template.id,
            "name": template.name,
            "config": template.config,
            "visibility": template.visibility,
            "is_standard": template.is_standard,
        }
    )


@login_required
@require_http_methods(["POST"])
def delete_report_template(request, template_id):
    template = (
        ReportTemplate.objects.filter(id=template_id, created_by=request.user)
        .exclude(visibility=ReportTemplate.VISIBILITY_SYSTEM)
        .first()
    )
    if not template:
        messages.error(request, _("Template not found."))
        return JsonResponse({"error": "Template not found."}, status=404)
    template.delete()
    messages.success(request, _("Template deleted."))
    return JsonResponse({"success": True})
