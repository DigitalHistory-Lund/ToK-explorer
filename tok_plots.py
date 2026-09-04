"""Shared Plotly helpers for generated Quarto pages.

Every page produced by ``build-quarto.py`` imports from this module,
so no chart is duplicated between pages. Functions take a
``pandas.DataFrame`` and column names + a title and render an
inline plotly figure via ``plotly.offline.iplot``.

Line plots skip zero values (treated as gaps, not real observations)
and mark the endpoints of each contiguous non-zero segment so short
runs are visible even when the surrounding data is missing.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objs as go
import plotly.offline as pyo


ENDPOINT_MARKER_SIZE = 7

# Historical thresholds used as vertical markers on year-axis charts.
WOMEN_IN_CHAMBER_VLINES: list[tuple[float, str]] = [
    (1919, "women's suffrage"),
    (1922, "first woman elected"),
]


def configure() -> None:
    """Init the offline notebook mode. Call once per page."""
    pyo.init_notebook_mode(connected=False)


def _title(text: str) -> dict:
    return {"title": {"text": text, "xanchor": "center", "x": 0.5}}


def _apply_vlines(layout: dict, vlines: list[tuple[float, str]] | None) -> None:
    """Append dashed vertical lines + short labels at each ``(x, label)``.

    No-op when ``vlines`` is falsy. Preserves any shapes/annotations already on
    the layout.
    """
    if not vlines:
        return
    shapes = list(layout.get("shapes", []))
    annotations = list(layout.get("annotations", []))
    for x, label in vlines:
        shapes.append({
            "type": "line",
            "xref": "x",
            "yref": "paper",
            "x0": x, "x1": x,
            "y0": 0, "y1": 1,
            "line": {"color": "gray", "dash": "dash", "width": 1},
        })
        annotations.append({
            "x": x,
            "xref": "x",
            "y": 1,
            "yref": "paper",
            "text": label,
            "showarrow": False,
            "yshift": 10,
            "font": {"size": 10, "color": "gray"},
        })
    layout["shapes"] = shapes
    layout["annotations"] = annotations


def _sum_by(df: pd.DataFrame, group_cols: Iterable[str]) -> pd.DataFrame:
    return df.groupby(list(group_cols), as_index=False).sum(numeric_only=True)


def _drop_zeros(y):
    """Return a copy of ``y`` where 0 (and NaN) become None so plotly leaves gaps."""
    return [v if (v is not None and pd.notna(v) and v != 0) else None for v in y]


def _endpoint_sizes(y):
    """Marker sizes: ``ENDPOINT_MARKER_SIZE`` at segment endpoints, 0 elsewhere.

    An endpoint is a non-None y-value whose left or right neighbour is None
    (or which sits at the start/end of the series). This surfaces isolated
    points and the boundaries of a run of data next to gaps.
    """
    n = len(y)
    sizes = [0] * n
    for i in range(n):
        if y[i] is None:
            continue
        left = y[i - 1] if i > 0 else None
        right = y[i + 1] if i < n - 1 else None
        if left is None or right is None:
            sizes[i] = ENDPOINT_MARKER_SIZE
    return sizes


def _line_trace(x, y, name):
    x = list(x)
    y_clean = _drop_zeros(list(y))
    return go.Scatter(
        mode="lines+markers",
        x=x,
        y=y_clean,
        name=name,
        connectgaps=False,
        marker={"size": _endpoint_sizes(y_clean)},
    )


def line_absolute(
    df: pd.DataFrame,
    x: str,
    ys: list[tuple[str, str]],
    title: str,
    log_y: bool = False,
    vlines: list[tuple[float, str]] | None = None,
) -> None:
    """One line per column in ``ys`` (list of ``(column, label)``).

    Legend labels include per-line running totals.
    """
    aggregated = _sum_by(df, [x])
    lines = []
    for column, label in ys:
        total = int(aggregated[column].sum())
        lines.append(_line_trace(aggregated[x], aggregated[column], f"{label} ({total:,})"))
    layout = _title(title)
    if log_y:
        layout["yaxis"] = {"type": "log"}
    _apply_vlines(layout, vlines)
    pyo.iplot({"data": lines, "layout": layout})


def line_relative(
    df: pd.DataFrame,
    x: str,
    ys: list[tuple[str, str]],
    baseline: str,
    title: str,
    vlines: list[tuple[float, str]] | None = None,
) -> None:
    """Each y column divided by the baseline column, per x bucket."""
    aggregated = _sum_by(df, [x])
    lines = []
    for column, label in ys:
        rate = aggregated[column] / aggregated[baseline]
        lines.append(_line_trace(aggregated[x], rate, label))
    layout = _title(title)
    _apply_vlines(layout, vlines)
    pyo.iplot({"data": lines, "layout": layout})


def line_absolute_by_group(
    df: pd.DataFrame,
    x: str,
    ys: list[tuple[str, str]],
    group: str,
    title: str,
    vlines: list[tuple[float, str]] | None = None,
) -> None:
    """One line per (group value, y column) pair, absolute values."""
    subset = df[df[group].notna()]
    aggregated = _sum_by(subset, [x, group])
    lines = []
    for value in sorted(aggregated[group].unique()):
        piece = aggregated[aggregated[group] == value]
        for column, label in ys:
            lines.append(_line_trace(piece[x], piece[column], f"{value}: {label}"))
    layout = _title(title)
    _apply_vlines(layout, vlines)
    pyo.iplot({"data": lines, "layout": layout})


def line_relative_by_group(
    df: pd.DataFrame,
    x: str,
    ys: list[tuple[str, str]],
    baseline: str,
    group: str,
    title: str,
    vlines: list[tuple[float, str]] | None = None,
) -> None:
    """One line per (group value, y column) pair, y/baseline values."""
    subset = df[df[group].notna()]
    aggregated = _sum_by(subset, [x, group])
    lines = []
    for value in sorted(aggregated[group].unique()):
        piece = aggregated[aggregated[group] == value]
        for column, label in ys:
            rate = piece[column] / piece[baseline]
            lines.append(_line_trace(piece[x], rate, f"{value}: {label}"))
    layout = _title(title)
    _apply_vlines(layout, vlines)
    pyo.iplot({"data": lines, "layout": layout})


def line_absolute_per_group(
    df: pd.DataFrame,
    x: str,
    y: str,
    group: str,
    title: str,
    vlines: list[tuple[float, str]] | None = None,
) -> None:
    """One line per distinct value of ``group``, absolute y against x."""
    subset = df[df[group].notna()]
    aggregated = _sum_by(subset, [x, group])
    lines = []
    for value in sorted(aggregated[group].unique()):
        piece = aggregated[aggregated[group] == value]
        lines.append(_line_trace(piece[x], piece[y], str(value)))
    layout = _title(title)
    _apply_vlines(layout, vlines)
    pyo.iplot({"data": lines, "layout": layout})


def line_per_group(
    df: pd.DataFrame,
    x: str,
    y: str,
    baseline: str,
    group: str,
    title: str,
    vlines: list[tuple[float, str]] | None = None,
) -> None:
    """One line per distinct value of ``group``, y/baseline against x."""
    subset = df[df[group].notna()]
    aggregated = _sum_by(subset, [x, group])
    lines = []
    for value in sorted(aggregated[group].unique()):
        piece = aggregated[aggregated[group] == value]
        rate = piece[y] / piece[baseline]
        lines.append(_line_trace(piece[x], rate, str(value)))
    layout = _title(title)
    _apply_vlines(layout, vlines)
    pyo.iplot({"data": lines, "layout": layout})


def line_distinct(
    df: pd.DataFrame,
    x: str,
    distinct_col: str,
    ys: list[tuple[str, str]],
    title: str,
) -> None:
    """One line per ``(filter_col, label)`` pair: distinct count of ``distinct_col`` per ``x``.

    ``filter_col == "*"`` means the unconditional distinct count (no row filter).
    Otherwise the count is over rows where ``filter_col > 0``.
    """
    lines = []
    for filter_col, label in ys:
        subset = df if filter_col == "*" else df[df[filter_col] > 0]
        counts = subset.groupby(x)[distinct_col].nunique().sort_index()
        lines.append(_line_trace(list(counts.index), list(counts.values), label))
    pyo.iplot({"data": lines, "layout": _title(title)})


def line_distinct_by_group(
    df: pd.DataFrame,
    x: str,
    distinct_col: str,
    group: str,
    title: str,
    filter_col: str | None = None,
) -> None:
    """One line per distinct ``group`` value: distinct count of ``distinct_col`` per ``x``.

    Optional ``filter_col`` restricts to rows where that column is > 0
    (used for "distinct speakers with a K1 hit, split by gender").
    """
    subset = df[df[group].notna()]
    if filter_col is not None:
        subset = subset[subset[filter_col] > 0]
    lines = []
    for value in sorted(subset[group].unique()):
        piece = subset[subset[group] == value]
        counts = piece.groupby(x)[distinct_col].nunique().sort_index()
        lines.append(_line_trace(list(counts.index), list(counts.values), str(value)))
    pyo.iplot({"data": lines, "layout": _title(title)})


def heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    value: str,
    title: str,
    zmin: float | None = None,
    zmax: float | None = None,
) -> None:
    """2-D heatmap. Rows keyed by ``y``, columns by ``x``, cell values by ``value``.

    Colour intensity is each cell's share of its row sum, so rows on different
    scales stay visually comparable. The hover tooltip shows both the share and
    the raw ``value``.
    """
    pivoted = df.pivot(index=y, columns=x, values=value)
    row_sums = pivoted.sum(axis=1)
    shares = pivoted.div(row_sums, axis=0).fillna(0)
    fig = {
        "data": [
            go.Heatmap(
                z=shares.values,
                x=list(pivoted.columns),
                y=list(pivoted.index),
                customdata=pivoted.values,
                hovertemplate=(
                    "%{x}<br>%{y}: %{z:.1%} of row "
                    "(%{customdata:,} " + value + ")<extra></extra>"
                ),
                colorbar={"title": "row share"},
                zmin=zmin,
                zmax=zmax,
            )
        ],
        "layout": _title(title),
    }
    pyo.iplot(fig)
