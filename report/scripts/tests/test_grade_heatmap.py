"""Tests for the grade comparison heatmap renderer (PRD 02/03)."""

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
    DEFAULT_HEIGHT_PX,
    FULL_WIDTH_PX,
    GradesData,
)
from generate_charts import _RENDERERS


@pytest.fixture(autouse=True)
def _clear_renderers():
    """Reset the renderer registry before/after each test."""
    saved = dict(_RENDERERS)
    _RENDERERS.clear()
    yield
    _RENDERERS.clear()
    _RENDERERS.update(saved)


@pytest.fixture()
def sample_grades_data() -> GradesData:
    """Build a 6-tool x 6-criteria GradesData for testing."""
    tools = [
        "pypsa",
        "pandapower",
        "gridcal",
        "powermodels",
        "powersimulations",
        "matpower",
    ]
    criteria = [
        "gate",
        "expressiveness",
        "extensibility",
        "scalability",
        "accessibility",
        "maturity",
    ]

    # Numeric tiers: mix of values across the 0-3 range
    numeric_values = {
        "pypsa": [3.0, 3.0, 2.0, 2.0, 3.0, 2.0],
        "pandapower": [3.0, 2.0, 2.0, 1.0, 3.0, 2.0],
        "gridcal": [2.0, 1.0, 1.0, 0.0, 2.0, 1.0],
        "powermodels": [3.0, 2.0, 3.0, 3.0, 1.0, 1.0],
        "powersimulations": [2.0, 2.0, 2.0, 2.0, 1.0, 1.0],
        "matpower": [3.0, 2.0, 0.0, 0.0, 3.0, 3.0],
    }

    tier_values = {
        "pypsa": ["Strong", "Strong", "Adequate", "Adequate", "Strong", "Adequate"],
        "pandapower": ["Strong", "Adequate", "Adequate", "Weak", "Strong", "Adequate"],
        "gridcal": ["Adequate", "Weak", "Weak", "Failing", "Adequate", "Weak"],
        "powermodels": ["Strong", "Adequate", "Strong", "Strong", "Weak", "Weak"],
        "powersimulations": [
            "Adequate",
            "Adequate",
            "Adequate",
            "Adequate",
            "Weak",
            "Weak",
        ],
        "matpower": ["Strong", "Adequate", "Failing", "Failing", "Strong", "Strong"],
    }

    # Build DataFrame: rows=criteria, columns=tools
    data = {}
    for tool in tools:
        data[tool] = numeric_values[tool]
    df = pd.DataFrame(data, index=criteria)

    # Build tier_labels dict: tool -> criterion -> tier
    tier_labels = {}
    for tool in tools:
        tier_labels[tool] = dict(zip(criteria, tier_values[tool]))

    return GradesData(df=df, tier_labels=tier_labels, criteria=criteria, tools=tools)


# Import the module under test (triggers register_renderer)
from renderers.heatmap import (  # noqa: E402
    annotation_font_color,
    build_tier_annotations,
    build_heatmap_figure,
    tier_colorscale_to_plotly,
    TIER_COLOR_SCALE,
    render_grade_heatmap,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_grade_heatmap_returns_one(sample_grades_data: GradesData) -> None:
    """1. render_grade_heatmap returns exactly one ChartOutput."""
    results = render_grade_heatmap(sample_grades_data)
    assert len(results) == 1
    assert isinstance(results[0], ChartOutput)


def test_heatmap_chart_id(sample_grades_data: GradesData) -> None:
    """2. Chart ID is 'heatmap_grades'."""
    result = render_grade_heatmap(sample_grades_data)[0]
    assert result.chart_id == "heatmap_grades"


def test_heatmap_chart_type(sample_grades_data: GradesData) -> None:
    """3. Chart type is ChartType.HEATMAP."""
    result = render_grade_heatmap(sample_grades_data)[0]
    assert result.chart_type == ChartType.HEATMAP


def test_heatmap_data_source(sample_grades_data: GradesData) -> None:
    """4. Data source is 'grades.json'."""
    result = render_grade_heatmap(sample_grades_data)[0]
    assert result.data_source == "grades.json"


def test_heatmap_figure_has_heatmap_trace(sample_grades_data: GradesData) -> None:
    """5. The figure contains a Heatmap trace."""
    fig = build_heatmap_figure(sample_grades_data)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Heatmap)


def test_heatmap_z_values_match_grades(sample_grades_data: GradesData) -> None:
    """6. Z values in the heatmap trace match the numeric grades."""
    fig = build_heatmap_figure(sample_grades_data)
    trace = fig.data[0]
    z = list(trace.z)
    # z should be rows=tools, columns=criteria
    for row_idx, tool in enumerate(sample_grades_data.tools):
        for col_idx, criterion in enumerate(sample_grades_data.criteria):
            expected = float(sample_grades_data.df.loc[criterion, tool])
            assert z[row_idx][col_idx] == pytest.approx(expected), (
                f"Mismatch at {tool}/{criterion}"
            )


def test_heatmap_x_labels_are_criteria(sample_grades_data: GradesData) -> None:
    """7. X-axis labels are the criteria names."""
    fig = build_heatmap_figure(sample_grades_data)
    trace = fig.data[0]
    assert list(trace.x) == sample_grades_data.criteria


def test_heatmap_y_labels_are_tools(sample_grades_data: GradesData) -> None:
    """8. Y-axis labels are the tool names."""
    fig = build_heatmap_figure(sample_grades_data)
    trace = fig.data[0]
    assert list(trace.y) == sample_grades_data.tools


def test_heatmap_has_annotations(sample_grades_data: GradesData) -> None:
    """9. Heatmap has 36 annotations (6 tools x 6 criteria)."""
    fig = build_heatmap_figure(sample_grades_data)
    annotations = fig.layout.annotations
    assert len(annotations) == 36


def test_heatmap_annotations_show_tiers(sample_grades_data: GradesData) -> None:
    """10. Each annotation text is a valid tier label from the data."""
    annotations = build_tier_annotations(sample_grades_data)
    # Collect all tier labels from the fixture
    all_tiers = set()
    for tool_tiers in sample_grades_data.tier_labels.values():
        all_tiers.update(tool_tiers.values())

    for ann in annotations:
        assert ann["text"] in all_tiers, f"Unexpected annotation text: {ann['text']}"


def test_annotation_font_color_dark_cells() -> None:
    """11. Strong (>=2.5) and Failing (<=0.5) tiers get white font color."""
    assert annotation_font_color(3.0) == "#ffffff"  # Strong
    assert annotation_font_color(2.5) == "#ffffff"  # boundary
    assert annotation_font_color(0.0) == "#ffffff"  # Failing
    assert annotation_font_color(0.5) == "#ffffff"  # boundary


def test_annotation_font_color_light_cells() -> None:
    """12. Adequate and Weak tiers (0.5 < value < 2.5) get dark font color."""
    assert annotation_font_color(2.0) == "#1a1a1a"  # Adequate
    assert annotation_font_color(1.0) == "#1a1a1a"  # Weak
    assert annotation_font_color(1.5) == "#1a1a1a"  # mid-range


def test_heatmap_dimensions(sample_grades_data: GradesData) -> None:
    """13. Heatmap figure uses FULL_WIDTH_PX and DEFAULT_HEIGHT_PX."""
    fig = build_heatmap_figure(sample_grades_data)
    assert fig.layout.width == FULL_WIDTH_PX
    assert fig.layout.height == DEFAULT_HEIGHT_PX


def test_tier_colorscale_to_plotly_format() -> None:
    """14. tier_colorscale_to_plotly returns valid Plotly colorscale format."""
    result = tier_colorscale_to_plotly(TIER_COLOR_SCALE)
    assert len(result) == 4
    for entry in result:
        assert len(entry) == 2
        assert isinstance(entry[0], float)
        assert isinstance(entry[1], str)
    # First entry should be 0.0, last should be 1.0
    assert result[0][0] == 0.0
    assert result[-1][0] == 1.0


def test_heatmap_colorscale_bounds(sample_grades_data: GradesData) -> None:
    """15. Heatmap trace has zmin=0 and zmax=3 for consistent color mapping."""
    fig = build_heatmap_figure(sample_grades_data)
    trace = fig.data[0]
    assert trace.zmin == 0
    assert trace.zmax == 3
