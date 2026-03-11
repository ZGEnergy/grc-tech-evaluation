"""Scalability benchmark line plots with graceful degradation.

Three-tier rendering strategy:
  1. FULL_TIMING — line plots of solve time vs. network size per tool
  2. PASS_FAIL_ONLY — bar chart of pass/fail counts when timing is missing
  3. NO_DATA — return an empty list (nothing to render)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import plotly.graph_objects as go

from chart_types import (
    ChartOutput,
    ChartType,
    DEFAULT_HEIGHT_PX,
    FONT_FAMILY,
    FULL_WIDTH_PX,
    TestResultsData,
    TimingRecord,
    TOOL_COLORS,
)
from generate_charts import register_renderer

TOOL_MARKERS: dict[str, str] = {
    "pypsa": "circle",
    "pandapower": "square",
    "gridcal": "diamond",
    "powermodels": "triangle-up",
    "powersimulations": "cross",
    "matpower": "star",
}


class ScalabilityDataTier(StrEnum):
    """Classification of available scalability data."""

    FULL_TIMING = "full_timing"
    PASS_FAIL_ONLY = "pass_fail_only"
    NO_DATA = "no_data"


@dataclass(frozen=True)
class BenchmarkSeries:
    """A single tool's timing series for one benchmark type."""

    tool: str
    network_sizes: list[int]
    solve_times: list[float]


@dataclass(frozen=True)
class BenchmarkGroup:
    """All tool series for one benchmark type."""

    benchmark_type: str
    series: list[BenchmarkSeries]


@dataclass(frozen=True)
class ScalabilityAssessment:
    """Assessment of what scalability data is available."""

    tier: ScalabilityDataTier
    timing_records: list[TimingRecord] = field(default_factory=list)
    pass_fail_summary: dict[str, dict[str, int]] = field(default_factory=dict)


def scalability_chart_id(benchmark_type: str) -> str:
    """Generate a chart ID for a scalability benchmark type."""
    return f"line_scalability-{benchmark_type}"


def assess_scalability_data(
    timing_records: list[TimingRecord],
) -> ScalabilityAssessment:
    """Assess the tier of scalability data available from timing records.

    Returns a ScalabilityAssessment indicating which rendering tier to use.
    """
    if not timing_records:
        return ScalabilityAssessment(tier=ScalabilityDataTier.NO_DATA)

    # Check if we have actual solve times (full timing) or just pass/fail
    has_timing = any(r.solve_time_seconds > 0 for r in timing_records)

    if has_timing:
        return ScalabilityAssessment(
            tier=ScalabilityDataTier.FULL_TIMING,
            timing_records=timing_records,
        )

    # Build pass/fail summary: {benchmark_type: {tool: pass_count}}
    summary: dict[str, dict[str, int]] = {}
    for rec in timing_records:
        if rec.benchmark_type not in summary:
            summary[rec.benchmark_type] = {}
        tool_counts = summary[rec.benchmark_type]
        if rec.tool not in tool_counts:
            tool_counts[rec.tool] = 0
        if rec.status == "pass":
            tool_counts[rec.tool] += 1

    return ScalabilityAssessment(
        tier=ScalabilityDataTier.PASS_FAIL_ONLY,
        timing_records=timing_records,
        pass_fail_summary=summary,
    )


def group_timing_by_benchmark(
    timing_records: list[TimingRecord],
) -> list[BenchmarkGroup]:
    """Group timing records into BenchmarkGroups by benchmark_type.

    Within each group, records are further grouped by tool into BenchmarkSeries,
    sorted by network_size.
    """
    # Collect records by benchmark_type, then by tool
    by_benchmark: dict[str, dict[str, list[TimingRecord]]] = {}
    for rec in timing_records:
        by_benchmark.setdefault(rec.benchmark_type, {}).setdefault(rec.tool, []).append(
            rec
        )

    groups: list[BenchmarkGroup] = []
    for bench_type in sorted(by_benchmark):
        tool_records = by_benchmark[bench_type]
        series_list: list[BenchmarkSeries] = []
        for tool_name in sorted(tool_records):
            records = sorted(tool_records[tool_name], key=lambda r: r.network_size)
            series_list.append(
                BenchmarkSeries(
                    tool=tool_name,
                    network_sizes=[r.network_size for r in records],
                    solve_times=[r.solve_time_seconds for r in records],
                )
            )
        groups.append(BenchmarkGroup(benchmark_type=bench_type, series=series_list))

    return groups


def build_line_plot(
    benchmark_group: BenchmarkGroup,
    *,
    width: int = FULL_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
    log_y: bool = True,
) -> go.Figure:
    """Build a line plot for a single benchmark group.

    One trace per tool, with colors from TOOL_COLORS and markers from TOOL_MARKERS.
    """
    fig = go.Figure()

    for series in benchmark_group.series:
        color = TOOL_COLORS.get(series.tool, "#333333")
        marker_symbol = TOOL_MARKERS.get(series.tool, "circle")

        fig.add_trace(
            go.Scatter(
                x=series.network_sizes,
                y=series.solve_times,
                mode="lines+markers",
                name=series.tool,
                line={"color": color},
                marker={"symbol": marker_symbol, "color": color, "size": 8},
            )
        )

    yaxis_type = "log" if log_y else "linear"

    fig.update_layout(
        title=f"Scalability — {benchmark_group.benchmark_type}",
        xaxis_title="Network Size (buses)",
        yaxis_title="Solve Time (s)",
        yaxis_type=yaxis_type,
        width=width,
        height=height,
        font={"family": FONT_FAMILY},
        legend={
            "x": 1.02,
            "y": 1,
            "xanchor": "left",
            "yanchor": "top",
        },
        margin={"r": 150},
    )

    return fig


def build_pass_fail_bar_chart(
    pass_fail_summary: dict[str, int],
    benchmark_label: str,
    *,
    width: int = FULL_WIDTH_PX,
    height: int = DEFAULT_HEIGHT_PX,
) -> go.Figure:
    """Build a bar chart showing pass counts per tool for a benchmark.

    Used as a fallback when full timing data is unavailable.
    """
    tools = sorted(pass_fail_summary.keys())
    counts = [pass_fail_summary[t] for t in tools]
    colors = [TOOL_COLORS.get(t, "#333333") for t in tools]

    fig = go.Figure(
        data=[
            go.Bar(
                x=tools,
                y=counts,
                marker_color=colors,
            )
        ]
    )

    fig.update_layout(
        title=f"Scalability — {benchmark_label} (pass count)",
        xaxis_title="Tool",
        yaxis_title="Tests Passed",
        width=width,
        height=height,
        font={"family": FONT_FAMILY},
    )

    return fig


def render_scalability_plots(
    *,
    test_results_data: TestResultsData,
    **_kwargs: object,
) -> list[ChartOutput]:
    """Top-level renderer: produce scalability charts from test results.

    Graceful degradation:
      - Full timing data → one line plot per benchmark type
      - Pass/fail only → one bar chart per benchmark type
      - No data → empty list
    """
    assessment = assess_scalability_data(test_results_data.timing_records)

    if assessment.tier == ScalabilityDataTier.NO_DATA:
        return []

    if assessment.tier == ScalabilityDataTier.PASS_FAIL_ONLY:
        outputs: list[ChartOutput] = []
        for bench_type, tool_counts in sorted(assessment.pass_fail_summary.items()):
            fig = build_pass_fail_bar_chart(tool_counts, bench_type)
            outputs.append(
                ChartOutput(
                    chart_id=scalability_chart_id(bench_type),
                    chart_type=ChartType.LINE,
                    subject=f"scalability-{bench_type}",
                    figure=fig,
                    data_source="test-results.json",
                    title=f"Scalability — {bench_type} (pass count)",
                )
            )
        return outputs

    # FULL_TIMING tier
    groups = group_timing_by_benchmark(assessment.timing_records)
    outputs = []
    for group in groups:
        fig = build_line_plot(group)
        outputs.append(
            ChartOutput(
                chart_id=scalability_chart_id(group.benchmark_type),
                chart_type=ChartType.LINE,
                subject=f"scalability-{group.benchmark_type}",
                figure=fig,
                data_source="test-results.json",
                title=f"Scalability — {group.benchmark_type}",
            )
        )

    return outputs


# Register with the chart pipeline
register_renderer("line", render_scalability_plots)
