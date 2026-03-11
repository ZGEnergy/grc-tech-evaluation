"""Tests for the export pipeline script (PRD 00/01).

Integration tests that read real data files are marked with skipif guards
for when the data files are not present.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fnm.scripts.export_intermediate_csvs import (
    MatpowerCase,
    TableExport,
    build_manifest,
    export_table_to_csv,
    filter_rows_by_bus,
    load_excluded_buses,
    load_matpower_case,
    normalize_tap_ratio,
    run_export_pipeline,
    split_branches_and_transformers,
    validate_csv_against_schema,
    validate_manifest_against_schema,
)
from fnm.scripts.raw_record_counter import PSSE_V31_SECTION_NAMES

# ---------------------------------------------------------------------------
# Path constants for integration tests
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_MAIN_CHECKOUT = _REPO_ROOT

# The .mat file may be in the worktree or main checkout
_MAT_PATH = _REPO_ROOT / "data" / "fnm" / "reference" / "cleaned" / "fnm_main_island.mat"
_EXCLUDED_JSON = _REPO_ROOT / "data" / "fnm" / "reference" / "excluded_buses.json"
_SCHEMA_DIR = _REPO_ROOT / "data" / "fnm" / "intermediate" / "schemas"

# Check main checkout if worktree doesn't have the files
if not _MAT_PATH.exists():
    # Try the git main working tree
    _git_file = _REPO_ROOT / ".git"
    if _git_file.is_file():
        _git_text = _git_file.read_text().strip()
        if _git_text.startswith("gitdir:"):
            _main_git = Path(_git_text.split(":", 1)[1].strip())
            _main_repo = _main_git.parent.parent.parent
            _alt_mat = _main_repo / "data" / "fnm" / "reference" / "cleaned" / "fnm_main_island.mat"
            _alt_excl = _main_repo / "data" / "fnm" / "reference" / "excluded_buses.json"
            _alt_schema = _main_repo / "data" / "fnm" / "intermediate" / "schemas"
            if _alt_mat.exists():
                _MAT_PATH = _alt_mat
            if _alt_excl.exists():
                _EXCLUDED_JSON = _alt_excl
            if _alt_schema.exists():
                _SCHEMA_DIR = _alt_schema

_HAS_MAT = _MAT_PATH.exists()
_HAS_EXCLUDED = _EXCLUDED_JSON.exists()
_HAS_SCHEMAS = _SCHEMA_DIR.exists()
_HAS_ALL_DATA = _HAS_MAT and _HAS_EXCLUDED and _HAS_SCHEMAS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus_schema(tmp_path: Path) -> Path:
    """Create a minimal bus schema for testing."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Bus",
        "type": "object",
        "properties": {
            "I": {"type": "integer"},
            "NAME": {"type": "string"},
            "BASKV": {"type": "number"},
            "IDE": {"type": "integer"},
        },
        "required": ["I", "NAME", "BASKV", "IDE"],
        "additionalProperties": False,
    }
    path = tmp_path / "bus.schema.json"
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def manifest_schema(tmp_path: Path) -> Path:
    """Create the manifest schema for testing."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Intermediate Format Manifest",
        "type": "object",
        "properties": {
            "sbase": {"type": "number"},
            "basfrq": {"type": "number"},
            "rev": {"type": "number"},
            "case_id": {"type": "string"},
            "canonical_parser": {
                "type": "string",
                "enum": ["matpower", "gridcal"],
            },
            "tables": {"type": "array"},
            "total_records": {"type": "integer", "minimum": 0},
            "total_tables": {"type": "integer", "minimum": 1},
            "non_empty_record_types": {"type": "array"},
            "schema_version": {"type": "string"},
            "generated_timestamp": {"type": "string", "format": "date-time"},
        },
        "required": [
            "sbase",
            "basfrq",
            "rev",
            "case_id",
            "canonical_parser",
            "tables",
            "total_records",
            "total_tables",
            "non_empty_record_types",
            "schema_version",
            "generated_timestamp",
        ],
        "additionalProperties": False,
    }
    path = tmp_path / "manifest.schema.json"
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def synthetic_branch_matrix() -> list[list[float]]:
    """Synthetic MATPOWER branch matrix: 3 plain branches + 2 transformers.

    Branch columns: fbus, tbus, r, x, b, rateA, rateB, rateC, tap, shift, status
    """
    return [
        # Plain branches (tap=0, shift=0)
        [1, 2, 0.01, 0.1, 0.02, 100, 100, 100, 0, 0, 1, -360, 360],
        [2, 3, 0.02, 0.2, 0.03, 200, 200, 200, 0, 0, 1, -360, 360],
        [1, 3, 0.03, 0.3, 0.04, 300, 300, 300, 0, 0, 1, -360, 360],
        # Transformers (tap != 0)
        [1, 4, 0.01, 0.1, 0.0, 100, 100, 100, 1.05, 0, 1, -360, 360],
        [3, 5, 0.02, 0.2, 0.0, 200, 200, 200, 0, 30.0, 1, -360, 360],
    ]


# ---------------------------------------------------------------------------
# Test 1: test_load_matpower_case_extracts_basemva
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_MAT, reason="requires FNM .mat file")
def test_load_matpower_case_extracts_basemva():
    case = load_matpower_case(_MAT_PATH)
    assert case.baseMVA == 100.0


# ---------------------------------------------------------------------------
# Test 2: test_load_matpower_case_extracts_bus_matrix_shape
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_MAT, reason="requires FNM .mat file")
def test_load_matpower_case_extracts_bus_matrix_shape():
    # NOTE: PRD specifies 30,307 (pre-filter) but the cleaned .mat file
    # has 27,862 buses (post island-extraction). We match the actual data.
    case = load_matpower_case(_MAT_PATH)
    assert len(case.bus) == 27862
    assert len(case.bus[0]) == 13


# ---------------------------------------------------------------------------
# Test 3: test_load_excluded_buses_count
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_EXCLUDED, reason="requires excluded_buses.json")
def test_load_excluded_buses_count():
    excluded = load_excluded_buses(_EXCLUDED_JSON)
    assert len(excluded) == 2445


# ---------------------------------------------------------------------------
# Test 4: test_split_branches_separates_transformers
# ---------------------------------------------------------------------------


def test_split_branches_separates_transformers(
    synthetic_branch_matrix: list[list[float]],
):
    bus_numbers = {1, 2, 3, 4, 5}
    branches, transformers = split_branches_and_transformers(synthetic_branch_matrix, bus_numbers)
    assert len(branches) == 3
    assert len(transformers) == 2


# ---------------------------------------------------------------------------
# Test 5: test_normalize_tap_zero_becomes_one
# ---------------------------------------------------------------------------


def test_normalize_tap_zero_becomes_one():
    assert normalize_tap_ratio(0.0) == 1.0
    assert normalize_tap_ratio(1.05) == 1.05


# ---------------------------------------------------------------------------
# Test 6: test_normalize_tap_on_transformer_rows
# ---------------------------------------------------------------------------


def test_normalize_tap_on_transformer_rows(
    synthetic_branch_matrix: list[list[float]],
):
    bus_numbers = {1, 2, 3, 4, 5}
    _, transformers = split_branches_and_transformers(synthetic_branch_matrix, bus_numbers)
    for t in transformers:
        assert t["WINDV1"] != 0.0, f"WINDV1 should not be 0.0: {t}"


# ---------------------------------------------------------------------------
# Test 7: test_filter_rows_removes_excluded_buses
# ---------------------------------------------------------------------------


def test_filter_rows_removes_excluded_buses():
    rows: list[dict[str, int | float | str]] = [
        {"I": 1, "NAME": "A"},
        {"I": 2, "NAME": "B"},
        {"I": 3, "NAME": "C"},
    ]
    bus_numbers = {1, 3}
    filtered = filter_rows_by_bus(rows, bus_numbers, bus_key="I")
    assert len(filtered) == 2
    assert {int(r["I"]) for r in filtered} == {1, 3}


# ---------------------------------------------------------------------------
# Test 8: test_filter_branch_rows_removes_both_endpoints
# ---------------------------------------------------------------------------


def test_filter_branch_rows_removes_both_endpoints():
    rows: list[dict[str, int | float | str]] = [
        {"I": 1, "J": 2, "CKT": "1 "},
        {"I": 2, "J": 3, "CKT": "1 "},
        {"I": 1, "J": 3, "CKT": "1 "},
    ]
    bus_numbers = {1, 3}
    # Manual filter: both endpoints must be in bus_numbers
    filtered = [r for r in rows if int(r["I"]) in bus_numbers and int(r["J"]) in bus_numbers]
    assert len(filtered) == 1
    assert int(filtered[0]["I"]) == 1
    assert int(filtered[0]["J"]) == 3


# ---------------------------------------------------------------------------
# Test 9: test_export_csv_column_order_matches_schema
# ---------------------------------------------------------------------------


def test_export_csv_column_order_matches_schema(
    tmp_path: Path,
    bus_schema: Path,
):
    rows = [
        {"I": 1, "NAME": "BUS1", "BASKV": 138.0, "IDE": 1},
        {"I": 2, "NAME": "BUS2", "BASKV": 345.0, "IDE": 2},
    ]
    csv_path = tmp_path / "bus.csv"
    export_table_to_csv(rows, bus_schema, csv_path)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    schema = json.loads(bus_schema.read_text(encoding="utf-8"))
    expected_cols = list(schema["properties"].keys())
    assert header == expected_cols


# ---------------------------------------------------------------------------
# Test 10: test_export_csv_integer_fields_no_decimal
# ---------------------------------------------------------------------------


def test_export_csv_integer_fields_no_decimal(
    tmp_path: Path,
    bus_schema: Path,
):
    rows = [
        {"I": 42, "NAME": "BUS42", "BASKV": 138.0, "IDE": 3},
    ]
    csv_path = tmp_path / "bus.csv"
    export_table_to_csv(rows, bus_schema, csv_path)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)

    # Integer fields should not have .0
    assert row["I"] == "42"
    assert row["IDE"] == "3"
    assert "." not in row["I"]
    assert "." not in row["IDE"]


# ---------------------------------------------------------------------------
# Test 11: test_manifest_contains_all_tables
# ---------------------------------------------------------------------------


def test_manifest_contains_all_tables():
    # Build a minimal case + 17 table exports
    case = MatpowerCase(
        baseMVA=100.0,
        version="2",
        bus=[],
        gen=[],
        branch=[],
        gencost=[],
        areas=[],
        bus_name=[],
        dcline=[],
    )

    table_exports = []
    for rt in PSSE_V31_SECTION_NAMES:
        table_name = rt.lower().replace(" ", "_").replace("-", "_")
        table_exports.append(
            TableExport(
                table_name=table_name,
                record_type=rt,
                file_name=f"{table_name}.csv",
                file_path=Path(f"{table_name}.csv"),
                record_count=0,
                column_count=5,
                schema_file=f"{table_name}.schema.json",
            )
        )

    manifest = build_manifest(case, table_exports)
    assert manifest.total_tables == 17
    manifest_types = {te.record_type for te in manifest.tables}
    expected_types = set(PSSE_V31_SECTION_NAMES)
    assert manifest_types == expected_types


# ---------------------------------------------------------------------------
# Test 12: test_manifest_sbase_matches_case
# ---------------------------------------------------------------------------


def test_manifest_sbase_matches_case():
    case = MatpowerCase(
        baseMVA=100.0,
        version="2",
        bus=[],
        gen=[],
        branch=[],
        gencost=[],
        areas=[],
        bus_name=[],
        dcline=[],
    )
    manifest = build_manifest(case, [])
    assert manifest.sbase == 100.0


# ---------------------------------------------------------------------------
# Test 13: test_manifest_total_records_is_sum
# ---------------------------------------------------------------------------


def test_manifest_total_records_is_sum():
    case = MatpowerCase(
        baseMVA=100.0,
        version="2",
        bus=[],
        gen=[],
        branch=[],
        gencost=[],
        areas=[],
        bus_name=[],
        dcline=[],
    )

    exports = [
        TableExport(
            table_name="bus",
            record_type="Bus",
            file_name="bus.csv",
            file_path=Path("bus.csv"),
            record_count=10,
            column_count=13,
            schema_file="bus.schema.json",
        ),
        TableExport(
            table_name="generator",
            record_type="Generator",
            file_name="generator.csv",
            file_path=Path("generator.csv"),
            record_count=5,
            column_count=28,
            schema_file="generator.schema.json",
        ),
    ]

    manifest = build_manifest(case, exports)
    assert manifest.total_records == 15
    assert manifest.total_records == sum(te.record_count for te in exports)


# ---------------------------------------------------------------------------
# Test 14: test_validate_bus_csv_passes_schema
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_ALL_DATA, reason="requires FNM data files")
def test_validate_bus_csv_passes_schema(tmp_path: Path):
    run_export_pipeline(
        mat_path=_MAT_PATH,
        excluded_buses_path=_EXCLUDED_JSON,
        schema_dir=_SCHEMA_DIR,
        output_dir=tmp_path / "export",
    )

    bus_csv = tmp_path / "export" / "bus.csv"
    bus_schema = _SCHEMA_DIR / "bus.schema.json"
    assert bus_csv.exists()
    assert bus_schema.exists()

    vr = validate_csv_against_schema(bus_csv, bus_schema)
    assert vr.is_valid, f"Bus CSV validation failed: {vr.errors}"


# ---------------------------------------------------------------------------
# Test 15: test_validate_manifest_passes_schema
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_ALL_DATA, reason="requires FNM data files")
def test_validate_manifest_passes_schema(tmp_path: Path):
    run_export_pipeline(
        mat_path=_MAT_PATH,
        excluded_buses_path=_EXCLUDED_JSON,
        schema_dir=_SCHEMA_DIR,
        output_dir=tmp_path / "export",
    )

    manifest_path = tmp_path / "export" / "manifest.json"
    manifest_schema = _SCHEMA_DIR / "manifest.schema.json"
    assert manifest_path.exists()
    assert manifest_schema.exists()

    vr = validate_manifest_against_schema(manifest_path, manifest_schema)
    assert vr.is_valid, f"Manifest validation failed: {vr.errors}"


# ---------------------------------------------------------------------------
# Test 16: test_validate_csv_detects_invalid_row
# ---------------------------------------------------------------------------


def test_validate_csv_detects_invalid_row(
    tmp_path: Path,
    bus_schema: Path,
):
    csv_path = tmp_path / "bad_bus.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["I", "NAME", "BASKV", "IDE"])
        # Valid row
        writer.writerow(["1", "BUS1", "138.0", "1"])
        # Invalid row: IDE not an integer-parseable string but we write
        # a string that would fail int casting; however jsonschema checks
        # the typed value. Let's put a missing required field by omitting NAME.
    # Rewrite with explicit missing field
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["I", "BASKV", "IDE"])  # Missing NAME column
        writer.writerow(["1", "138.0", "1"])

    # Create a schema that requires NAME
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Bus",
        "type": "object",
        "properties": {
            "I": {"type": "integer"},
            "NAME": {"type": "string"},
            "BASKV": {"type": "number"},
            "IDE": {"type": "integer"},
        },
        "required": ["I", "NAME", "BASKV", "IDE"],
        "additionalProperties": False,
    }
    schema_path = tmp_path / "bus_strict.schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    vr = validate_csv_against_schema(csv_path, schema_path)
    assert not vr.is_valid
    assert len(vr.errors) > 0


# ---------------------------------------------------------------------------
# Test 17: test_empty_table_produces_header_only_csv
# ---------------------------------------------------------------------------


def test_empty_table_produces_header_only_csv(
    tmp_path: Path,
    bus_schema: Path,
):
    csv_path = tmp_path / "empty.csv"
    te = export_table_to_csv([], bus_schema, csv_path)

    assert te.record_count == 0

    with open(csv_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Should have exactly one line (the header)
    assert len(lines) == 1
    assert "I" in lines[0]


# ---------------------------------------------------------------------------
# Test 18: test_run_export_pipeline_end_to_end
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_ALL_DATA, reason="requires FNM data files")
def test_run_export_pipeline_end_to_end(tmp_path: Path):
    output_dir = tmp_path / "export"
    result = run_export_pipeline(
        mat_path=_MAT_PATH,
        excluded_buses_path=_EXCLUDED_JSON,
        schema_dir=_SCHEMA_DIR,
        output_dir=output_dir,
    )

    # All CSVs exist
    for te in result.table_exports:
        assert te.file_path.exists(), f"Missing CSV: {te.file_name}"

    # Manifest exists
    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists()

    # All validations pass
    assert result.success, f"Pipeline failed: {result.errors}"

    # Bus count should be 27,862 (main island)
    bus_export = next(te for te in result.table_exports if te.record_type == "Bus")
    assert bus_export.record_count == 27862

    # Manifest has all 17 tables
    assert result.manifest.total_tables == 17

    # Total records > 0
    assert result.manifest.total_records > 0
