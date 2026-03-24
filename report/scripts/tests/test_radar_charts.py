"""Tests for the radar chart renderer (PRD 02/02)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import (
    ChartType,
    DEFAULT_HEIGHT_PX,
    FULL_WIDTH_PX,
    GradesData,
    PER_TOOL_WIDTH_PX,
    TOOL_COLORS,
)
from renderers.radar import (
    TIER_TICKS,
    configure_polar_layout,
    render_radar_charts,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TOOLS = [
    "pypsa",
    "pandapower",
    "gridcal",
    "powermodels",
    "powersimulations",
    "matpower",
]
CRITERIA = [
    "gate",
    "expressiveness",
    "extensibility",
    "scalability",
    "accessibility",
    "maturity",
]

# Deterministic numeric tiers (6 tools x 6 criteria), values 0-3
_TIER_VALUES = [
    [3.0, 3.0, 2.0, 2.0, 1.0, 1.0],
    [3.0, 2.0, 2.0, 1.0, 1.0, 0.0],
    [2.0, 2.0, 1.0, 1.0, 0.0, 0.0],
    [2.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
]

_TIER_MAP = {
    3.0: "Strong",
    2.0: "Adequate",
    1.0: "Weak",
    0.0: "Failing",
}


@pytest.fixture()
def grades_data() -> GradesData:
    """Build a GradesData fixture with deterministic tiers."""
    data: dict[str, dict[str, float]] = {}
    tier_labels: dict[str, dict[str, str]] = {}

    for ti, tool in enumerate(TOOLS):
        tier_labels[tool] = {}
        for ci, criterion in enumerate(CRITERIA):
            val = _TIER_VALUES[ti][ci]
            data.setdefault(criterion, {})[tool] = val
            tier_labels[tool][criterion] = _TIER_MAP[val]

    df = pd.DataFrame(data).T.reindex(index=CRITERIA, columns=TOOLS)

    return GradesData(
        df=df,
        tier_labels=tier_labels,
        criteria=CRITERIA,
        tools=TOOLS,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_radar_charts_returns_seven(grades_data: GradesData) -> None:
    """render_radar_charts should return exactly 7 ChartOutput objects."""
    outputs = render_radar_charts(grades_data)
    assert len(outputs) == 7


def test_per_tool_radar_chart_ids(grades_data: GradesData) -> None:
    """First 6 outputs should have chart_id = radar_<tool>."""
    outputs = render_radar_charts(grades_data)
    per_tool = outputs[:6]
    expected_ids = [f"radar_{t}" for t in TOOLS]
    assert [o.chart_id for o in per_tool] == expected_ids


def test_overlay_radar_chart_id(grades_data: GradesData) -> None:
    """Last output should be the overlay with chart_id 'radar_overlay'."""
    outputs = render_radar_charts(grades_data)
    assert outputs[-1].chart_id == "radar_overlay"


def test_per_tool_radar_single_trace(grades_data: GradesData) -> None:
    """Each per-tool radar figure should contain exactly one trace."""
    outputs = render_radar_charts(grades_data)
    for out in outputs[:6]:
        assert len(out.figure.data) == 1


def test_overlay_radar_six_traces(grades_data: GradesData) -> None:
    """The overlay radar should contain exactly 6 traces."""
    outputs = render_radar_charts(grades_data)
    overlay = outputs[-1]
    assert len(overlay.figure.data) == 6


def test_per_tool_radar_values_match_grades(grades_data: GradesData) -> None:
    """The r values in each per-tool radar should match the grades DataFrame."""
    outputs = render_radar_charts(grades_data)
    for ti, tool in enumerate(TOOLS):
        trace = outputs[ti].figure.data[0]
        expected = [float(grades_data.df.loc[c, tool]) for c in CRITERIA]
        # trace.r has the polygon closed (first value appended)
        actual = list(trace.r[: len(CRITERIA)])
        assert actual == expected, f"Mismatch for {tool}"


def test_overlay_radar_has_legend(grades_data: GradesData) -> None:
    """The overlay figure layout should have showlegend=True."""
    outputs = render_radar_charts(grades_data)
    overlay = outputs[-1]
    assert overlay.figure.layout.showlegend is True


def test_overlay_radar_fill_opacity(grades_data: GradesData) -> None:
    """Each trace in the overlay should have opacity=0.3."""
    outputs = render_radar_charts(grades_data)
    overlay = outputs[-1]
    for trace in overlay.figure.data:
        assert trace.opacity == pytest.approx(0.3)


def test_polar_layout_has_grade_ticks() -> None:
    """configure_polar_layout should set radial tick values 0–4 with letter labels."""
    import plotly.graph_objects as go

    fig = go.Figure()
    configure_polar_layout(fig, CRITERIA)
    radial = fig.layout.polar.radialaxis
    assert list(radial.tickvals) == list(TIER_TICKS.keys())
    assert list(radial.ticktext) == list(TIER_TICKS.values())


def test_polar_layout_angular_labels() -> None:
    """configure_polar_layout should set angular axis category array to criteria."""
    import plotly.graph_objects as go

    fig = go.Figure()
    configure_polar_layout(fig, CRITERIA)
    angular = fig.layout.polar.angularaxis
    assert list(angular.categoryarray) == CRITERIA


def test_per_tool_radar_dimensions(grades_data: GradesData) -> None:
    """Per-tool radars should use PER_TOOL_WIDTH_PX x DEFAULT_HEIGHT_PX."""
    outputs = render_radar_charts(grades_data)
    for out in outputs[:6]:
        assert out.figure.layout.width == PER_TOOL_WIDTH_PX
        assert out.figure.layout.height == DEFAULT_HEIGHT_PX


def test_overlay_radar_dimensions(grades_data: GradesData) -> None:
    """Overlay radar should use FULL_WIDTH_PX x DEFAULT_HEIGHT_PX."""
    outputs = render_radar_charts(grades_data)
    overlay = outputs[-1]
    assert overlay.figure.layout.width == FULL_WIDTH_PX
    assert overlay.figure.layout.height == DEFAULT_HEIGHT_PX


def test_radar_chart_types_in_output(grades_data: GradesData) -> None:
    """All chart outputs should have chart_type = ChartType.RADAR."""
    outputs = render_radar_charts(grades_data)
    for out in outputs:
        assert out.chart_type == ChartType.RADAR


def test_radar_data_source_in_output(grades_data: GradesData) -> None:
    """All chart outputs should have data_source = 'grades.json'."""
    outputs = render_radar_charts(grades_data)
    for out in outputs:
        assert out.data_source == "grades.json"


def test_per_tool_radar_uses_tool_color(grades_data: GradesData) -> None:
    """Each per-tool radar trace should use the correct TOOL_COLORS color."""
    outputs = render_radar_charts(grades_data)
    for ti, tool in enumerate(TOOLS):
        trace = outputs[ti].figure.data[0]
        expected_color = TOOL_COLORS[tool]
        assert trace.line.color == expected_color, f"Color mismatch for {tool}"
