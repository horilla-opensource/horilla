"""Server-side chart-to-PNG rendering for report exports (PDF + Excel).

Uses reportlab.graphics — already a pinned dependency via xhtml2pdf/pisa
(see requirements.txt), so this adds no new package requirement. Renders
the same bar/donut/line primitives the in-app charts use
(report/metrics/*.py's payload["charts"]) into standalone PNGs that get
embedded in the PDF export and, separately, backed by real openpyxl chart
objects in the Excel export (see report/export.py).
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Optional

from reportlab.graphics import renderPM
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors

# Same brand palette as report/export.py's COLOR_PRIMARY, plus a few
# distinct hues for additional series — kept visually consistent with the
# in-app charts and the rest of the exported document.
PALETTE = [
    colors.HexColor("#E54F38"),  # coral — brand primary
    colors.HexColor("#2563EB"),  # blue
    colors.HexColor("#15803D"),  # green
    colors.HexColor("#7C3AED"),  # violet
    colors.HexColor("#0D9488"),  # teal
    colors.HexColor("#F59E0B"),  # amber
]

WIDTH = 560
HEIGHT = 260
# Reserved column on the right for the legend, whenever one is drawn — keeps
# swatch+text inside the canvas instead of being clipped at the edge.
LEGEND_COL = 150


def render_chart_png(
    chart: dict[str, Any], width: int = WIDTH, height: int = HEIGHT
) -> Optional[bytes]:
    """Render one payload["charts"] entry to a PNG. Returns None if the
    chart has no plottable data — callers should skip it in that case."""
    categories = chart.get("categories") or []
    series = [s for s in (chart.get("series") or []) if s.get("data")]
    if not categories or not series:
        return None

    chart_type = (chart.get("type") or "bar").lower()
    try:
        if chart_type in ("donut", "pie"):
            drawing = _pie_drawing(categories, series[0], width, height)
        elif chart_type == "line":
            drawing = _line_drawing(categories, series, width, height)
        else:
            drawing = _bar_drawing(categories, series, width, height)
    except Exception:
        return None

    buf = BytesIO()
    renderPM.drawToFile(drawing, buf, fmt="PNG", dpi=150)
    return buf.getvalue()


def _legend(pairs: list[tuple], x: float, y: float) -> Legend:
    legend = Legend()
    legend.x = x
    legend.y = y
    legend.alignment = "left"
    legend.fontSize = 8
    legend.boxAnchor = "nw"
    legend.dx = 8
    legend.dy = 8
    legend.dxTextSpace = 6
    legend.deltay = 14
    legend.columnMaximum = 12
    legend.colorNamePairs = pairs
    return legend


def _bar_drawing(categories, series, width, height) -> Drawing:
    drawing = Drawing(width, height)
    has_legend = len(series) > 1
    plot_width = width - LEGEND_COL - 70 if has_legend else width - 90

    chart = VerticalBarChart()
    chart.x = 55
    chart.y = 55
    chart.width = plot_width
    chart.height = height - 80
    chart.data = [[v or 0 for v in (s.get("data") or [])] for s in series]
    chart.categoryAxis.categoryNames = [str(c) for c in categories]
    chart.categoryAxis.labels.fontSize = 7
    if len(categories) > 6:
        chart.categoryAxis.labels.angle = 30
        chart.categoryAxis.labels.dx = -6
        chart.categoryAxis.labels.dy = -8
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.barSpacing = 3
    chart.groupSpacing = 12
    chart.bars.strokeColor = None
    for i in range(len(series)):
        chart.bars[i].fillColor = PALETTE[i % len(PALETTE)]
    drawing.add(chart)

    if has_legend:
        pairs = [
            (PALETTE[i % len(PALETTE)], s.get("name") or f"Series {i + 1}")
            for i, s in enumerate(series)
        ]
        drawing.add(_legend(pairs, chart.x + plot_width + 20, height - 30))
    return drawing


def _pie_drawing(categories, series, width, height) -> Drawing:
    drawing = Drawing(width, height)
    values = [max(v or 0, 0) for v in (series.get("data") or [])]
    diameter = min(height - 60, 170)
    pie = Pie()
    pie.x = 30
    pie.y = (height - diameter) / 2
    pie.width = diameter
    pie.height = diameter
    pie.data = values
    pie.labels = None
    pie.slices.strokeWidth = 1.2
    pie.slices.strokeColor = colors.white
    for i in range(len(values)):
        pie.slices[i].fillColor = PALETTE[i % len(PALETTE)]
    drawing.add(pie)

    pairs = [
        (PALETTE[i % len(PALETTE)], str(categories[i]))
        for i in range(min(len(categories), len(values)))
    ]
    drawing.add(_legend(pairs, pie.x + diameter + 30, height - 30))
    return drawing


def _line_drawing(categories, series, width, height) -> Drawing:
    drawing = Drawing(width, height)
    has_legend = len(series) > 1
    plot_width = width - LEGEND_COL - 70 if has_legend else width - 90

    chart = LinePlot()
    chart.x = 55
    chart.y = 45
    chart.width = plot_width
    chart.height = height - 75
    chart.data = [
        [(i, v or 0) for i, v in enumerate(s.get("data") or [])] for s in series
    ]
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = max(len(categories) - 1, 1)
    chart.xValueAxis.valueSteps = list(range(len(categories))) or [0]
    labels = [str(c) for c in categories]
    chart.xValueAxis.labelTextFormat = lambda v: (
        labels[int(v)] if 0 <= int(v) < len(labels) else ""
    )
    chart.xValueAxis.labels.fontSize = 7
    chart.yValueAxis.labels.fontSize = 7
    for i in range(len(series)):
        chart.lines[i].strokeColor = PALETTE[i % len(PALETTE)]
        chart.lines[i].strokeWidth = 2.2
    drawing.add(chart)

    if has_legend:
        pairs = [
            (PALETTE[i % len(PALETTE)], s.get("name") or f"Series {i + 1}")
            for i, s in enumerate(series)
        ]
        drawing.add(_legend(pairs, chart.x + plot_width + 20, height - 30))
    return drawing
