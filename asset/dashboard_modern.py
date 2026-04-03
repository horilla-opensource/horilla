"""
Modern asset dashboard views — KPI summary + ApexCharts.

Accessible at /asset/dashboard/modern/ alongside the existing dashboard.
"""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render


def _parse_period(request):
    """Parse from_date and to_date from GET params. Defaults to current month."""
    today = date.today()
    from_str = request.GET.get("from_date")
    to_str = request.GET.get("to_date")
    try:
        from_date = date.fromisoformat(from_str) if from_str else today.replace(day=1)
    except (ValueError, TypeError):
        from_date = today.replace(day=1)
    try:
        to_date = date.fromisoformat(to_str) if to_str else today
    except (ValueError, TypeError):
        to_date = today
    return from_date, to_date


@login_required
def modern_asset_dashboard(request):
    """Render the modern asset dashboard page."""
    return render(request, "asset/dashboard_modern.html")


@login_required
def asset_kpi_data(request):
    """Return asset KPI summary data as JSON."""
    from asset.models import Asset, AssetAssignment, AssetRequest

    total_assets = Asset.objects.all().count()
    in_use = Asset.objects.filter(asset_status="In use").count()
    available = Asset.objects.filter(asset_status="Available").count()
    not_available = Asset.objects.filter(asset_status="Not-Available").count()

    pending_requests = AssetRequest.objects.filter(
        asset_request_status="Requested",
        requested_employee_id__is_active=True,
    ).count()

    total_value = Asset.objects.aggregate(
        total=Coalesce(Sum("asset_purchase_cost"), 0, output_field=DecimalField())
    )["total"]

    # Expiring soon (next 30 days)
    today = date.today()
    expiring_soon = Asset.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=30),
    ).count()

    # Return requests pending
    return_requests = AssetAssignment.objects.filter(
        return_request=True,
        return_status__isnull=True,
    ).count()

    return JsonResponse(
        {
            "total_assets": total_assets,
            "in_use": in_use,
            "available": available,
            "not_available": not_available,
            "pending_requests": pending_requests,
            "total_value": float(total_value),
            "expiring_soon": expiring_soon,
            "return_requests": return_requests,
        }
    )


@login_required
def asset_status_distribution(request):
    """Asset count by status."""
    from asset.models import Asset

    statuses = [
        {
            "status": "In use",
            "label": "In Use",
            "count": Asset.objects.filter(asset_status="In use").count(),
        },
        {
            "status": "Available",
            "label": "Available",
            "count": Asset.objects.filter(asset_status="Available").count(),
        },
        {
            "status": "Not-Available",
            "label": "Not Available",
            "count": Asset.objects.filter(asset_status="Not-Available").count(),
        },
    ]

    return JsonResponse({"statuses": statuses})


@login_required
def asset_by_category(request):
    """Asset count by category with in-use breakdown."""
    from asset.models import Asset

    categories = []

    try:
        data = (
            Asset.objects.all()
            .values("asset_category_id__asset_category_name")
            .annotate(
                total=Count("id"),
                in_use=Count("id", filter=Q(asset_status="In use")),
                available_count=Count("id", filter=Q(asset_status="Available")),
            )
            .order_by("-total")
        )

        for item in data:
            cat = item["asset_category_id__asset_category_name"]
            if cat:
                categories.append(
                    {
                        "category": cat,
                        "total": item["total"],
                        "in_use": item["in_use"],
                        "available": item["available_count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse({"categories": categories})


@login_required
def asset_request_status(request):
    """Asset request status breakdown."""
    from asset.models import AssetRequest

    statuses = [
        {
            "status": "Requested",
            "label": "Requested",
            "count": AssetRequest.objects.filter(
                asset_request_status="Requested"
            ).count(),
        },
        {
            "status": "Approved",
            "label": "Approved",
            "count": AssetRequest.objects.filter(
                asset_request_status="Approved"
            ).count(),
        },
        {
            "status": "Rejected",
            "label": "Rejected",
            "count": AssetRequest.objects.filter(
                asset_request_status="Rejected"
            ).count(),
        },
    ]

    return JsonResponse({"statuses": statuses})


@login_required
def asset_value_by_category(request):
    """Total asset value by category."""
    from asset.models import Asset

    categories = []

    try:
        data = (
            Asset.objects.all()
            .values("asset_category_id__asset_category_name")
            .annotate(
                total_value=Coalesce(
                    Sum("asset_purchase_cost"), 0, output_field=DecimalField()
                ),
                count=Count("id"),
            )
            .order_by("-total_value")
        )

        for item in data:
            cat = item["asset_category_id__asset_category_name"]
            if cat:
                categories.append(
                    {
                        "category": cat,
                        "value": float(item["total_value"]),
                        "count": item["count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse({"categories": categories})


@login_required
def asset_expiring_soon(request):
    """Assets expiring in the next 60 days."""
    from asset.models import Asset

    today = date.today()
    assets = []

    try:
        qs = (
            Asset.objects.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + timedelta(days=60),
            )
            .select_related("asset_category_id")
            .order_by("expiry_date")[:15]
        )

        for a in qs:
            days_left = (a.expiry_date - today).days
            assets.append(
                {
                    "name": a.asset_name,
                    "tracking_id": a.asset_tracking_id,
                    "category": (
                        a.asset_category_id.asset_category_name
                        if a.asset_category_id
                        else "—"
                    ),
                    "expiry_date": a.expiry_date.strftime("%b %d, %Y"),
                    "days_left": days_left,
                    "status": a.asset_status,
                }
            )
    except Exception:
        pass

    return JsonResponse({"assets": assets})


@login_required
def asset_recent_allocations(request):
    """Recently allocated assets."""
    from asset.models import AssetAssignment

    allocations = []

    try:
        qs = (
            AssetAssignment.objects.filter(
                return_status__isnull=True,
            )
            .select_related(
                "asset_id", "assigned_to_employee_id", "asset_id__asset_category_id"
            )
            .order_by("-assigned_date")[:15]
        )

        for aa in qs:
            emp = aa.assigned_to_employee_id
            allocations.append(
                {
                    "id": emp.id if emp else None,
                    "employee": emp.get_full_name() if emp else "—",
                    "avatar": (
                        emp.employee_profile.url
                        if emp and emp.employee_profile
                        else None
                    ),
                    "asset": aa.asset_id.asset_name if aa.asset_id else "—",
                    "category": (
                        aa.asset_id.asset_category_id.asset_category_name
                        if aa.asset_id and aa.asset_id.asset_category_id
                        else "—"
                    ),
                    "date": (
                        aa.assigned_date.strftime("%b %d") if aa.assigned_date else "—"
                    ),
                }
            )
    except Exception:
        pass

    return JsonResponse({"allocations": allocations})


@login_required
def asset_department_distribution(request):
    """Assets distributed by department (via assigned employees)."""
    from asset.models import AssetAssignment

    departments = []

    try:
        data = (
            AssetAssignment.objects.filter(return_status__isnull=True)
            .values(
                "assigned_to_employee_id__employee_work_info__department_id__department"
            )
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for item in data:
            dept = item[
                "assigned_to_employee_id__employee_work_info__department_id__department"
            ]
            if dept:
                departments.append(
                    {
                        "department": dept,
                        "count": item["count"],
                    }
                )
    except Exception:
        pass

    return JsonResponse({"departments": departments})


@login_required
def asset_age_distribution(request):
    """Asset age distribution by purchase year."""
    from asset.models import Asset

    today = date.today()
    brackets = []
    try:
        bracket_map = {
            "< 1 year": 0,
            "1–2 years": 0,
            "2–3 years": 0,
            "3–5 years": 0,
            "5+ years": 0,
        }
        for a in Asset.objects.filter(asset_purchase_date__isnull=False):
            age_years = (today - a.asset_purchase_date).days / 365.25
            if age_years < 1:
                bracket_map["< 1 year"] += 1
            elif age_years < 2:
                bracket_map["1–2 years"] += 1
            elif age_years < 3:
                bracket_map["2–3 years"] += 1
            elif age_years < 5:
                bracket_map["3–5 years"] += 1
            else:
                bracket_map["5+ years"] += 1
        brackets = [{"bracket": k, "count": v} for k, v in bracket_map.items() if v > 0]
    except Exception:
        pass
    return JsonResponse({"brackets": brackets})
