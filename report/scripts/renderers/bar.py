"""Per-criterion horizontal bar chart renderer.

Produces one bar chart per rubric criterion showing each tool's grade as a
horizontal bar, colored by tool identity, with letter-grade annotations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import (
    ChartOutput,
    ChartType,
    FONT_FAMILY,
    FULL_WIDTH_PX,
    GradesData,
    TOOL_COLORS,
    register_renderer,
)

TIER_TICKS: dict[int, str] = {0: "Failing", 1: "Weak", 2: "Adequate", 3: "Strong"}
BAR_HEIGHT_PX: int = 350


def build_criterion_bar(
    grades_data: GradesData,
    criterion: str,
) -> go.Figure:
    """Build a horizontal bar chart for a single criterion."""
    tools = list(reversed(grades_data.tools))  # top tool at top of chart
    values = [float(grades_data.df.loc[criterion, t]) for t in tools]
    colors = [TOOL_COLORS.get(t, "#333333") for t in tools]
    letters = [grades_data.tier_labels[t][criterion] for t in tools]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=values,
            y=tools,
            orientation="h",
            marker={"color": colors},
            text=letters,
            textposition="auto",
            textfont={"family": FONT_FAMILY, "size": 14, "color": "#ffffff"},
            hovertemplate="%{y}: %{text} (%{x:.1f})<extra></extra>",
        )
    )

    pretty_name = criterion.replace("_", " ").title()
    fig.update_layout(
        title=f"{pretty_name} - Tier Comparison",
        xaxis={
            "title": "Grade",
            "range": [0, 3.5],
            "tickvals": list(TIER_TICKS.keys()),
            "ticktext": list(TIER_TICKS.values()),
        },
        yaxis={"title": None},
        width=FULL_WIDTH_PX,
        height=BAR_HEIGHT_PX,
        font={"family": FONT_FAMILY},
        showlegend=False,
        margin={"l": 140},  # room for tool names
    )

    return fig


def render_bar_charts(
    *,
    grades_data: GradesData,
    **_kwargs: object,
) -> list[ChartOutput]:
    """Return one ChartOutput per criterion (6 total)."""
    outputs: list[ChartOutput] = []
    for criterion in grades_data.criteria:
        fig = build_criterion_bar(grades_data, criterion)
        pretty_name = criterion.replace("_", " ").title()
        outputs.append(
            ChartOutput(
                chart_id=f"bar_{criterion}",
                chart_type=ChartType.BAR,
                subject=f"{criterion}_grades",
                figure=fig,
                data_source="grades.json",
                title=f"{pretty_name} - Tier Comparison",
            )
        )
    return outputs


register_renderer("bar", render_bar_charts)
