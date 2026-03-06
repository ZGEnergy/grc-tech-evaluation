"""Tests for Schema Conformance & File Completeness Checks (PRD 05/01).

All 18 tests correspond to the PRD success criteria. Tests are self-contained
with no external file dependencies — all test data is created via temporary
files and directories.
"""

from __future__ import annotations

from pathlib import Path


from scripts.validate_schema import (
    CheckId,
    CheckStatus,
    ColumnDtype,
    ColumnSpec,
    CsvFileType,
    FileManifestEntry,
    build_column_specs_load,
    build_file_manifest,
    check_column_names,
    check_column_order,
    check_dtype_conformance,
    check_file_exists,
    check_id_columns_not_null,
    check_no_nan_inf,
    check_row_count,
    check_time_dimension,
    validate_file,
    validate_network_schema,
)


# ---------------------------------------------------------------------------
# Test 1: build_file_manifest_tiny_has_all_file_types
# ---------------------------------------------------------------------------


def test_build_file_manifest_tiny_has_all_file_types() -> None:
    """Manifest for case39 contains entries for all 13 CsvFileType values."""
    manifest = build_file_manifest("case39")
    file_types_in_manifest = {entry.file_type for entry in manifest}

    for ft in CsvFileType:
        assert ft in file_types_in_manifest, f"Missing file type: {ft}"

    # Every entry has a non-empty relative_path and non-empty columns list.
    for entry in manifest:
        assert entry.relative_path, f"Empty relative_path for {entry.file_type}"
        assert len(entry.columns) > 0, f"Empty columns for {entry.file_type}"


# ---------------------------------------------------------------------------
# Test 2: build_file_manifest_medium_may_exclude_scenarios
# ---------------------------------------------------------------------------


def test_build_file_manifest_medium_may_exclude_scenarios() -> None:
    """Manifest for ACTIVSg10k includes scenario files (OQ-E03 option B).

    Per implementation, scenario files are always included in the manifest.
    The manifest should have 13 entries (all file types).
    """
    manifest = build_file_manifest("ACTIVSg10k")
    # Scenarios included: 13 entries total.
    assert len(manifest) == 13


# ---------------------------------------------------------------------------
# Test 3: build_column_specs_load_has_25_columns
# ---------------------------------------------------------------------------


def test_build_column_specs_load_has_25_columns() -> None:
    """Load column spec has 25 entries: bus_id + 24 HR columns."""
    cols = build_column_specs_load()
    assert len(cols) == 25

    # First column is bus_id (INT, is_id=True).
    assert cols[0].name == "bus_id"
    assert cols[0].dtype == ColumnDtype.INT
    assert cols[0].is_id is True

    # Remaining 24 are HR_1..HR_24 (FLOAT, MW, min_value=0.0).
    for i, col in enumerate(cols[1:], start=1):
        assert col.name == f"HR_{i}"
        assert col.dtype == ColumnDtype.FLOAT
        assert col.unit == "MW"
        assert col.min_value == 0.0


# ---------------------------------------------------------------------------
# Test 4: check_file_exists_pass
# ---------------------------------------------------------------------------


def test_check_file_exists_pass(tmp_path: Path) -> None:
    """check_file_exists returns PASS for an existing file."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("bus_id,HR_1\n1,100.0\n")

    status, violations = check_file_exists(csv_file)
    assert status == CheckStatus.PASS
    assert violations == []


# ---------------------------------------------------------------------------
# Test 5: check_file_exists_fail
# ---------------------------------------------------------------------------


def test_check_file_exists_fail(tmp_path: Path) -> None:
    """check_file_exists returns FAIL for a non-existent file."""
    missing = tmp_path / "nonexistent.csv"

    status, violations = check_file_exists(missing)
    assert status == CheckStatus.FAIL
    assert len(violations) == 1
    assert violations[0].error_type == "missing_file"


# ---------------------------------------------------------------------------
# Test 6: check_column_names_pass
# ---------------------------------------------------------------------------


def test_check_column_names_pass() -> None:
    """Column names match exactly => PASS."""
    specs = [
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
        ColumnSpec(name="HR_2", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]
    actual = ["bus_id", "HR_1", "HR_2"]

    status, violations = check_column_names(actual, specs)
    assert status == CheckStatus.PASS
    # No missing_column violations (extra_column violations may exist but not here).
    missing_violations = [v for v in violations if v.error_type == "missing_column"]
    assert len(missing_violations) == 0


# ---------------------------------------------------------------------------
# Test 7: check_column_names_missing_required
# ---------------------------------------------------------------------------


def test_check_column_names_missing_required() -> None:
    """Missing required column HR_2 => FAIL with missing_column violation."""
    specs = [
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
        ColumnSpec(name="HR_2", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]
    actual = ["bus_id", "HR_1"]

    status, violations = check_column_names(actual, specs)
    assert status == CheckStatus.FAIL
    missing = [v for v in violations if v.error_type == "missing_column"]
    assert len(missing) == 1
    assert missing[0].column_name == "HR_2"


# ---------------------------------------------------------------------------
# Test 8: check_column_order_mismatch
# ---------------------------------------------------------------------------


def test_check_column_order_mismatch() -> None:
    """Columns out of canonical order => FAIL indicating bus_id out of position."""
    specs = [
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
        ColumnSpec(name="HR_2", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]
    actual = ["HR_1", "bus_id", "HR_2"]

    status, violations = check_column_order(actual, specs)
    assert status == CheckStatus.FAIL
    assert len(violations) >= 1
    # The violation should mention bus_id being out of position.
    v = violations[0]
    assert v.error_type == "wrong_order"
    assert "bus_id" in v.message


# ---------------------------------------------------------------------------
# Test 9: check_dtype_conformance_pass
# ---------------------------------------------------------------------------


def test_check_dtype_conformance_pass(tmp_path: Path) -> None:
    """Valid int and float values => PASS."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("bus_id,HR_1\n1,100.5\n2,200.0\n")

    specs = [
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]

    status, violations = check_dtype_conformance(csv_file, specs)
    assert status == CheckStatus.PASS
    assert violations == []


# ---------------------------------------------------------------------------
# Test 10: check_dtype_conformance_fail_non_numeric
# ---------------------------------------------------------------------------


def test_check_dtype_conformance_fail_non_numeric(tmp_path: Path) -> None:
    """Non-numeric value 'abc' in FLOAT column => FAIL with wrong_dtype."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("bus_id,HR_1\n1,abc\n")

    specs = [
        ColumnSpec(name="bus_id", dtype=ColumnDtype.INT, unit="none", required=True),
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]

    status, violations = check_dtype_conformance(csv_file, specs)
    assert status == CheckStatus.FAIL
    assert len(violations) >= 1
    v = violations[0]
    assert v.error_type == "wrong_dtype"
    assert v.column_name == "HR_1"
    assert v.actual_value == "abc"


# ---------------------------------------------------------------------------
# Test 11: check_id_columns_not_null_fail
# ---------------------------------------------------------------------------


def test_check_id_columns_not_null_fail(tmp_path: Path) -> None:
    """Empty string in ID column gen_uid => FAIL with null_id."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("gen_uid,HR_1\n,100.0\n")

    specs = [
        ColumnSpec(
            name="gen_uid",
            dtype=ColumnDtype.STR,
            unit="none",
            required=True,
            is_id=True,
        ),
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]

    status, violations = check_id_columns_not_null(csv_file, specs)
    assert status == CheckStatus.FAIL
    assert len(violations) >= 1
    assert violations[0].error_type == "null_id"


# ---------------------------------------------------------------------------
# Test 12: check_time_dimension_pass
# ---------------------------------------------------------------------------


def test_check_time_dimension_pass() -> None:
    """All HR_1..HR_24 present for LOAD_24H => PASS."""
    actual = ["bus_id"] + [f"HR_{h}" for h in range(1, 25)]

    status, violations = check_time_dimension(actual, CsvFileType.LOAD_24H)
    assert status == CheckStatus.PASS
    assert violations == []


# ---------------------------------------------------------------------------
# Test 13: check_time_dimension_missing_hour
# ---------------------------------------------------------------------------


def test_check_time_dimension_missing_hour() -> None:
    """Missing HR_24 for LOAD_24H => FAIL mentioning HR_24."""
    actual = ["bus_id"] + [f"HR_{h}" for h in range(1, 24)]  # HR_1..HR_23

    status, violations = check_time_dimension(actual, CsvFileType.LOAD_24H)
    assert status == CheckStatus.FAIL
    assert len(violations) >= 1
    hr24_violations = [v for v in violations if v.column_name == "HR_24"]
    assert len(hr24_violations) == 1


# ---------------------------------------------------------------------------
# Test 14: check_row_count_exact_pass
# ---------------------------------------------------------------------------


def test_check_row_count_exact_pass() -> None:
    """exact_rows=50 with actual=50 => PASS."""
    entry = FileManifestEntry(
        relative_path="test.csv",
        file_type=CsvFileType.SCENARIO_MULTIPLIERS_WIND,
        columns=[],
        min_rows=50,
        exact_rows=50,
    )

    status, violations = check_row_count(50, entry)
    assert status == CheckStatus.PASS
    assert violations == []


# ---------------------------------------------------------------------------
# Test 15: check_row_count_exact_fail
# ---------------------------------------------------------------------------


def test_check_row_count_exact_fail() -> None:
    """exact_rows=50 with actual=48 => FAIL with actual=48, expected=50."""
    entry = FileManifestEntry(
        relative_path="test.csv",
        file_type=CsvFileType.SCENARIO_MULTIPLIERS_WIND,
        columns=[],
        min_rows=50,
        exact_rows=50,
    )

    status, violations = check_row_count(48, entry)
    assert status == CheckStatus.FAIL
    assert len(violations) == 1
    assert violations[0].actual_value == "48"
    assert violations[0].expected == "50"


# ---------------------------------------------------------------------------
# Test 16: check_no_nan_inf_fail_nan
# ---------------------------------------------------------------------------


def test_check_no_nan_inf_fail_nan(tmp_path: Path) -> None:
    """NaN value in FLOAT column => FAIL with nan_value."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("HR_1,HR_2\n100.0,nan\n")

    specs = [
        ColumnSpec(name="HR_1", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
        ColumnSpec(name="HR_2", dtype=ColumnDtype.FLOAT, unit="MW", required=True),
    ]

    status, violations = check_no_nan_inf(csv_file, specs)
    assert status == CheckStatus.FAIL
    nan_violations = [v for v in violations if v.error_type == "nan_value"]
    assert len(nan_violations) >= 1
    assert nan_violations[0].column_name == "HR_2"


# ---------------------------------------------------------------------------
# Test 17: validate_file_missing_file_skips_downstream
# ---------------------------------------------------------------------------


def test_validate_file_missing_file_skips_downstream(tmp_path: Path) -> None:
    """Missing file => FILE_EXISTS=FAIL, all other checks=SKIP."""
    entry = FileManifestEntry(
        relative_path="nonexistent.csv",
        file_type=CsvFileType.LOAD_24H,
        columns=build_column_specs_load(),
        min_rows=1,
    )

    result = validate_file("case39", tmp_path, entry)
    assert result.file_exists is False
    assert result.checks[CheckId.FILE_EXISTS] == CheckStatus.FAIL

    for check_id, check_status in result.checks.items():
        if check_id != CheckId.FILE_EXISTS:
            assert check_status == CheckStatus.SKIP, (
                f"Expected SKIP for {check_id} when file is missing, got {check_status}"
            )


# ---------------------------------------------------------------------------
# Test 18: validate_network_schema_aggregates_results
# ---------------------------------------------------------------------------


def test_validate_network_schema_aggregates_results(tmp_path: Path) -> None:
    """Network-level validation aggregates per-file results correctly.

    Creates a minimal directory with two valid CSV files matching a subset
    of the manifest, then verifies the aggregation logic.
    """
    # Create a minimal network directory.
    network_dir = tmp_path / "case39"
    network_dir.mkdir()
    scenarios_dir = network_dir / "scenarios"
    scenarios_dir.mkdir()

    # Create load_24h.csv with valid content.
    hr_header = ",".join(f"HR_{h}" for h in range(1, 25))
    hr_values = ",".join("100.0" for _ in range(24))
    load_csv = network_dir / "load_24h.csv"
    load_csv.write_text(f"bus_id,{hr_header}\n1,{hr_values}\n2,{hr_values}\n")

    # Create gen_temporal_params.csv with valid content.
    gen_csv = network_dir / "gen_temporal_params.csv"
    gen_csv.write_text(
        "gen_uid,pmax,pmin,ramp_rate,min_up_time,min_down_time,"
        "startup_cost,shutdown_cost,marginal_cost,fuel_type,unit_type\n"
        "gen1,100.0,10.0,5.0,2.0,1.0,500.0,0.0,30.0,ng,CT\n"
    )

    report = validate_network_schema("case39", tmp_path)

    # The manifest for case39 has 13 entries.
    assert report.total_files_expected == 13
    # We created 2 files.
    assert report.total_files_found == 2
    assert report.total_files_missing == 11
    # There should be failures (11 missing files).
    assert report.total_checks_failed > 0
    assert report.overall_pass is False
    # Verify file_results list length matches manifest.
    assert len(report.file_results) == 13
