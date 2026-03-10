"""Shared types and visual constants for chart generation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

import pandas as pd
import plotly.graph_objects as go


class ToolName(StrEnum):
    PYPSA = "pypsa"
    PANDAPOWER = "pandapower"
    GRIDCAL = "gridcal"
    POWERMODELS = "powermodels"
    POWERSIMULATIONS = "powersimulations"
    MATPOWER = "matpower"


class ChartType(StrEnum):
    RADAR = "radar"
    HEATMAP = "heatmap"
    MATRIX = "matrix"
    LINE = "line"


class ExportFormat(StrEnum):
    SVG = "svg"
    PNG = "png"


# Visual constants
TOOL_COLORS: dict[str, str] = {
    "pypsa": "#1f77b4",
    "pandapower": "#ff7f0e",
    "gridcal": "#2ca02c",
    "powermodels": "#d62728",
    "powersimulations": "#9467bd",
    "matpower": "#8c564b",
}

FONT_FAMILY: str = "Inter, sans-serif"
FULL_WIDTH_PX: int = 800
PER_TOOL_WIDTH_PX: int = 500
DEFAULT_HEIGHT_PX: int = 500


@dataclass(frozen=True)
class GradesData:
    """Processed grades data with numeric DataFrame and letter grades."""

    df: pd.DataFrame
    letter_grades: dict[str, dict[str, str]]
    criteria: list[str]
    tools: list[str]


@dataclass(frozen=True)
class TimingRecord:
    """A single timing measurement from a benchmark run."""

    tool: str
    benchmark_type: str
    network_size: int
    solve_time_seconds: float
    status: str


@dataclass(frozen=True)
class TestResultsData:
    """Processed test results with pass/fail/skip matrix."""

    matrix_df: pd.DataFrame
    suite_grouping: dict[str, str]
    tools: list[str]
    test_ids: list[str]
    timing_records: list[TimingRecord]


@dataclass(frozen=True)
class ChartManifestEntry:
    """A single entry in the chart manifest."""

    id: str
    type: str
    subject: str
    files: dict[str, str]
    data_source: str
    title: str


@dataclass(frozen=True)
class ChartManifest:
    """The full chart manifest."""

    charts: list[ChartManifestEntry]


@dataclass(frozen=True)
class ChartOutput:
    """Output from a chart renderer: a Plotly figure plus metadata."""

    chart_id: str
    chart_type: ChartType
    subject: str
    figure: go.Figure
    data_source: str
    title: str


ChartRendererFn = Callable[..., list[ChartOutput]]
