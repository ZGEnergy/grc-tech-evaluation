"""Tests for the test pass/fail matrix renderer (PRD 02/04)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import ChartType, TestResultsData  # noqa: E402
from generate_charts import _RENDERERS  # noqa: E402

# Import renderer module (triggers register_renderer at module level)
from renderers.matrix import (  # noqa: E402
    build_categorical_colorscale,
    build_matrix_figure,
    build_suite_separators,
    decide_matrix_split,
    encode_status_matrix,
    render_test_matrix,
)

# ---------------------------------------------------------------------------
# Inline fixture helpers
# ---------------------------------------------------------------------------

SMALL_TEST_RESULTS_RAW: dict = {
    "suites": ["gate", "expr"],
    "tools": [
        {
            "tool": "toolA",
            "total_pass": 2,
            "total_fail": 0,
            "total_skip": 0,
            "by_suite": [
                {
                    "suite": "gate",
                    "pass": 1,
                    "fail": 0,
                    "skip": 0,
                    "tests": [{"id": "G-1", "name": "Ingest", "result": "pass"}],
                },
                {
                    "suite": "expr",
                    "pass": 1,
                    "fail": 0,
                    "skip": 0,
                    "tests": [{"id": "A-1", "name": "DCPF", "result": "pass"}],
                },
            ],
        },
        {
            "tool": "toolB",
            "total_pass": 1,
            "total_fail": 1,
            "total_skip": 0,
            "by_suite": [
                {
                    "suite": "gate",
                    "pass": 1,
                    "fail": 0,
                    "skip": 0,
                    "tests": [{"id": "G-1", "name": "Ingest", "result": "pass"}],
                },
                {
                    "suite": "expr",
                    "pass": 0,
                    "fail": 1,
                    "skip": 0,
                    "tests": [{"id": "A-1", "name": "DCPF", "result": "fail"}],
                },
            ],
        },
    ],
}


def _build_small_test_results() -> TestResultsData:
    """Build a small TestResultsData with 2 tests x 2 tools."""
    from generate_charts import build_test_results_data

    return build_test_results_data(SMALL_TEST_RESULTS_RAW)


def _build_large_test_results(n_tests: int = 50) -> TestResultsData:
    """Build a TestResultsData with many tests to trigger splitting."""
    tools = ["toolA", "toolB"]
    suite_names = ["gate", "expr", "scale"]
    tests_per_suite = n_tests // len(suite_names)
    remainder = n_tests - tests_per_suite * len(suite_names)

    all_test_ids: list[str] = []
    suite_grouping: dict[str, str] = {}
    matrix_rows: dict[str, dict[str, str]] = {}

    idx = 0
    for s_i, suite in enumerate(suite_names):
        count = tests_per_suite + (1 if s_i < remainder else 0)
        for j in range(count):
            tid = f"{suite[0].upper()}-{idx}"
            all_test_ids.append(tid)
            suite_grouping[tid] = suite
            matrix_rows[tid] = {
                "toolA": "pass" if j % 3 != 0 else "fail",
                "toolB": "skip" if j % 5 == 0 else "pass",
            }
            idx += 1

    matrix_df = pd.DataFrame.from_dict(matrix_rows, orient="index")
    matrix_df = matrix_df.reindex(index=all_test_ids, columns=tools)

    return TestResultsData(
        matrix_df=matrix_df,
        suite_grouping=suite_grouping,
        tools=tools,
        test_ids=all_test_ids,
        timing_records=[],
    )


@pytest.fixture(autouse=True)
def _clear_renderers():
    """Reset the renderer registry before each test, then re-register matrix."""
    saved = dict(_RENDERERS)
    _RENDERERS.clear()
    # Re-import to re-register
    from renderers.matrix import render_test_matrix

    if "matrix" not in _RENDERERS:
        from generate_charts import register_renderer

        register_renderer("matrix", render_test_matrix)
    yield
    _RENDERERS.clear()
    _RENDERERS.update(saved)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_test_matrix_returns_nonempty() -> None:
    """1. render_test_matrix returns a non-empty list."""
    tr = _build_small_test_results()
    results = render_test_matrix(test_results_data=tr)
    assert len(results) > 0


def test_matrix_chart_type() -> None:
    """2. All returned charts have ChartType.MATRIX."""
    tr = _build_small_test_results()
    results = render_test_matrix(test_results_data=tr)
    for chart in results:
        assert chart.chart_type == ChartType.MATRIX


def test_matrix_data_source() -> None:
    """3. All returned charts have data_source 'test-results.json'."""
    tr = _build_small_test_results()
    results = render_test_matrix(test_results_data=tr)
    for chart in results:
        assert chart.data_source == "test-results.json"


def test_single_matrix_when_few_tests() -> None:
    """4. Single chart with id 'matrix_test-results' when tests <= 40."""
    tr = _build_small_test_results()
    results = render_test_matrix(test_results_data=tr)
    assert len(results) == 1
    assert results[0].chart_id == "matrix_test-results"


def test_split_matrix_when_many_tests() -> None:
    """5. Multiple charts when tests > 40, one per suite."""
    tr = _build_large_test_results(n_tests=50)
    results = render_test_matrix(test_results_data=tr)
    assert len(results) > 1
    # Each chart id should contain a suite name
    for chart in results:
        assert chart.chart_id.startswith("matrix_test-results-")


def test_decide_matrix_split_below_threshold() -> None:
    """6. decide_matrix_split returns False when tests <= threshold."""
    tr = _build_small_test_results()
    assert decide_matrix_split(tr, max_tests_per_chart=40) is False


def test_decide_matrix_split_above_threshold() -> None:
    """7. decide_matrix_split returns True when tests > threshold."""
    tr = _build_large_test_results(n_tests=50)
    assert decide_matrix_split(tr, max_tests_per_chart=40) is True


def test_encode_status_matrix_values() -> None:
    """8. encode_status_matrix maps pass->2, skip->1, fail->0."""
    df = pd.DataFrame({"t1": ["pass", "fail", "skip"]}, index=["a", "b", "c"])
    encoded = encode_status_matrix(df)
    assert encoded.loc["a", "t1"] == 2
    assert encoded.loc["b", "t1"] == 0
    assert encoded.loc["c", "t1"] == 1


def test_categorical_colorscale_three_colors() -> None:
    """9. build_categorical_colorscale returns exactly 3 color stops."""
    cs = build_categorical_colorscale()
    assert len(cs) == 3
    # Check boundaries
    assert cs[0][0] == 0.0
    assert cs[-1][0] == 1.0


def test_matrix_y_labels_are_tools() -> None:
    """10. The heatmap y-axis labels correspond to tool names."""
    tr = _build_small_test_results()
    fig = build_matrix_figure(tr, title="Test")
    heatmap = fig.data[0]
    assert list(heatmap.y) == tr.tools


def test_matrix_x_labels_are_test_ids() -> None:
    """11. The heatmap x-axis labels correspond to test IDs."""
    tr = _build_small_test_results()
    fig = build_matrix_figure(tr, title="Test")
    heatmap = fig.data[0]
    assert list(heatmap.x) == tr.test_ids


def test_suite_separators_at_boundaries() -> None:
    """12. build_suite_separators returns positions at suite transitions."""
    test_ids = ["G-1", "G-2", "A-1", "A-2"]
    suite_grouping = {"G-1": "gate", "G-2": "gate", "A-1": "expr", "A-2": "expr"}
    seps = build_suite_separators(test_ids, suite_grouping)
    assert len(seps) == 1
    assert seps[0] == pytest.approx(1.5)


def test_fallback_suite_summary_when_no_individual_tests() -> None:
    """13. render_test_matrix returns a fallback chart when test_ids is empty."""
    tr = TestResultsData(
        matrix_df=pd.DataFrame(),
        suite_grouping={},
        tools=["toolA", "toolB"],
        test_ids=[],
        timing_records=[],
    )
    results = render_test_matrix(test_results_data=tr)
    assert len(results) == 1
    assert "summary" in results[0].chart_id


def test_matrix_x_labels_rotated() -> None:
    """14. x-axis tick labels are rotated (negative angle)."""
    tr = _build_small_test_results()
    fig = build_matrix_figure(tr, title="Test")
    tick_angle = fig.layout.xaxis.tickangle
    assert tick_angle is not None
    assert tick_angle < 0
