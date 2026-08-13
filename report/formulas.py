"""Pure formula helpers used by metric reports / Phase 8 tests."""

from __future__ import annotations


def turnover_rate(hires: int, exits: int, avg_headcount: float) -> float:
    """Period turnover % = exits / average headcount * 100."""
    if not avg_headcount:
        return 0.0
    return round(exits / avg_headcount * 100, 1)


def absenteeism_rate(absent_days: float, expected_days: float) -> float:
    """Absenteeism % = absent / expected working days * 100."""
    if not expected_days:
        return 0.0
    return round(absent_days / expected_days * 100, 1)


def leave_utilization_rate(used: float, allocated: float) -> float:
    if not allocated:
        return 0.0
    return round(used / allocated * 100, 1)


def offer_acceptance_rate(accepted: int, sent: int) -> float:
    if not sent:
        return 0.0
    return round(accepted / sent * 100, 1)


def ot_concentration_share(top_seconds: float, total_seconds: float) -> float:
    if not total_seconds:
        return 0.0
    return round(top_seconds / total_seconds * 100, 1)
