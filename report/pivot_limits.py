"""
Shared helpers for pivot explorer scale limits.
"""

from __future__ import annotations

from django.http import JsonResponse

# Soft cap for client-side pivot payloads. Beyond this, users should refine
# filters or use standard reports (server-side aggregates).
MAX_PIVOT_ROWS = 5000


def capped_list(rows, limit: int = MAX_PIVOT_ROWS) -> tuple[list, bool]:
    """Return (rows[:limit], truncated_flag)."""
    rows = list(rows)
    if len(rows) > limit:
        return rows[:limit], True
    return rows, False


def pivot_json_with_meta(rows, limit: int = MAX_PIVOT_ROWS, bare: bool = True):
    """
    If bare=True (default), return JsonResponse(list) for existing PivotTable UI.
    Truncation is applied silently to protect the browser.
    """
    data, truncated = capped_list(rows, limit=limit)
    if bare:
        response = JsonResponse(data, safe=False)
        if truncated:
            response["X-Horilla-Pivot-Truncated"] = "1"
            response["X-Horilla-Pivot-Limit"] = str(limit)
        return response
    return JsonResponse(
        {
            "data": data,
            "truncated": truncated,
            "limit": limit,
            "total": len(rows) if isinstance(rows, list) else len(data),
        }
    )
