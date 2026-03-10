"""Tests for the scalability benchmark line plots renderer (PRD 02/05)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import (
    ChartOutput,
    ChartType,
    TestResultsData,
    TimingRecord,
    TOOL_COLORS,
)
from generate_charts import _RENDERERS


@pytest.fixture(autouse=True)
def _clear_renderers():
    """Reset the renderer registry before each test, then re-register scalability."""
    _RENDERERS.clear()
    # Ensure the scalability module is imported (no-op after first call)
    import renderers.scalability  # noqa: F401

    # The initial import registers "line", but after clear() we need to re-register
    from renderers.scalability import render_scalability_plots

    if "line" not in _RENDERERS:
        from generate_charts import register_renderer

        register_renderer("line", render_scalability_plots)
    yield
    _RENDERERS.clear()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

TIMING_RECORDS_FULL: list[TimingRecord] = [
    TimingRecord(
        tool="pypsa",
        benchmark_type="acpf",
        network_size=14,
        solve_time_seconds=0.05,
        status="pass",
    ),
    TimingRecord(
        tool="pypsa",
        benchmark_type="acpf",
        network_size=118,
        solve_time_seconds=0.3,
        status="pass",
    ),
    TimingRecord(
        tool="pypsa",
        benchmark_type="acpf",
        network_size=300,
        solve_time_seconds=1.2,
        status="pass",
    ),
    TimingRecord(
        tool="pandapower",
        benchmark_type="acpf",
        network_size=14,
        solve_time_seconds=0.04,
        status="pass",
    ),
    TimingRecord(
        tool="pandapower",
        benchmark_type="acpf",
        network_size=118,
        solve_time_seconds=0.25,
        status="pass",
    ),
    TimingRecord(
        tool="pandapower",
        benchmark_type="acpf",
        network_size=300,
        solve_time_seconds=0.9,
        status="pass",
    ),
    TimingRecord(
        tool="pypsa",
        benchmark_type="dcopf",
        network_size=14,
        solve_time_seconds=0.02,
        status="pass",
    ),
    TimingRecord(
        tool="pypsa",
        benchmark_type="dcopf",
        network_size=118,
        solve_time_seconds=0.1,
        status="pass",
    ),
]

TIMING_RECORDS_PASS_FAIL: list[TimingRecord] = [
    TimingRecord(
        tool="pypsa",
        benchmark_type="acpf",
        network_size=14,
        solve_time_seconds=0.0,
        status="pass",
    ),
    TimingRecord(
        tool="pypsa",
        benchmark_type="acpf",
        network_size=118,
        solve_time_seconds=0.0,
        status="pass",
    ),
    TimingRecord(
        tool="pandapower",
        benchmark_type="acpf",
        network_size=14,
        solve_time_seconds=0.0,
        status="pass",
    ),
    TimingRecord(
        tool="pandapower",
        benchmark_type="acpf",
        network_size=118,
        solve_time_seconds=0.0,
        status="fail",
    ),
]


def _make_test_results_data(
    timing_records: list[TimingRecord] | None = None,
) -> TestResultsData:
    """Build a minimal TestResultsData with the given timing records."""
    return TestResultsData(
        matrix_df=pd.DataFrame({"toolA": ["pass"]}, index=["G-1"]),
        suite_grouping={"G-1": "gate"},
        tools=["toolA"],
        test_ids=["G-1"],
        timing_records=timing_records or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_scalability_with_full_timing() -> None:
    """1. render_scalability_plots returns charts when full timing data is present."""
    from renderers.scalability import render_scalability_plots

    trd = _make_test_results_data(TIMING_RECORDS_FULL)
    outputs = render_scalability_plots(test_results_data=trd)
    assert len(outputs) == 2  # acpf + dcopf
    assert all(isinstance(o, ChartOutput) for o in outputs)


def test_render_scalability_no_data() -> None:
    """2. render_scalability_plots returns empty list when no timing data."""
    from renderers.scalability import render_scalability_plots

    trd = _make_test_results_data([])
    outputs = render_scalability_plots(test_results_data=trd)
    assert outputs == []


def test_scalability_chart_ids() -> None:
    """3. Chart IDs follow the line_scalability-{type} pattern."""
    from renderers.scalability import render_scalability_plots

    trd = _make_test_results_data(TIMING_RECORDS_FULL)
    outputs = render_scalability_plots(test_results_data=trd)
    ids = {o.chart_id for o in outputs}
    assert "line_scalability-acpf" in ids
    assert "line_scalability-dcopf" in ids


def test_scalability_chart_type() -> None:
    """4. All scalability charts have chart_type LINE."""
    from renderers.scalability import render_scalability_plots

    trd = _make_test_results_data(TIMING_RECORDS_FULL)
    outputs = render_scalability_plots(test_results_data=trd)
    assert all(o.chart_type == ChartType.LINE for o in outputs)


def test_scalability_data_source() -> None:
    """5. All scalability charts cite test-results.json as data source."""
    from renderers.scalability import render_scalability_plots

    trd = _make_test_results_data(TIMING_RECORDS_FULL)
    outputs = render_scalability_plots(test_results_data=trd)
    assert all(o.data_source == "test-results.json" for o in outputs)


def test_assess_scalability_full_timing() -> None:
    """6. assess_scalability_data returns FULL_TIMING when timing is present."""
    from renderers.scalability import ScalabilityDataTier, assess_scalability_data

    assessment = assess_scalability_data(TIMING_RECORDS_FULL)
    assert assessment.tier == ScalabilityDataTier.FULL_TIMING


def test_assess_scalability_no_data() -> None:
    """7. assess_scalability_data returns NO_DATA for empty list."""
    from renderers.scalability import ScalabilityDataTier, assess_scalability_data

    assessment = assess_scalability_data([])
    assert assessment.tier == ScalabilityDataTier.NO_DATA


def test_group_timing_by_benchmark() -> None:
    """8. group_timing_by_benchmark produces correct groups and series."""
    from renderers.scalability import group_timing_by_benchmark

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    assert len(groups) == 2

    acpf_group = next(g for g in groups if g.benchmark_type == "acpf")
    assert len(acpf_group.series) == 2  # pypsa + pandapower

    pypsa_series = next(s for s in acpf_group.series if s.tool == "pypsa")
    assert pypsa_series.network_sizes == [14, 118, 300]
    assert pypsa_series.solve_times == [0.05, 0.3, 1.2]


def test_line_plot_traces_per_tool() -> None:
    """9. build_line_plot creates one trace per tool in the benchmark group."""
    from renderers.scalability import build_line_plot, group_timing_by_benchmark

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    acpf_group = next(g for g in groups if g.benchmark_type == "acpf")
    fig = build_line_plot(acpf_group)
    assert len(fig.data) == 2  # pypsa + pandapower


def test_line_plot_log_y_axis() -> None:
    """10. build_line_plot uses log y-axis by default."""
    from renderers.scalability import build_line_plot, group_timing_by_benchmark

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    fig = build_line_plot(groups[0])
    assert fig.layout.yaxis.type == "log"


def test_line_plot_tool_colors() -> None:
    """11. Line plot traces use the correct tool colors from TOOL_COLORS."""
    from renderers.scalability import build_line_plot, group_timing_by_benchmark

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    acpf_group = next(g for g in groups if g.benchmark_type == "acpf")
    fig = build_line_plot(acpf_group)

    for trace in fig.data:
        expected_color = TOOL_COLORS[trace.name]
        assert trace.line.color == expected_color


def test_line_plot_tool_markers() -> None:
    """12. Line plot traces use the correct marker symbols from TOOL_MARKERS."""
    from renderers.scalability import (
        TOOL_MARKERS,
        build_line_plot,
        group_timing_by_benchmark,
    )

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    acpf_group = next(g for g in groups if g.benchmark_type == "acpf")
    fig = build_line_plot(acpf_group)

    for trace in fig.data:
        expected_marker = TOOL_MARKERS[trace.name]
        assert trace.marker.symbol == expected_marker


def test_line_plot_legend_outside() -> None:
    """13. Legend is positioned outside the plot area (x >= 1.0)."""
    from renderers.scalability import build_line_plot, group_timing_by_benchmark

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    fig = build_line_plot(groups[0])
    assert fig.layout.legend.x >= 1.0


def test_pass_fail_bar_chart_fallback() -> None:
    """14. Pass/fail data produces bar charts instead of line plots."""
    from renderers.scalability import render_scalability_plots

    trd = _make_test_results_data(TIMING_RECORDS_PASS_FAIL)
    outputs = render_scalability_plots(test_results_data=trd)
    assert len(outputs) >= 1
    # The figure should contain Bar traces, not Scatter
    for output in outputs:
        assert any(isinstance(trace, go.Bar) for trace in output.figure.data)


def test_scalability_chart_id_format() -> None:
    """15. scalability_chart_id follows the expected format."""
    from renderers.scalability import scalability_chart_id

    assert scalability_chart_id("acpf") == "line_scalability-acpf"
    assert scalability_chart_id("dcopf") == "line_scalability-dcopf"


def test_line_plot_dimensions() -> None:
    """16. Line plots use the default dimensions from chart_types."""
    from renderers.scalability import build_line_plot, group_timing_by_benchmark

    from chart_types import DEFAULT_HEIGHT_PX, FULL_WIDTH_PX

    groups = group_timing_by_benchmark(TIMING_RECORDS_FULL)
    fig = build_line_plot(groups[0])
    assert fig.layout.width == FULL_WIDTH_PX
    assert fig.layout.height == DEFAULT_HEIGHT_PX
