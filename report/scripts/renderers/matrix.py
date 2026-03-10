"""Test pass/fail matrix renderer — heatmap-style matrix charts from TestResultsData."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from chart_types import (
    ChartOutput,
    ChartType,
    FONT_FAMILY,
    FULL_WIDTH_PX,
    DEFAULT_HEIGHT_PX,
    TestResultsData,
)
from generate_charts import register_renderer

STATUS_COLORS: dict[str, str] = {
    "pass": "#4caf50",
    "fail": "#f44336",
    "skip": "#9e9e9e",
}

STATUS_NUMERIC: dict[str, int] = {
    "pass": 2,
    "skip": 1,
    "fail": 0,
}

DATA_SOURCE = "test-results.json"


def build_categorical_colorscale() -> list[list[float | str]]:
    """Return a 3-color discrete colorscale: 0=fail(red), 1=skip(gray), 2=pass(green)."""
    return [
        [0.0, STATUS_COLORS["fail"]],
        [0.5, STATUS_COLORS["skip"]],
        [1.0, STATUS_COLORS["pass"]],
    ]


def encode_status_matrix(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """Convert a string status matrix to numeric encoding using STATUS_NUMERIC."""
    return matrix_df.map(lambda v: STATUS_NUMERIC.get(str(v).lower(), 1))


def decide_matrix_split(
    test_results_data: TestResultsData,
    *,
    max_tests_per_chart: int = 40,
) -> bool:
    """Return True if the matrix should be split by suite (total tests > threshold)."""
    return len(test_results_data.test_ids) > max_tests_per_chart


def build_suite_separators(
    test_ids: list[str],
    suite_grouping: dict[str, str],
) -> list[float]:
    """Return x-axis positions where suite boundaries occur.

    Each separator sits between the last test of one suite and the first test of the next.
    """
    if not test_ids:
        return []

    separators: list[float] = []
    prev_suite = suite_grouping.get(test_ids[0], "")
    for i, tid in enumerate(test_ids[1:], start=1):
        current_suite = suite_grouping.get(tid, "")
        if current_suite != prev_suite:
            separators.append(i - 0.5)
        prev_suite = current_suite
    return separators


def build_matrix_figure(
    test_results_data: TestResultsData,
    test_ids: list[str] | None = None,
    *,
    title: str,
    width: int = FULL_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
) -> go.Figure:
    """Build a heatmap figure for the test pass/fail matrix.

    Parameters
    ----------
    test_results_data:
        The full test results data.
    test_ids:
        Subset of test IDs to include. If None, uses all test_ids.
    title:
        Chart title.
    width, height:
        Figure dimensions in pixels.
    """
    ids = test_ids if test_ids is not None else test_results_data.test_ids
    tools = test_results_data.tools

    sub_df = test_results_data.matrix_df.loc[ids, tools]
    numeric_df = encode_status_matrix(sub_df)

    # Heatmap: x=test_ids (columns after transpose), y=tools (rows after transpose)
    # matrix_df has rows=test_ids, columns=tools. We want y=tools, x=test_ids.
    z_values = numeric_df.T.values.tolist()

    # Build hover text from original status strings
    hover_text = sub_df.T.values.tolist()

    colorscale = build_categorical_colorscale()

    heatmap = go.Heatmap(
        z=z_values,
        x=ids,
        y=tools,
        colorscale=colorscale,
        zmin=0,
        zmax=2,
        showscale=False,
        text=hover_text,
        hovertemplate="Tool: %{y}<br>Test: %{x}<br>Result: %{text}<extra></extra>",
    )

    fig = go.Figure(data=[heatmap])

    # Suite separators
    separators = build_suite_separators(ids, test_results_data.suite_grouping)
    for sep_x in separators:
        fig.add_vline(x=sep_x, line_width=2, line_dash="dash", line_color="white")

    tick_angle = -90 if len(ids) > 20 else -60

    fig.update_layout(
        title=dict(text=title, font=dict(family=FONT_FAMILY, size=16)),
        xaxis=dict(
            tickangle=tick_angle,
            tickfont=dict(family=FONT_FAMILY, size=10),
            side="bottom",
        ),
        yaxis=dict(
            tickfont=dict(family=FONT_FAMILY, size=11),
            autorange="reversed",
        ),
        width=width,
        height=height,
        margin=dict(l=120, r=40, t=60, b=120),
        font=dict(family=FONT_FAMILY),
    )

    return fig


def build_fallback_suite_summary(test_results_data: TestResultsData) -> go.Figure:
    """Build a simple bar chart summarizing suite-level pass counts as a fallback.

    Used when no individual test IDs are available.
    """
    tools = test_results_data.tools
    # Count passes per tool from the matrix (even if empty, handle gracefully)
    pass_counts = []
    for tool in tools:
        if tool in test_results_data.matrix_df.columns:
            count = (test_results_data.matrix_df[tool] == "pass").sum()
        else:
            count = 0
        pass_counts.append(count)

    fig = go.Figure(
        data=[
            go.Bar(
                x=tools,
                y=pass_counts,
                marker_color=[STATUS_COLORS["pass"]] * len(tools),
            )
        ]
    )
    fig.update_layout(
        title=dict(
            text="Suite Summary (no individual test data)",
            font=dict(family=FONT_FAMILY, size=16),
        ),
        xaxis=dict(tickfont=dict(family=FONT_FAMILY)),
        yaxis=dict(title="Tests Passed", tickfont=dict(family=FONT_FAMILY)),
        width=FULL_WIDTH_PX,
        height=DEFAULT_HEIGHT_PX,
        font=dict(family=FONT_FAMILY),
    )
    return fig


def render_test_matrix(
    test_results_data: TestResultsData,
    **_kwargs: object,
) -> list[ChartOutput]:
    """Render test pass/fail matrix chart(s) from TestResultsData.

    If total tests <= 40: produces a single chart with id "matrix_test-results".
    If > 40: splits by suite, producing one chart per suite with id
    "matrix_test-results-{suite_name}".

    Falls back to a suite summary bar chart if no individual test IDs exist.
    """
    if not test_results_data.test_ids:
        fig = build_fallback_suite_summary(test_results_data)
        return [
            ChartOutput(
                chart_id="matrix_test-results-summary",
                chart_type=ChartType.MATRIX,
                subject="test-results-summary",
                figure=fig,
                data_source=DATA_SOURCE,
                title="Test Results Summary",
            )
        ]

    should_split = decide_matrix_split(test_results_data)

    if not should_split:
        fig = build_matrix_figure(
            test_results_data,
            title="Test Pass/Fail Matrix",
        )
        return [
            ChartOutput(
                chart_id="matrix_test-results",
                chart_type=ChartType.MATRIX,
                subject="test-results",
                figure=fig,
                data_source=DATA_SOURCE,
                title="Test Pass/Fail Matrix",
            )
        ]

    # Split by suite
    outputs: list[ChartOutput] = []
    suites_seen: dict[str, list[str]] = {}
    for tid in test_results_data.test_ids:
        suite = test_results_data.suite_grouping.get(tid, "unknown")
        suites_seen.setdefault(suite, []).append(tid)

    for suite_name, suite_test_ids in suites_seen.items():
        fig = build_matrix_figure(
            test_results_data,
            test_ids=suite_test_ids,
            title=f"Test Matrix — {suite_name}",
        )
        outputs.append(
            ChartOutput(
                chart_id=f"matrix_test-results-{suite_name}",
                chart_type=ChartType.MATRIX,
                subject=f"test-results-{suite_name}",
                figure=fig,
                data_source=DATA_SOURCE,
                title=f"Test Matrix — {suite_name}",
            )
        )

    return outputs


# Register this renderer with the chart pipeline
register_renderer("matrix", render_test_matrix)
