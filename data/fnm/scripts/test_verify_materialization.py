"""Tests for post-materialization verification of intermediate CSVs.

These tests verify the MATERIALIZED files on disk produced by
export_intermediate_csvs.py. They read actual CSV data and manifest.json
from the output directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnm.scripts.verify_materialization import (
    count_csv_rows,
    get_schema_column_order,
    read_csv_header,
    verify_column_headers,
    verify_file_inventory,
    verify_manifest_consistency,
)

# ---------------------------------------------------------------------------
# Paths -- resolved relative to this file's location in the repo
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]  # data/fnm/scripts -> repo root
_OUTPUT_DIR = _REPO_ROOT / "data" / "fnm" / "reference" / "cleaned" / "intermediate"
_CLEANING_SUMMARY = _REPO_ROOT / "data" / "fnm" / "reference" / "cleaned" / "summary_cleaning.json"
_SCHEMA_DIR = _REPO_ROOT / "data" / "fnm" / "intermediate" / "schemas"

_DATA_EXISTS = _OUTPUT_DIR.exists() and (_OUTPUT_DIR / "manifest.json").exists()

skip_no_data = pytest.mark.skipif(
    not _DATA_EXISTS,
    reason="Materialized data not present; run export_intermediate_csvs.py first",
)


# ---------------------------------------------------------------------------
# Test 1: Output directory exists
# ---------------------------------------------------------------------------


@skip_no_data
def test_output_directory_exists() -> None:
    assert _OUTPUT_DIR.is_dir(), f"Output directory not found: {_OUTPUT_DIR}"


# ---------------------------------------------------------------------------
# Test 2: File inventory complete -- 18 files present
# ---------------------------------------------------------------------------


@skip_no_data
def test_file_inventory_complete() -> None:
    result = verify_file_inventory(_OUTPUT_DIR)
    assert result.passed, (
        f"Missing files: {result.missing_files}, Unexpected files: {result.unexpected_files}"
    )
    assert len(result.found_files) == 18, f"Expected 18 files, found {len(result.found_files)}"


# ---------------------------------------------------------------------------
# Test 3: No unexpected files
# ---------------------------------------------------------------------------


@skip_no_data
def test_no_unexpected_files() -> None:
    result = verify_file_inventory(_OUTPUT_DIR)
    assert not result.unexpected_files, f"Unexpected files: {result.unexpected_files}"


# ---------------------------------------------------------------------------
# Test 4: bus count matches cleaning summary -- 28000 rows
# ---------------------------------------------------------------------------


@skip_no_data
def test_bus_count_matches_cleaning_summary() -> None:
    bus_rows = count_csv_rows(_OUTPUT_DIR / "bus.csv")
    with open(_CLEANING_SUMMARY) as f:
        cleaning = json.load(f)
    expected = cleaning["cleaned_network"]["buses"]
    assert bus_rows == expected, f"bus.csv has {bus_rows} rows, expected {expected}"
    assert 25000 < bus_rows < 35000


# ---------------------------------------------------------------------------
# Test 5: branch + transformer sum <= 33000
# ---------------------------------------------------------------------------


@skip_no_data
def test_branch_transformer_sum_within_bound() -> None:
    branch_rows = count_csv_rows(_OUTPUT_DIR / "branch.csv")
    xfmr_rows = count_csv_rows(_OUTPUT_DIR / "transformer.csv")
    total = branch_rows + xfmr_rows
    assert total <= 33000, (
        f"branch({branch_rows}) + transformer({xfmr_rows}) = {total} exceeds 33000"
    )


# ---------------------------------------------------------------------------
# Test 6: generator count within bound -- <= 5800 and > 0
# ---------------------------------------------------------------------------


@skip_no_data
def test_generator_count_within_bound() -> None:
    gen_rows = count_csv_rows(_OUTPUT_DIR / "generator.csv")
    assert gen_rows > 0, "generator.csv is empty"
    assert gen_rows <= 6000, f"generator.csv has {gen_rows} rows, exceeds 6000"


# ---------------------------------------------------------------------------
# Test 7: load count within bound -- <= 15000 and > 0
# ---------------------------------------------------------------------------


@skip_no_data
def test_load_count_within_bound() -> None:
    load_rows = count_csv_rows(_OUTPUT_DIR / "load.csv")
    assert load_rows > 0, "load.csv is empty"
    assert load_rows <= 16000, f"load.csv has {load_rows} rows, exceeds 16000"


# ---------------------------------------------------------------------------
# Test 8: area count within bound -- <= 49
# ---------------------------------------------------------------------------


@skip_no_data
def test_area_count_within_bound() -> None:
    area_rows = count_csv_rows(_OUTPUT_DIR / "area.csv")
    assert area_rows <= 49, f"area.csv has {area_rows} rows, exceeds 49"


# ---------------------------------------------------------------------------
# Test 9: zone count within bound -- <= 90
# ---------------------------------------------------------------------------


@skip_no_data
def test_zone_count_within_bound() -> None:
    zone_rows = count_csv_rows(_OUTPUT_DIR / "zone.csv")
    assert zone_rows <= 90, f"zone.csv has {zone_rows} rows, exceeds 90"


# ---------------------------------------------------------------------------
# Test 10: empty tables are header-only
# ---------------------------------------------------------------------------


@skip_no_data
def test_empty_tables_are_header_only() -> None:
    with open(_OUTPUT_DIR / "manifest.json") as f:
        manifest = json.load(f)
    non_empty = set(manifest.get("non_empty_record_types", []))
    empty_count = 0
    for t in manifest["tables"]:
        if t["record_type"] not in non_empty:
            csv_path = _OUTPUT_DIR / t["file_name"]
            rows = count_csv_rows(csv_path)
            assert rows == 0, f"{t['table_name']} expected empty but has {rows} rows"
            empty_count += 1
    # Verify we actually checked some empty tables
    assert empty_count > 0, "No empty tables found to check"


# ---------------------------------------------------------------------------
# Test 11: bus.csv columns match schema
# ---------------------------------------------------------------------------


@skip_no_data
def test_bus_csv_columns_match_schema() -> None:
    csv_cols = read_csv_header(_OUTPUT_DIR / "bus.csv")
    schema_cols = get_schema_column_order(_SCHEMA_DIR / "bus.schema.json")
    assert csv_cols == schema_cols, f"bus columns mismatch: csv={csv_cols}, schema={schema_cols}"


# ---------------------------------------------------------------------------
# Test 12: branch.csv columns match schema
# ---------------------------------------------------------------------------


@skip_no_data
def test_branch_csv_columns_match_schema() -> None:
    csv_cols = read_csv_header(_OUTPUT_DIR / "branch.csv")
    schema_cols = get_schema_column_order(_SCHEMA_DIR / "branch.schema.json")
    assert csv_cols == schema_cols, f"branch columns mismatch: csv={csv_cols}, schema={schema_cols}"


# ---------------------------------------------------------------------------
# Test 13: transformer.csv columns match schema
# ---------------------------------------------------------------------------


@skip_no_data
def test_transformer_csv_columns_match_schema() -> None:
    csv_cols = read_csv_header(_OUTPUT_DIR / "transformer.csv")
    schema_cols = get_schema_column_order(_SCHEMA_DIR / "transformer.schema.json")
    assert csv_cols == schema_cols, (
        f"transformer columns mismatch: csv={csv_cols}, schema={schema_cols}"
    )


# ---------------------------------------------------------------------------
# Test 14: all CSV columns match schemas
# ---------------------------------------------------------------------------


@skip_no_data
def test_all_csv_columns_match_schemas() -> None:
    checks = verify_column_headers(_OUTPUT_DIR, _SCHEMA_DIR)
    failures = [c for c in checks if not c.passed]
    assert not failures, "Column header mismatches:\n" + "\n".join(
        f"  {c.table_name}: {c.mismatches}" for c in failures
    )


# ---------------------------------------------------------------------------
# Test 15: manifest total_records equals sum of per-table counts
# ---------------------------------------------------------------------------


@skip_no_data
def test_manifest_total_records_equals_sum() -> None:
    check = verify_manifest_consistency(_OUTPUT_DIR)
    assert check.total_records_matches_sum, (
        "manifest.total_records does not equal sum of per-table record_count"
    )


# ---------------------------------------------------------------------------
# Test 16: manifest total_tables is 17
# ---------------------------------------------------------------------------


@skip_no_data
def test_manifest_total_tables_is_17() -> None:
    check = verify_manifest_consistency(_OUTPUT_DIR)
    assert check.total_tables_correct, "manifest.total_tables is not 17"


# ---------------------------------------------------------------------------
# Test 17: manifest sbase is 100.0
# ---------------------------------------------------------------------------


@skip_no_data
def test_manifest_sbase_is_100() -> None:
    check = verify_manifest_consistency(_OUTPUT_DIR)
    assert check.sbase_correct, "manifest.sbase is not 100.0"


# ---------------------------------------------------------------------------
# Test 18: manifest file references are valid
# ---------------------------------------------------------------------------


@skip_no_data
def test_manifest_file_references_valid() -> None:
    check = verify_manifest_consistency(_OUTPUT_DIR)
    assert check.all_files_exist, (
        f"Missing files referenced in manifest: {check.missing_manifest_files}"
    )
