"""Integration tests for the chart pipeline and manifest validation (PRD 02/06).

These tests run the full chart pipeline against the committed data files
and verify that all expected outputs are produced correctly. They also
test the validation module independently.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure scripts/ is importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_charts import (  # noqa: E402
    validate_manifest,
    validate_manifest_schema,
    validate_png_file,
    validate_svg_file,
)

# ---------------------------------------------------------------------------
# Locate real data directory relative to this file
# ---------------------------------------------------------------------------
REPORT_DIR = SCRIPTS_DIR.parent
DATA_DIR = REPORT_DIR / "data"

# Minimal valid SVG content for mocked image export
_STUB_SVG = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
    "<rect width='100' height='100'/></svg>"
)

# Minimal valid PNG: 8-byte magic + IHDR chunk + IEND chunk
_STUB_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _stub_write_image(self: object, **kwargs: object) -> None:
    """Mock write_image that writes minimal valid SVG or PNG stubs."""
    file_path = str(kwargs.get("file", ""))
    fmt = str(kwargs.get("format", ""))
    if not file_path:
        return
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "svg" or file_path.endswith(".svg"):
        path.write_text(_STUB_SVG)
    elif fmt == "png" or file_path.endswith(".png"):
        path.write_bytes(_STUB_PNG)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pipeline_output(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the full chart pipeline once and return the temporary report dir.

    Copies real data files to a temp directory, monkeypatches module-level
    paths in generate_charts, imports all renderers, runs the pipeline
    with mocked image export (no Chrome/Kaleido needed), and yields
    the temp report root. Shared across all integration tests via session scope.
    """
    tmp_report = tmp_path_factory.mktemp("report")
    tmp_data = tmp_report / "data"
    tmp_static = tmp_report / "static"
    tmp_img = tmp_static / "img"
    tmp_data.mkdir(parents=True)
    tmp_img.mkdir(parents=True)

    # Copy all real data files
    for json_file in DATA_DIR.glob("*.json"):
        shutil.copy2(json_file, tmp_data / json_file.name)

    # Monkeypatch module-level paths before running the pipeline
    import generate_charts

    orig_static = generate_charts.STATIC_DIR
    orig_img = generate_charts.IMG_DIR
    orig_manifest = generate_charts.MANIFEST_PATH

    generate_charts.STATIC_DIR = tmp_static
    generate_charts.IMG_DIR = tmp_img
    generate_charts.MANIFEST_PATH = tmp_img / "chart-manifest.json"

    try:
        # Ensure renderer modules are importable, then clear any stale/mock
        # registrations left by other test modules and reload to re-register.
        import importlib

        import renderers.heatmap  # noqa: F401
        import renderers.matrix  # noqa: F401
        import renderers.radar  # noqa: F401
        import renderers.scalability  # noqa: F401

        generate_charts._RENDERERS.clear()
        for mod_name in (
            "renderers.radar",
            "renderers.heatmap",
            "renderers.matrix",
            "renderers.scalability",
        ):
            importlib.reload(sys.modules[mod_name])

        # Mock write_image to avoid requiring Chrome/Kaleido.
        # Writes minimal valid SVG/PNG stubs so format validation passes.
        import plotly.graph_objects as go

        with patch.object(go.Figure, "write_image", _stub_write_image):
            generate_charts.generate_all_charts(data_dir=tmp_data, output_dir=tmp_img)
    finally:
        generate_charts.STATIC_DIR = orig_static
        generate_charts.IMG_DIR = orig_img
        generate_charts.MANIFEST_PATH = orig_manifest

    return tmp_report


@pytest.fixture(scope="session")
def manifest_path(pipeline_output: Path) -> Path:
    """Return path to the generated chart-manifest.json."""
    return pipeline_output / "static" / "img" / "chart-manifest.json"


@pytest.fixture(scope="session")
def manifest_data(manifest_path: Path) -> dict:
    """Return parsed manifest JSON."""
    with open(manifest_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def static_dir(pipeline_output: Path) -> Path:
    """Return the static/ directory of the pipeline output."""
    return pipeline_output / "static"


# ---------------------------------------------------------------------------
# Integration tests: pipeline output validation
# ---------------------------------------------------------------------------


def test_integration_pipeline_produces_manifest(manifest_path: Path) -> None:
    """1. Run generate_all_charts() and verify chart-manifest.json exists."""
    assert manifest_path.exists(), f"Manifest not found at {manifest_path}"


def test_integration_manifest_is_valid_json(manifest_path: Path) -> None:
    """2. Verify that the produced chart-manifest.json is parseable as valid JSON."""
    text = manifest_path.read_text()
    data = json.loads(text)
    assert isinstance(data, dict)


def test_integration_manifest_has_charts_key(manifest_data: dict) -> None:
    """3. Verify that the manifest JSON has a top-level 'charts' key containing a list."""
    assert "charts" in manifest_data
    assert isinstance(manifest_data["charts"], list)


def test_integration_manifest_entry_schema(manifest_data: dict) -> None:
    """4. Verify every entry contains all required fields."""
    required_fields = {"id", "type", "subject", "files", "data_source", "title"}
    charts = manifest_data["charts"]
    assert len(charts) > 0, "Manifest has no chart entries"

    for i, entry in enumerate(charts):
        missing = required_fields - set(entry.keys())
        assert not missing, f"Entry {i} ({entry.get('id', '?')}): missing {missing}"


def test_integration_manifest_file_paths_resolve(
    manifest_data: dict,
    static_dir: Path,
) -> None:
    """5. Verify every file path in every manifest entry resolves to an existing file."""
    charts = manifest_data["charts"]
    missing: list[str] = []

    for entry in charts:
        for fmt, rel_path in entry["files"].items():
            full_path = static_dir / rel_path
            if not full_path.exists():
                missing.append(f"{entry['id']}/{fmt}: {rel_path}")

    assert not missing, "Missing files:\n" + "\n".join(missing)


def test_integration_min_radar_charts(manifest_data: dict) -> None:
    """6. Verify the manifest contains at least 7 entries with type='radar'."""
    radar_entries = [e for e in manifest_data["charts"] if e["type"] == "radar"]
    assert len(radar_entries) >= 7, (
        f"Expected >= 7 radar charts, got {len(radar_entries)}"
    )


def test_integration_min_heatmap_charts(manifest_data: dict) -> None:
    """7. Verify the manifest contains at least 1 entry with type='heatmap'."""
    heatmap_entries = [e for e in manifest_data["charts"] if e["type"] == "heatmap"]
    assert len(heatmap_entries) >= 1, (
        f"Expected >= 1 heatmap chart, got {len(heatmap_entries)}"
    )


def test_integration_min_matrix_charts(manifest_data: dict) -> None:
    """8. Verify the manifest contains at least 1 entry with type='matrix'."""
    matrix_entries = [e for e in manifest_data["charts"] if e["type"] == "matrix"]
    assert len(matrix_entries) >= 1, (
        f"Expected >= 1 matrix chart, got {len(matrix_entries)}"
    )


def test_integration_svg_files_wellformed(
    manifest_data: dict,
    static_dir: Path,
) -> None:
    """9. For every SVG file in the manifest, verify it is well-formed XML."""
    charts = manifest_data["charts"]
    failures: list[str] = []

    for entry in charts:
        svg_path = entry["files"].get("svg")
        if svg_path is None:
            continue
        full_path = static_dir / svg_path
        result = validate_svg_file(full_path)
        if not result.valid:
            failures.append(f"{entry['id']}: {result.error}")

    assert not failures, "Invalid SVG files:\n" + "\n".join(failures)


def test_integration_png_files_valid_header(
    manifest_data: dict,
    static_dir: Path,
) -> None:
    """10. For every PNG file in the manifest, verify it has a valid PNG header."""
    charts = manifest_data["charts"]
    failures: list[str] = []

    for entry in charts:
        png_path = entry["files"].get("png")
        if png_path is None:
            continue
        full_path = static_dir / png_path
        result = validate_png_file(full_path)
        if not result.valid:
            failures.append(f"{entry['id']}: {result.error}")

    assert not failures, "Invalid PNG files:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# Validation module unit-style tests
# ---------------------------------------------------------------------------


def test_validate_manifest_missing_file_detected(tmp_path: Path) -> None:
    """11. Manifest entry referencing a non-existent file is detected."""
    static = tmp_path / "static"
    img = static / "img"
    img.mkdir(parents=True)

    manifest = {
        "charts": [
            {
                "id": "test-chart",
                "type": "radar",
                "subject": "demo",
                "files": {"svg": "img/radar_demo.svg", "png": "img/radar_demo.png"},
                "data_source": "test.json",
                "title": "Test",
            }
        ]
    }
    manifest_file = img / "chart-manifest.json"
    manifest_file.write_text(json.dumps(manifest))

    result = validate_manifest(manifest_file, static)
    assert not result.valid
    assert len(result.missing_files) == 2
    assert "img/radar_demo.svg" in result.missing_files
    assert "img/radar_demo.png" in result.missing_files


def test_validate_manifest_schema_missing_field() -> None:
    """12. Entry missing the 'title' field produces a schema error."""
    data = {
        "charts": [
            {
                "id": "c1",
                "type": "radar",
                "subject": "demo",
                "files": {"svg": "img/radar_demo.svg", "png": "img/radar_demo.png"},
                "data_source": "test.json",
                # "title" intentionally omitted
            }
        ]
    }
    errors = validate_manifest_schema(data)
    assert any("title" in e for e in errors), f"Expected 'title' error, got: {errors}"


def test_validate_svg_invalid_xml(tmp_path: Path) -> None:
    """13. Non-XML content is detected as invalid SVG."""
    bad_svg = tmp_path / "bad.svg"
    bad_svg.write_text("this is not xml at all <><><<<")
    result = validate_svg_file(bad_svg)
    assert not result.valid
    assert result.error is not None
    assert result.format == "svg"


def test_validate_png_invalid_header(tmp_path: Path) -> None:
    """14. Random bytes (not a PNG header) are detected as invalid."""
    bad_png = tmp_path / "bad.png"
    bad_png.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07")
    result = validate_png_file(bad_png)
    assert not result.valid
    assert result.error is not None
    assert result.format == "png"


def test_make_charts_target_exits_zero() -> None:
    """15. Running ``make charts`` via subprocess exits with code 0."""
    result = subprocess.run(
        ["make", "charts"],
        cwd=str(REPORT_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"make charts failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_no_extra_chart_files_on_disk(
    manifest_data: dict,
    static_dir: Path,
) -> None:
    """16. Every chart .svg/.png file in img/ is referenced by the manifest."""
    result = validate_manifest(
        static_dir / "img" / "chart-manifest.json",
        static_dir,
    )
    assert not result.extra_files, "Extra chart files not in manifest:\n" + "\n".join(
        result.extra_files
    )
