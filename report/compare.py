"""
Period comparison helpers for standard reports (Phase 4a).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Optional

from django.utils.translation import gettext as _

from report.engine import ReportFilters

COMPARE_NONE = "none"
COMPARE_PRIOR_PERIOD = "prior_period"
COMPARE_PRIOR_YEAR = "prior_year"
COMPARE_PRESETS = {
    COMPARE_NONE,
    COMPARE_PRIOR_PERIOD,
    COMPARE_PRIOR_YEAR,
}

COMPARE_LABELS = {
    COMPARE_PRIOR_PERIOD: _("Prior period"),
    COMPARE_PRIOR_YEAR: _("Prior year"),
}


def normalize_compare_preset(value: Optional[str]) -> str:
    raw = (value or COMPARE_NONE).strip().lower()
    if raw in ("", "off", "false", "0"):
        return COMPARE_NONE
    if raw in COMPARE_PRESETS:
        return raw
    return COMPARE_NONE


def _shift_year(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        # Feb 29 → Feb 28
        return d.replace(year=d.year - 1, day=28)


def prior_period_bounds(from_date: date, to_date: date) -> tuple[date, date]:
    """Same-length window ending the day before ``from_date``."""
    length = (to_date - from_date).days + 1
    prior_to = from_date - timedelta(days=1)
    prior_from = prior_to - timedelta(days=length - 1)
    return prior_from, prior_to


def prior_year_bounds(from_date: date, to_date: date) -> tuple[date, date]:
    return _shift_year(from_date), _shift_year(to_date)


def resolve_compare_bounds(
    from_date: date, to_date: date, compare_preset: str
) -> Optional[tuple[date, date]]:
    preset = normalize_compare_preset(compare_preset)
    if preset == COMPARE_PRIOR_PERIOD:
        return prior_period_bounds(from_date, to_date)
    if preset == COMPARE_PRIOR_YEAR:
        return prior_year_bounds(from_date, to_date)
    return None


def filters_for_compare(
    filters: ReportFilters, compare_preset: str
) -> Optional[ReportFilters]:
    bounds = resolve_compare_bounds(filters.from_date, filters.to_date, compare_preset)
    if not bounds:
        return None
    prior_from, prior_to = bounds
    return replace(
        filters,
        from_date=prior_from,
        to_date=prior_to,
        period_preset="custom",
        request=None,
        extra={**(filters.extra or {}), "is_compare": True},
    )


def parse_kpi_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1]
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def kpi_is_percent(value: Any) -> bool:
    return isinstance(value, str) and "%" in value


def format_delta_value(delta: float, as_percent_points: bool = False) -> str:
    if as_percent_points:
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta:.1f} pp"
    if abs(delta) >= 1000:
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta:,.0f}"
    if float(delta).is_integer():
        sign = "+" if delta > 0 else ""
        return f"{sign}{int(delta)}"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f}"


def compute_kpi_delta(current_value: Any, prior_value: Any) -> dict[str, Any]:
    cur = parse_kpi_number(current_value)
    pri = parse_kpi_number(prior_value)
    if cur is None or pri is None:
        return {
            "delta": None,
            "delta_pct": None,
            "delta_label": None,
            "delta_direction": "flat",
        }
    delta = cur - pri
    as_pp = kpi_is_percent(current_value) or kpi_is_percent(prior_value)
    if abs(pri) < 1e-9:
        delta_pct = None
    else:
        delta_pct = round((delta / abs(pri)) * 100, 1)
    if abs(delta) < 1e-9:
        direction = "flat"
    elif delta > 0:
        direction = "up"
    else:
        direction = "down"
    label = format_delta_value(delta, as_percent_points=as_pp)
    if delta_pct is not None and not as_pp:
        label = f"{label} ({'+' if delta_pct > 0 else ''}{delta_pct}%)"
    return {
        "delta": round(delta, 4),
        "delta_pct": delta_pct,
        "delta_label": label,
        "delta_direction": direction,
    }


def merge_kpis(current_kpis: list, prior_kpis: list) -> list:
    prior_by_label = {str(k.get("label")): k for k in (prior_kpis or [])}
    merged = []
    for kpi in current_kpis or []:
        item = dict(kpi)
        prior = prior_by_label.get(str(kpi.get("label")))
        if prior is not None:
            item["prior_value"] = prior.get("value")
            item.update(compute_kpi_delta(kpi.get("value"), prior.get("value")))
        merged.append(item)
    return merged


def _align_series_by_category(
    current_categories: list,
    current_data: list,
    prior_categories: list,
    prior_data: list,
) -> list:
    prior_map = {
        str(cat): prior_data[i] if i < len(prior_data) else 0
        for i, cat in enumerate(prior_categories or [])
    }
    return [prior_map.get(str(cat), 0) for cat in (current_categories or [])]


def merge_charts(current_charts: list, prior_charts: list, compare_label: str) -> list:
    prior_by_id = {c.get("id"): c for c in (prior_charts or []) if c.get("id")}
    # Fallback match by title order when ids missing
    prior_list = list(prior_charts or [])
    merged = []
    for idx, chart in enumerate(current_charts or []):
        item = deepcopy(chart)
        prior = prior_by_id.get(chart.get("id"))
        if prior is None and idx < len(prior_list):
            prior = prior_list[idx]
        if not prior:
            merged.append(item)
            continue

        chart_type = (item.get("type") or "bar").lower()
        item["compare_label"] = compare_label
        if chart_type == "donut":
            item["prior_categories"] = prior.get("categories") or []
            prior_series = prior.get("series") or []
            item["prior_data"] = (
                prior_series[0].get("data") if prior_series else []
            ) or []
            merged.append(item)
            continue

        categories = item.get("categories") or []
        series = list(item.get("series") or [])
        prior_categories = prior.get("categories") or []
        prior_series = prior.get("series") or []
        if series and prior_series:
            aligned = _align_series_by_category(
                categories,
                series[0].get("data") or [],
                prior_categories,
                prior_series[0].get("data") or [],
            )
            series.append(
                {
                    "name": compare_label,
                    "data": aligned,
                    "is_compare": True,
                }
            )
            item["series"] = series
        merged.append(item)
    return merged


def apply_compare(
    current_payload: dict,
    prior_payload: dict,
    compare_preset: str,
    prior_filters: ReportFilters,
) -> dict:
    preset = normalize_compare_preset(compare_preset)
    label = str(COMPARE_LABELS.get(preset, _("Comparison")))
    payload = dict(current_payload)
    payload["kpis"] = merge_kpis(
        current_payload.get("kpis") or [], prior_payload.get("kpis") or []
    )
    payload["charts"] = merge_charts(
        current_payload.get("charts") or [],
        prior_payload.get("charts") or [],
        label,
    )
    payload["compare"] = {
        "preset": preset,
        "label": label,
        "period": {
            "from_date": prior_filters.from_date.isoformat(),
            "to_date": prior_filters.to_date.isoformat(),
        },
    }
    filters = list(payload.get("filters") or [])
    filters.append(f"{label}: {prior_filters.period_label}")
    payload["filters"] = filters
    return payload
