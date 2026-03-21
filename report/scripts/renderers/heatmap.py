"""Grade comparison heatmap renderer (PRD 02/03).

Produces a single ChartOutput showing letter grades for all tools x criteria
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

GRADE_COLOR_SCALE: list[list[float | str]] = [
    [0.0, "#c0392b"],  # F = red (matches .grade-f in evaluation.css)
    [0.25, "#d4764e"],  # D = orange (matches .grade-d)
    [0.5, "#e8b44d"],  # C = amber (matches .grade-c)
    [0.75, "#7ec8a0"],  # B = light green (matches .grade-b)
    [1.0, "#1b7a3d"],  # A = dark green (matches .grade-a)
]


def annotation_font_color(grade_value: float) -> str:
    """Return white for dark cells (A/A-, F), dark gray for light cells (B, C, D).

    A/A- grades (>=3.5) sit on dark green; F grades (<=0.5) sit on dark red.
    Both need white text. Mid-range grades (B+, B, B-, C+, C, D) sit on lighter
    backgrounds and need dark text for readability.
    """
    if grade_value >= 3.5 or grade_value <= 0.5:
        return "#ffffff"
    return "#1a1a1a"


def grade_colorscale_to_plotly(
    scale: list[list[float | str]],
) -> list[list[float | str]]:
    """Convert breakpoint tuples to Plotly-compatible colorscale format.

    Plotly expects a list of [normalized_value, color_string] pairs.
    This function validates and returns the scale as-is since our internal
    format already matches Plotly's expected format.
    """
    return [[float(point[0]), str(point[1])] for point in scale]


def build_grade_annotations(grades_data: GradesData) -> list[dict]:
    """Build Plotly annotation dicts for each cell showing the letter grade.

    Returns one annotation per cell in the tools x criteria grid.
    """
    annotations: list[dict] = []
    for row_idx, tool in enumerate(grades_data.tools):
        for col_idx, criterion in enumerate(grades_data.criteria):
            letter = grades_data.letter_grades[tool][criterion]
            numeric = grades_data.df.loc[criterion, tool]
            annotations.append(
                {
                    "x": col_idx,
                    "y": row_idx,
                    "text": letter,
                    "font": {
                        "color": annotation_font_color(numeric),
                        "size": 14,
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
    - z = numeric grade values (rows=tools, columns=criteria)
    - x = criteria labels
    - y = tool labels
    - Annotations showing letter grades in each cell
    - Consistent color mapping with zmin=0, zmax=4
    """
    # Build z-matrix: rows=tools, columns=criteria
    z_values: list[list[float]] = []
    for tool in grades_data.tools:
        row = [
            float(grades_data.df.loc[criterion, tool])
            for criterion in grades_data.criteria
        ]
        z_values.append(row)

    colorscale = grade_colorscale_to_plotly(GRADE_COLOR_SCALE)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=grades_data.criteria,
            y=grades_data.tools,
            colorscale=colorscale,
            zmin=0,
            zmax=4,
            showscale=True,
            colorbar={"title": "Grade"},
        )
    )

    annotations = build_grade_annotations(grades_data)

    fig.update_layout(
        title="Grade Comparison Heatmap",
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
    """Return a list with one ChartOutput for the grade comparison heatmap."""
    fig = build_heatmap_figure(grades_data)
    return [
        ChartOutput(
            chart_id="heatmap_grades",
            chart_type=ChartType.HEATMAP,
            subject="grades",
            figure=fig,
            data_source="grades.json",
            title="Grade Comparison Heatmap",
        )
    ]


register_renderer("heatmap", render_grade_heatmap)
