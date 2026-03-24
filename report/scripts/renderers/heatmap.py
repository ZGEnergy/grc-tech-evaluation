"""Grade comparison heatmap renderer (PRD 02/03).

Produces a single ChartOutput showing tier assessments for all tools x criteria
as a color-coded heatmap with cell annotations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go

# Ensure scripts/ is importable when run from various locations
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import (
    ChartOutput,
    ChartType,
    DEFAULT_HEIGHT_PX,
    FONT_FAMILY,
    FULL_WIDTH_PX,
    GradesData,
    register_renderer,
)

TIER_COLOR_SCALE: list[list[float | str]] = [
    [0.0, "#c0392b"],  # Failing = red
    [0.33, "#e8b44d"],  # Weak = amber
    [0.67, "#7ec8a0"],  # Adequate = light green
    [1.0, "#1b7a3d"],  # Strong = dark green
]


def annotation_font_color(tier_value: float) -> str:
    """Return white for dark cells (Strong, Failing), dark gray for light cells.

    Strong (3) sits on dark green; Failing (0) sits on dark red.
    Both need white text. Adequate and Weak sit on lighter backgrounds.
    """
    if tier_value >= 2.5 or tier_value <= 0.5:
        return "#ffffff"
    return "#1a1a1a"


def tier_colorscale_to_plotly(
    scale: list[list[float | str]],
) -> list[list[float | str]]:
    """Convert breakpoint tuples to Plotly-compatible colorscale format."""
    return [[float(point[0]), str(point[1])] for point in scale]


def build_tier_annotations(grades_data: GradesData) -> list[dict]:
    """Build Plotly annotation dicts for each cell showing the tier label.

    Returns one annotation per cell in the tools x criteria grid.
    """
    annotations: list[dict] = []
    for row_idx, tool in enumerate(grades_data.tools):
        for col_idx, criterion in enumerate(grades_data.criteria):
            tier = grades_data.tier_labels[tool][criterion]
            numeric = grades_data.df.loc[criterion, tool]
            annotations.append(
                {
                    "x": col_idx,
                    "y": row_idx,
                    "text": tier,
                    "font": {
                        "color": annotation_font_color(numeric),
                        "size": 13,
                        "family": FONT_FAMILY,
                    },
                    "showarrow": False,
                    "xref": "x",
                    "yref": "y",
                }
            )
    return annotations


def build_heatmap_figure(
    grades_data: GradesData,
    *,
    width: int = FULL_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
) -> go.Figure:
    """Build a Plotly heatmap figure from grades data.

    The heatmap has:
    - z = numeric tier values (rows=tools, columns=criteria)
    - x = criteria labels
    - y = tool labels
    - Annotations showing tier labels in each cell
    - Consistent color mapping with zmin=0, zmax=3
    """
    # Build z-matrix: rows=tools, columns=criteria
    z_values: list[list[float]] = []
    for tool in grades_data.tools:
        row = [
            float(grades_data.df.loc[criterion, tool])
            for criterion in grades_data.criteria
        ]
        z_values.append(row)

    colorscale = tier_colorscale_to_plotly(TIER_COLOR_SCALE)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=grades_data.criteria,
            y=grades_data.tools,
            colorscale=colorscale,
            zmin=0,
            zmax=3,
            showscale=True,
            colorbar={"title": "Tier"},
        )
    )

    annotations = build_tier_annotations(grades_data)

    fig.update_layout(
        title="Tier Comparison Heatmap",
        xaxis={"title": "Criteria", "side": "bottom"},
        yaxis={"title": "Tool", "autorange": "reversed"},
        width=width,
        height=height,
        font={"family": FONT_FAMILY},
        annotations=annotations,
    )

    return fig


def render_grade_heatmap(
    grades_data: GradesData,
    **_kwargs: object,
) -> list[ChartOutput]:
    """Return a list with one ChartOutput for the tier comparison heatmap."""
    fig = build_heatmap_figure(grades_data)
    return [
        ChartOutput(
            chart_id="heatmap_grades",
            chart_type=ChartType.HEATMAP,
            subject="grades",
            figure=fig,
            data_source="grades.json",
            title="Tier Comparison Heatmap",
        )
    ]


register_renderer("heatmap", render_grade_heatmap)
