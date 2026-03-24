"""Radar chart renderer — per-tool and overlay radar charts from grades data."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go

# Ensure scripts/ is importable (same pattern as the test suite)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import (
    ChartOutput,
    ChartType,
    DEFAULT_HEIGHT_PX,
    FONT_FAMILY,
    FULL_WIDTH_PX,
    GradesData,
    PER_TOOL_WIDTH_PX,
    TOOL_COLORS,
    register_renderer,
)

TIER_TICKS: dict[int, str] = {0: "Failing", 1: "Weak", 2: "Adequate", 3: "Strong"}


def render_radar_charts(
    grades_data: GradesData,
    **_kwargs: object,
) -> list[ChartOutput]:
    """Return 7 ChartOutput objects: 6 per-tool radars + 1 overlay."""
    outputs: list[ChartOutput] = []

    for tool in grades_data.tools:
        values = [float(grades_data.df.loc[c, tool]) for c in grades_data.criteria]
        color = TOOL_COLORS.get(tool, "#333333")
        fig = build_per_tool_radar(
            tool_name=tool,
            values=values,
            criteria=grades_data.criteria,
            color=color,
        )
        outputs.append(
            ChartOutput(
                chart_id=f"radar_{tool}",
                chart_type=ChartType.RADAR,
                subject=tool,
                figure=fig,
                data_source="grades.json",
                title=f"Radar — {tool}",
            )
        )

    overlay_fig = build_overlay_radar(grades_data)
    outputs.append(
        ChartOutput(
            chart_id="radar_overlay",
            chart_type=ChartType.RADAR,
            subject="overlay",
            figure=overlay_fig,
            data_source="grades.json",
            title="Radar — All Tools Overlay",
        )
    )

    return outputs


def build_per_tool_radar(
    tool_name: str,
    values: list[float],
    criteria: list[str],
    color: str,
    *,
    width: int = PER_TOOL_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
) -> go.Figure:
    """Build a single-tool radar chart with one filled Scatterpolar trace."""
    # Close the polygon
    r_closed = values + [values[0]]
    theta_closed = criteria + [criteria[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r_closed,
            theta=theta_closed,
            fill="toself",
            fillcolor=color,
            line={"color": color},
            name=tool_name,
        )
    )

    configure_polar_layout(fig, criteria)
    fig.update_layout(
        width=width,
        height=height,
        title=tool_name,
        font={"family": FONT_FAMILY},
        showlegend=False,
    )
    return fig


def build_overlay_radar(
    grades_data: GradesData,
    *,
    width: int = FULL_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
    fill_opacity: float = 0.3,
) -> go.Figure:
    """Build an overlay radar chart with one semi-transparent trace per tool."""
    fig = go.Figure()

    for tool in grades_data.tools:
        values = [float(grades_data.df.loc[c, tool]) for c in grades_data.criteria]
        color = TOOL_COLORS.get(tool, "#333333")

        r_closed = values + [values[0]]
        theta_closed = grades_data.criteria + [grades_data.criteria[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=r_closed,
                theta=theta_closed,
                fill="toself",
                opacity=fill_opacity,
                line={"color": color},
                name=tool,
                showlegend=True,
            )
        )

    configure_polar_layout(fig, grades_data.criteria)
    fig.update_layout(
        width=width,
        height=height,
        title="All Tools Overlay",
        font={"family": FONT_FAMILY},
        showlegend=True,
    )
    return fig


def configure_polar_layout(
    fig: go.Figure,
    criteria: list[str],
    *,
    radial_range: tuple[float, float] = (0, 3.5),
) -> None:
    """Set radial ticks at 0-3 with tier labels; angular labels = criteria."""
    tick_vals = list(TIER_TICKS.keys())
    tick_text = list(TIER_TICKS.values())

    fig.update_layout(
        polar={
            "radialaxis": {
                "visible": True,
                "range": list(radial_range),
                "tickvals": tick_vals,
                "ticktext": tick_text,
            },
            "angularaxis": {
                "categoryorder": "array",
                "categoryarray": criteria,
            },
        },
    )


# Register this renderer so the pipeline discovers it at import time.
register_renderer("radar", render_radar_charts)
