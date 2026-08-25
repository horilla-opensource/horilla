"""
Narrative blurbs for standard report exports (Phase 6).
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _


def build_narrative(payload: dict[str, Any]) -> str:
    """
    Short prose summary from KPI deltas / compare metadata.
    Empty when there is nothing useful to say.
    """
    parts: list[str] = []
    compare = payload.get("compare") or {}
    if compare.get("period"):
        label = compare.get("label") or _("comparison period")
        period = compare["period"]
        parts.append(
            _("Compared with %(label)s (%(from)s → %(to)s).")
            % {
                "label": label,
                "from": period.get("from_date") or "—",
                "to": period.get("to_date") or "—",
            }
        )

    movers: list[str] = []
    for kpi in payload.get("kpis") or []:
        direction = kpi.get("delta_direction")
        if direction not in ("up", "down"):
            continue
        delta_label = kpi.get("delta_label")
        if not delta_label:
            continue
        movers.append(
            f"{kpi.get('label') or _('Metric')}: {kpi.get('value')} " f"({delta_label})"
        )
    if movers:
        parts.append(
            _("Key changes: %(changes)s.") % {"changes": "; ".join(movers[:5])}
        )
    elif compare:
        parts.append(_("No material KPI movement versus the comparison period."))

    title = payload.get("title")
    kpis = payload.get("kpis") or []
    if not parts and kpis:
        top = ", ".join(
            f"{k.get('label')}: {k.get('value')}" for k in kpis[:3] if k.get("label")
        )
        if top:
            parts.append(
                _("%(title)s highlights — %(top)s.")
                % {"title": title or _("Report"), "top": top}
            )

    return " ".join(parts).strip()
