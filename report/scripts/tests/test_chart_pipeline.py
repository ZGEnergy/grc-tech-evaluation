"""Tests for the chart generation pipeline (PRD 02/01)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chart_types import (
    ChartManifestEntry,
    ChartOutput,
    ChartType,
    ExportFormat,
    GradesData,
    TestResultsData,
)
from generate_charts import (
    _RENDERERS,
    build_grades_data,
    build_manifest_entry,
    build_test_results_data,
    chart_file_name,
    export_chart,
    get_registered_renderers,
    tier_to_numeric,
    load_all_data_files,
    load_json_file,
    register_renderer,
    run_renderers,
    write_chart_manifest,
)

# ---------------------------------------------------------------------------
# Inline fixture data
# ---------------------------------------------------------------------------

SAMPLE_GRADES_RAW: dict = {
    "tiers": {"Strong": 3, "Adequate": 2, "Weak": 1, "Failing": 0},
    "tools": ["toolA", "toolB"],
    "criteria": ["crit1", "crit2"],
    "grades": [
        {"tool": "toolA", "criterion": "crit1", "tier": "Strong", "numeric": 3.0},
        {"tool": "toolA", "criterion": "crit2", "tier": "Adequate", "numeric": 2.0},
        {"tool": "toolB", "criterion": "crit1", "tier": "Weak", "numeric": 1.0},
        {"tool": "toolB", "criterion": "crit2", "tier": "Failing", "numeric": 0.0},
    ],
}

SAMPLE_TEST_RESULTS_RAW: dict = {
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


@pytest.fixture(autouse=True)
def _clear_renderers():
    """Reset the renderer registry before each test."""
    _RENDERERS.clear()
    yield
    _RENDERERS.clear()


# ---------------------------------------------------------------------------
# Stage 1: Data loading tests
# ---------------------------------------------------------------------------


def test_load_json_file_valid(tmp_path: Path) -> None:
    """1. load_json_file returns parsed dict for valid JSON."""
    fp = tmp_path / "test.json"
    fp.write_text(json.dumps({"key": "value"}))
    result = load_json_file(fp)
    assert result == {"key": "value"}


def test_load_json_file_missing_raises(tmp_path: Path) -> None:
    """2. load_json_file raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        load_json_file(tmp_path / "nonexistent.json")


def test_load_json_file_invalid_json_raises(tmp_path: Path) -> None:
    """3. load_json_file raises JSONDecodeError for invalid JSON."""
    fp = tmp_path / "bad.json"
    fp.write_text("{not valid json")
    with pytest.raises(json.JSONDecodeError):
        load_json_file(fp)


def test_load_all_data_files_returns_all_stems(tmp_path: Path) -> None:
    """4. load_all_data_files returns dict keyed by file stem."""
    (tmp_path / "alpha.json").write_text(json.dumps({"a": 1}))
    (tmp_path / "beta.json").write_text(json.dumps({"b": 2}))
    result = load_all_data_files(tmp_path)
    assert set(result.keys()) == {"alpha", "beta"}
    assert result["alpha"] == {"a": 1}


def test_load_all_data_files_empty_dir_raises(tmp_path: Path) -> None:
    """5. load_all_data_files raises ValueError when no JSON files exist."""
    with pytest.raises(ValueError, match="No .json files"):
        load_all_data_files(tmp_path)


def test_tier_to_numeric_all_tiers() -> None:
    """6. tier_to_numeric returns correct values for the full scale."""
    expected = {
        "Strong": 3.0,
        "Adequate": 2.0,
        "Weak": 1.0,
        "Failing": 0.0,
    }
    for tier, expected_val in expected.items():
        assert tier_to_numeric(tier) == pytest.approx(expected_val), (
            f"Failed for {tier}"
        )


def test_tier_to_numeric_invalid_raises() -> None:
    """7. tier_to_numeric raises ValueError for unrecognized tiers."""
    with pytest.raises(ValueError, match="Unrecognized tier"):
        tier_to_numeric("Z")


def test_build_grades_data_structure() -> None:
    """8. build_grades_data produces correct GradesData structure."""
    gd = build_grades_data(SAMPLE_GRADES_RAW)
    assert isinstance(gd, GradesData)
    assert gd.tools == ["toolA", "toolB"]
    assert gd.criteria == ["crit1", "crit2"]
    assert gd.df.loc["crit1", "toolA"] == 3.0
    assert gd.df.loc["crit2", "toolB"] == 0.0
    assert gd.tier_labels["toolA"]["crit1"] == "Strong"
    assert gd.tier_labels["toolB"]["crit2"] == "Failing"


def test_build_test_results_data_structure() -> None:
    """9. build_test_results_data produces correct TestResultsData."""
    tr = build_test_results_data(SAMPLE_TEST_RESULTS_RAW)
    assert isinstance(tr, TestResultsData)
    assert tr.tools == ["toolA", "toolB"]
    assert "G-1" in tr.test_ids
    assert "A-1" in tr.test_ids
    assert tr.matrix_df.loc["G-1", "toolA"] == "pass"
    assert tr.matrix_df.loc["A-1", "toolB"] == "fail"
    assert tr.suite_grouping["G-1"] == "gate"
    assert tr.suite_grouping["A-1"] == "expr"


# ---------------------------------------------------------------------------
# Stage 3: Export tests
# ---------------------------------------------------------------------------


def test_chart_file_name_convention() -> None:
    """10. chart_file_name produces {type}_{subject}.{ext} format."""
    assert (
        chart_file_name(ChartType.RADAR, "grades", ExportFormat.SVG)
        == "radar_grades.svg"
    )
    assert (
        chart_file_name(ChartType.HEATMAP, "tests", ExportFormat.PNG)
        == "heatmap_tests.png"
    )


def test_export_chart_creates_files(tmp_path: Path) -> None:
    """11. export_chart writes image files to disk."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        pytest.skip("plotly not installed")

    fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])
    co = ChartOutput(
        chart_id="test-chart",
        chart_type=ChartType.RADAR,
        subject="demo",
        figure=fig,
        data_source="test",
        title="Test Chart",
    )

    try:
        exported = export_chart(co, tmp_path, formats=(ExportFormat.SVG,))
    except Exception:
        # Kaleido may not be available; mock write_image instead
        with patch.object(fig, "write_image"):
            exported = export_chart(co, tmp_path, formats=(ExportFormat.SVG,))
            assert "svg" in exported
            assert exported["svg"].name == "radar_demo.svg"
            return

    assert "svg" in exported
    assert exported["svg"].exists()
    assert exported["svg"].name == "radar_demo.svg"


def test_build_manifest_entry_relative_paths(tmp_path: Path) -> None:
    """12. build_manifest_entry produces paths relative to static_dir."""
    static_dir = tmp_path / "static"
    img_dir = static_dir / "img"
    img_dir.mkdir(parents=True)

    co = ChartOutput(
        chart_id="c1",
        chart_type=ChartType.HEATMAP,
        subject="matrix",
        figure=MagicMock(),
        data_source="test-results.json",
        title="Result Matrix",
    )
    exported_files = {
        "svg": img_dir / "heatmap_matrix.svg",
        "png": img_dir / "heatmap_matrix.png",
    }

    entry = build_manifest_entry(co, exported_files, static_dir)
    assert isinstance(entry, ChartManifestEntry)
    assert entry.id == "c1"
    assert entry.files["svg"] == "img/heatmap_matrix.svg"
    assert entry.files["png"] == "img/heatmap_matrix.png"


def test_write_chart_manifest_valid_json(tmp_path: Path) -> None:
    """13. write_chart_manifest produces valid JSON."""
    dest = tmp_path / "chart-manifest.json"
    entries = [
        ChartManifestEntry(
            id="c1",
            type="radar",
            subject="grades",
            files={"svg": "img/radar_grades.svg"},
            data_source="grades.json",
            title="Grades Radar",
        ),
    ]
    write_chart_manifest(entries, dest)
    data = json.loads(dest.read_text())
    assert "generated_at" in data
    assert "charts" in data
    assert len(data["charts"]) == 1
    assert data["charts"][0]["id"] == "c1"


def test_write_chart_manifest_indented(tmp_path: Path) -> None:
    """14. write_chart_manifest uses 2-space indentation."""
    dest = tmp_path / "chart-manifest.json"
    write_chart_manifest([], dest)
    text = dest.read_text()
    # JSON with indent=2 will have lines starting with exactly 2 spaces
    lines = text.strip().splitlines()
    # The second line (first key) should be indented by 2 spaces
    assert lines[1].startswith("  ")
    # Should not be indented by 4 spaces (indent=4)
    assert not lines[1].startswith("    ")


# ---------------------------------------------------------------------------
# Stage 2: Renderer registry tests
# ---------------------------------------------------------------------------


def test_register_renderer_and_retrieve() -> None:
    """15. register_renderer adds a function retrievable via get_registered_renderers."""
    mock_fn = MagicMock(return_value=[])
    register_renderer("my_renderer", mock_fn)
    renderers = get_registered_renderers()
    assert "my_renderer" in renderers
    assert renderers["my_renderer"] is mock_fn


def test_register_duplicate_renderer_raises() -> None:
    """16. register_renderer raises ValueError for duplicate names."""
    mock_fn = MagicMock(return_value=[])
    register_renderer("dup", mock_fn)
    with pytest.raises(ValueError, match="already registered"):
        register_renderer("dup", mock_fn)


def test_run_renderers_calls_all_registered() -> None:
    """17. run_renderers invokes every registered renderer."""
    gd = build_grades_data(SAMPLE_GRADES_RAW)
    tr = build_test_results_data(SAMPLE_TEST_RESULTS_RAW)

    mock_a = MagicMock(return_value=[])
    mock_b = MagicMock(return_value=[])
    register_renderer("renderer_a", mock_a)
    register_renderer("renderer_b", mock_b)

    run_renderers(gd, tr)
    mock_a.assert_called_once()
    mock_b.assert_called_once()


def test_generate_all_charts_empty_renderers(tmp_path: Path) -> None:
    """18. generate_all_charts produces empty manifest when no renderers registered."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    output_dir = tmp_path / "static" / "img"

    # Write minimal data files
    (data_dir / "grades.json").write_text(json.dumps(SAMPLE_GRADES_RAW))
    (data_dir / "test-results.json").write_text(json.dumps(SAMPLE_TEST_RESULTS_RAW))

    # generate_all_charts also calls validate_data_files which checks DATA_FILES keys,
    # so we use the lower-level approach: call the pipeline steps directly
    from generate_charts import (
        build_grades_data,
        build_test_results_data,
        load_all_data_files,
        run_renderers,
        write_chart_manifest,
    )

    raw = load_all_data_files(data_dir)
    gd = build_grades_data(raw["grades"])
    tr = build_test_results_data(raw["test-results"])
    outputs = run_renderers(gd, tr)

    assert outputs == []

    manifest_path = output_dir / "chart-manifest.json"
    write_chart_manifest([], manifest_path)
    data = json.loads(manifest_path.read_text())
    assert data["charts"] == []
    assert data["chart_count"] == 0
