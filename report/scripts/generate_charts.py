#!/usr/bin/env python3
"""Chart generation pipeline for the Phase 1 Report Site.

Three-stage pipeline:
  1. Data loading — validate and transform JSON into typed dataclasses
  2. Chart rendering — execute registered renderers to produce ChartOutputs
  3. Export & manifest — write image files and chart-manifest.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from chart_types import (
    ChartManifest,
    ChartManifestEntry,
    ChartOutput,
    ChartRendererFn,  # noqa: F401 — re-exported for tests
    ChartType,
    ExportFormat,
    GradesData,
    TestResultsData,
    TimingRecord,
    _RENDERERS,  # noqa: F401 — re-exported for tests
    get_registered_renderers,
    register_renderer,  # noqa: F401 — re-exported for tests
)

SCRIPT_DIR = Path(__file__).parent
REPORT_DIR = SCRIPT_DIR.parent
DATA_DIR = REPORT_DIR / "data"
IMG_DIR = REPORT_DIR / "static" / "img"
MANIFEST_PATH = IMG_DIR / "chart-manifest.json"
STATIC_DIR = REPORT_DIR / "static"

GENERATOR_VERSION = "0.1.0"

# Data files and their required top-level keys
DATA_FILES: dict[str, list[str]] = {
    "grades.json": ["scale", "tools", "criteria", "grades"],
    "sensitivity.json": ["scenarios"],
    "risk-register.json": ["risks"],
    "head-to-head.json": ["capabilities"],
    "sweep-themes.json": ["themes"],
    "probe-results.json": ["probes"],
    "tool-profiles.json": ["tools"],
    "test-results.json": ["suites", "tools"],
}

# ---------------------------------------------------------------------------
# Stage 1: Data loading
# ---------------------------------------------------------------------------


def load_json_file(path: Path) -> dict[str, Any]:
    """Load and parse a single JSON file."""
    with open(path) as f:
        return json.load(f)


def load_all_data_files(data_dir: Path) -> dict[str, Any]:
    """Load all JSON files from the data directory.

    Returns a dict mapping file stem (no extension) to parsed content.
    Raises FileNotFoundError if the directory doesn't exist, or ValueError
    if no JSON files are found.
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        raise ValueError(f"No .json files found in {data_dir}")
    return {f.stem: load_json_file(f) for f in json_files}


def validate_data_files(data_dir: Path) -> dict[str, dict[str, Any]]:
    """Validate all expected data files exist, parse, and contain required keys.

    Returns dict mapping filename to parsed data.
    Raises SystemExit if any validation fails.
    """
    print("Validating data files...")
    errors: list[str] = []
    data: dict[str, dict[str, Any]] = {}

    for filename, required_keys in DATA_FILES.items():
        filepath = data_dir / filename
        if not filepath.exists():
            errors.append(f"  {filename}: MISSING")
            continue

        try:
            with open(filepath) as f:
                parsed = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"  {filename}: INVALID JSON - {e}")
            continue

        missing_keys = [k for k in required_keys if k not in parsed]
        if missing_keys:
            errors.append(f"  {filename}: MISSING KEYS - {', '.join(missing_keys)}")
            continue

        key_count = len(required_keys)
        print(
            f"  {filename}: OK ({key_count} required key{'s' if key_count != 1 else ''})"
        )
        data[filename] = parsed

    if errors:
        print("\nValidation FAILED:")
        for error in errors:
            print(error)
        sys.exit(1)

    print(f"All {len(DATA_FILES)} data files validated successfully.\n")
    return data


def grade_to_numeric(letter: str) -> float:
    """Convert a letter grade to its numeric equivalent.

    A+=4.3, A=4.0, A-=3.7, B+=3.3, B=3.0, B-=2.7,
    C+=2.3, C=2.0, C-=1.7, D+=1.3, D=1.0, D-=0.7, F=0.0.

    Raises ValueError for unrecognized grades.
    """
    scale: dict[str, float] = {
        "A+": 4.3,
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D+": 1.3,
        "D": 1.0,
        "D-": 0.7,
        "F": 0.0,
    }
    key = letter.upper().strip()
    if key not in scale:
        raise ValueError(f"Unrecognized grade: {letter!r}")
    return scale[key]


def build_grades_data(raw: dict[str, Any]) -> GradesData:
    """Transform the grades.json payload into a GradesData instance.

    The raw dict must contain 'grades', 'criteria', and 'tools' keys.
    Each grade entry has 'tool', 'criterion', 'letter', and 'numeric' fields.
    """
    grades_list: list[dict[str, Any]] = raw["grades"]
    criteria: list[str] = raw["criteria"]
    tools: list[str] = raw["tools"]

    # Build numeric DataFrame: rows=criteria, columns=tools
    rows: dict[str, dict[str, float]] = {}
    letter_grades: dict[str, dict[str, str]] = {}

    for entry in grades_list:
        tool = entry["tool"]
        criterion = entry["criterion"]
        numeric = float(entry["numeric"])
        letter = entry["letter"]

        if criterion not in rows:
            rows[criterion] = {}
        rows[criterion][tool] = numeric

        if tool not in letter_grades:
            letter_grades[tool] = {}
        letter_grades[tool][criterion] = letter

    df = pd.DataFrame(rows).T  # rows=criteria, columns=tools
    # Reindex to match declared order
    df = df.reindex(index=criteria, columns=tools)

    return GradesData(
        df=df,
        letter_grades=letter_grades,
        criteria=criteria,
        tools=tools,
    )


def build_test_results_data(raw: dict[str, Any]) -> TestResultsData:
    """Transform the test-results.json payload into a TestResultsData instance.

    The raw dict must contain 'suites' and 'tools' keys.
    Each tool entry has 'by_suite' with suite-level test results.
    """
    tools_list: list[dict[str, Any]] = raw["tools"]
    tool_names: list[str] = [t["tool"] for t in tools_list]

    # Collect all unique test IDs in order, and map test_id -> suite
    all_test_ids: list[str] = []
    suite_grouping: dict[str, str] = {}
    seen_ids: set[str] = set()

    # Iterate all tools to capture the full union of test IDs
    for tool_entry in tools_list:
        for suite_entry in tool_entry["by_suite"]:
            suite_name = suite_entry["suite"]
            for test in suite_entry["tests"]:
                test_id = test["id"]
                if test_id not in seen_ids:
                    all_test_ids.append(test_id)
                    suite_grouping[test_id] = suite_name
                    seen_ids.add(test_id)

    # Build result matrix: rows=test_ids, columns=tools, values=result strings
    matrix_data: dict[str, dict[str, str]] = {tid: {} for tid in all_test_ids}

    for tool_entry in tools_list:
        tool_name = tool_entry["tool"]
        for suite_entry in tool_entry["by_suite"]:
            for test in suite_entry["tests"]:
                test_id = test["id"]
                result = test["result"]
                matrix_data[test_id][tool_name] = result

    matrix_df = pd.DataFrame.from_dict(matrix_data, orient="index")
    matrix_df = matrix_df.reindex(index=all_test_ids, columns=tool_names)
    # Fill any missing entries with "skip"
    matrix_df = matrix_df.fillna("skip")

    # Build timing records from the optional timing_records array
    timing_records: list[TimingRecord] = []
    for rec in raw.get("timing_records", []):
        timing_records.append(
            TimingRecord(
                tool=rec["tool"],
                benchmark_type=rec["benchmark_type"],
                network_size=rec["network_size"],
                solve_time_seconds=rec["solve_time_seconds"],
                status=rec["status"],
            )
        )

    return TestResultsData(
        matrix_df=matrix_df,
        suite_grouping=suite_grouping,
        tools=tool_names,
        test_ids=all_test_ids,
        timing_records=timing_records,
    )


# ---------------------------------------------------------------------------
# Stage 2: Chart rendering
# ---------------------------------------------------------------------------


def run_renderers(
    grades_data: GradesData,
    test_results_data: TestResultsData,
) -> list[ChartOutput]:
    """Execute all registered renderers and collect their outputs."""
    renderers = get_registered_renderers()
    outputs: list[ChartOutput] = []
    for name, fn in renderers.items():
        print(f"  Running renderer: {name}")
        results = fn(grades_data=grades_data, test_results_data=test_results_data)
        outputs.extend(results)
    if not renderers:
        print("  No renderers registered (Phase 1 skeleton)")
    return outputs


# ---------------------------------------------------------------------------
# Stage 3: Export & manifest
# ---------------------------------------------------------------------------


def chart_file_name(chart_type: ChartType, subject: str, fmt: ExportFormat) -> str:
    """Generate a canonical chart filename: {type}_{subject}.{ext}."""
    return f"{chart_type.value}_{subject}.{fmt.value}"


def export_chart(
    chart_output: ChartOutput,
    output_dir: Path,
    formats: tuple[ExportFormat, ...] = (ExportFormat.SVG, ExportFormat.PNG),
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Path]:
    """Export a chart figure to the requested formats.

    Returns a dict mapping format name to the written file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[str, Path] = {}

    for fmt in formats:
        filename = chart_file_name(chart_output.chart_type, chart_output.subject, fmt)
        filepath = output_dir / filename

        write_kwargs: dict[str, Any] = {"file": str(filepath), "format": fmt.value}
        if width is not None:
            write_kwargs["width"] = width
        if height is not None:
            write_kwargs["height"] = height

        chart_output.figure.write_image(**write_kwargs)
        exported[fmt.value] = filepath
        print(f"    Exported: {filepath.name}")

    return exported


def build_manifest_entry(
    chart_output: ChartOutput,
    exported_files: dict[str, Path],
    static_dir: Path,
) -> ChartManifestEntry:
    """Build a manifest entry with paths relative to the static directory."""
    relative_files: dict[str, str] = {}
    for fmt_name, filepath in exported_files.items():
        try:
            rel = filepath.relative_to(static_dir)
        except ValueError:
            rel = filepath
        relative_files[fmt_name] = str(rel)

    return ChartManifestEntry(
        id=chart_output.chart_id,
        type=chart_output.chart_type.value,
        subject=chart_output.subject,
        files=relative_files,
        data_source=chart_output.data_source,
        title=chart_output.title,
    )


def write_chart_manifest(entries: list[ChartManifestEntry], dest_path: Path) -> None:
    """Write chart manifest JSON to disk."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": GENERATOR_VERSION,
        "chart_count": len(entries),
        "charts": [asdict(e) for e in entries],
    }

    with open(dest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\nWrote chart manifest: {dest_path.name} ({len(entries)} charts)")


# ---------------------------------------------------------------------------
# Top-level pipeline
# ---------------------------------------------------------------------------


def _import_renderers() -> None:
    """Import renderer modules to trigger self-registration in chart_types."""
    from renderers import bar as _bar  # noqa: F401
    from renderers import heatmap as _heatmap  # noqa: F401
    from renderers import matrix as _matrix  # noqa: F401
    from renderers import radar as _radar  # noqa: F401
    from renderers import scalability as _scalability  # noqa: F401


def generate_all_charts(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
) -> ChartManifest:
    """Run the full chart pipeline: load, render, export, manifest.

    Args:
        data_dir: Path to JSON data files. Defaults to DATA_DIR.
        output_dir: Path to write chart images. Defaults to IMG_DIR.

    Returns:
        The ChartManifest describing all generated charts.
    """
    _import_renderers()

    data_dir = data_dir or DATA_DIR
    output_dir = output_dir or IMG_DIR

    # Stage 1: Data loading
    validated = validate_data_files(data_dir)
    grades_data = build_grades_data(validated["grades.json"])
    test_results_data = build_test_results_data(validated["test-results.json"])

    print(
        f"Loaded grades: {len(grades_data.tools)} tools x {len(grades_data.criteria)} criteria"
    )
    print(
        f"Loaded test results: {len(test_results_data.tools)} tools x"
        f" {len(test_results_data.test_ids)} tests"
    )

    # Stage 2: Chart rendering
    print("\nRendering charts...")
    chart_outputs = run_renderers(grades_data, test_results_data)

    # Stage 3: Export & manifest
    print("\nExporting charts...")
    manifest_entries: list[ChartManifestEntry] = []
    for chart_output in chart_outputs:
        exported_files = export_chart(chart_output, output_dir)
        entry = build_manifest_entry(chart_output, exported_files, STATIC_DIR)
        manifest_entries.append(entry)

    write_chart_manifest(manifest_entries, MANIFEST_PATH)

    return ChartManifest(charts=manifest_entries)


def main() -> int:
    """Entry point. Returns 0 on success, 1 on failure."""
    try:
        generate_all_charts()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
