"""Post-materialization verification for intermediate CSV export.

Checks that the materialized CSV files and manifest.json produced by
export_intermediate_csvs.py are correct and complete: file counts,
record counts, column headers, and manifest internal consistency.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileInventoryCheck:
    expected_files: list[str]
    found_files: list[str]
    missing_files: list[str]
    unexpected_files: list[str]
    passed: bool


@dataclass(frozen=True)
class RecordCountCheck:
    table_name: str
    materialized_count: int
    reference_count: int
    reference_source: str
    comparison: str  # "==" or "<="
    passed: bool
    message: str


@dataclass(frozen=True)
class ColumnHeaderCheck:
    table_name: str
    csv_columns: list[str]
    schema_columns: list[str]
    passed: bool
    mismatches: list[str]


@dataclass(frozen=True)
class ManifestConsistencyCheck:
    total_records_matches_sum: bool
    total_tables_correct: bool
    sbase_correct: bool
    all_files_exist: bool
    missing_manifest_files: list[str]
    passed: bool


@dataclass
class MaterializationVerification:
    file_inventory: FileInventoryCheck
    record_count_checks: list[RecordCountCheck]
    column_header_checks: list[ColumnHeaderCheck]
    manifest_consistency: ManifestConsistencyCheck
    all_passed: bool
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Expected file inventory (17 CSVs + manifest.json)
# ---------------------------------------------------------------------------

EXPECTED_FILES: list[str] = [
    "area.csv",
    "branch.csv",
    "bus.csv",
    "facts.csv",
    "fixed_shunt.csv",
    "generator.csv",
    "impedance_correction.csv",
    "interarea_transfer.csv",
    "load.csv",
    "manifest.json",
    "multi_section_line.csv",
    "multi_terminal_dc.csv",
    "owner.csv",
    "switched_shunt.csv",
    "transformer.csv",
    "two_terminal_dc.csv",
    "vsc_dc.csv",
    "zone.csv",
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def count_csv_rows(csv_path: Path) -> int:
    """Count data rows in a CSV file (excludes header)."""
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return sum(1 for _ in reader)


def read_csv_header(csv_path: Path) -> list[str]:
    """Read the header row of a CSV file."""
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        return list(header) if header else []


def get_schema_column_order(schema_path: Path) -> list[str]:
    """Extract column names from a JSON Schema file's properties dict."""
    with open(schema_path) as f:
        schema = json.load(f)
    return list(schema.get("properties", {}).keys())


# ---------------------------------------------------------------------------
# Verification functions
# ---------------------------------------------------------------------------


def verify_file_inventory(output_dir: Path) -> FileInventoryCheck:
    """Check that exactly the expected 18 files are present."""
    found = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    expected = sorted(EXPECTED_FILES)
    missing = sorted(set(expected) - set(found))
    unexpected = sorted(set(found) - set(expected))
    passed = not missing and not unexpected
    return FileInventoryCheck(
        expected_files=expected,
        found_files=found,
        missing_files=missing,
        unexpected_files=unexpected,
        passed=passed,
    )


def verify_record_counts(
    output_dir: Path,
    cleaning_summary_path: Path,
    intermediate_manifest_path: Path | None,
) -> list[RecordCountCheck]:
    """Cross-validate CSV row counts against reference sources."""
    checks: list[RecordCountCheck] = []

    # Load cleaning summary
    with open(cleaning_summary_path) as f:
        cleaning = json.load(f)
    cleaned = cleaning["cleaned_network"]

    # Load intermediate manifest (the one we just generated)
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    # --- bus count matches cleaning summary exactly ---
    bus_csv = output_dir / "bus.csv"
    bus_rows = count_csv_rows(bus_csv)
    ref_buses = cleaned["buses"]
    checks.append(
        RecordCountCheck(
            table_name="bus",
            materialized_count=bus_rows,
            reference_count=ref_buses,
            reference_source="summary_cleaning.json:cleaned_network.buses",
            comparison="==",
            passed=bus_rows == ref_buses,
            message=f"bus.csv has {bus_rows} rows, expected {ref_buses}",
        )
    )

    # --- branch + transformer <= branches_total ---
    branch_rows = count_csv_rows(output_dir / "branch.csv")
    xfmr_rows = count_csv_rows(output_dir / "transformer.csv")
    ref_branches = cleaned["branches_total"]
    branch_sum = branch_rows + xfmr_rows
    checks.append(
        RecordCountCheck(
            table_name="branch+transformer",
            materialized_count=branch_sum,
            reference_count=ref_branches,
            reference_source="summary_cleaning.json:cleaned_network.branches_total",
            comparison="<=",
            passed=branch_sum <= ref_branches,
            message=(
                f"branch({branch_rows}) + transformer({xfmr_rows}) = {branch_sum}, "
                f"bound {ref_branches}"
            ),
        )
    )

    # --- generator count within bound ---
    gen_rows = count_csv_rows(output_dir / "generator.csv")
    ref_gens = cleaned["generators_total"]
    checks.append(
        RecordCountCheck(
            table_name="generator",
            materialized_count=gen_rows,
            reference_count=ref_gens,
            reference_source="summary_cleaning.json:cleaned_network.generators_total",
            comparison="<=",
            passed=0 < gen_rows <= ref_gens,
            message=f"generator.csv has {gen_rows} rows, bound {ref_gens}",
        )
    )

    # --- load count within bound ---
    load_rows = count_csv_rows(output_dir / "load.csv")
    ref_loads = 16000  # Upper bound (rounded)
    checks.append(
        RecordCountCheck(
            table_name="load",
            materialized_count=load_rows,
            reference_count=ref_loads,
            reference_source="PRD upper bound",
            comparison="<=",
            passed=0 < load_rows <= ref_loads,
            message=f"load.csv has {load_rows} rows, bound {ref_loads}",
        )
    )

    # --- area count within bound ---
    area_rows = count_csv_rows(output_dir / "area.csv")
    checks.append(
        RecordCountCheck(
            table_name="area",
            materialized_count=area_rows,
            reference_count=49,
            reference_source="PRD upper bound",
            comparison="<=",
            passed=area_rows <= 49,
            message=f"area.csv has {area_rows} rows, bound 49",
        )
    )

    # --- zone count within bound ---
    zone_rows = count_csv_rows(output_dir / "zone.csv")
    checks.append(
        RecordCountCheck(
            table_name="zone",
            materialized_count=zone_rows,
            reference_count=90,
            reference_source="PRD upper bound",
            comparison="<=",
            passed=zone_rows <= 90,
            message=f"zone.csv has {zone_rows} rows, bound 90",
        )
    )

    # --- Cross-validate against intermediate manifest ---
    # Each CSV row count should match the manifest's record_count
    for table_entry in manifest["tables"]:
        tname = table_entry["table_name"]
        fname = table_entry["file_name"]
        csv_path = output_dir / fname
        if csv_path.exists():
            csv_rows = count_csv_rows(csv_path)
            manifest_rc = table_entry["record_count"]
            checks.append(
                RecordCountCheck(
                    table_name=f"{tname}_vs_manifest",
                    materialized_count=csv_rows,
                    reference_count=manifest_rc,
                    reference_source="intermediate manifest.json",
                    comparison="==",
                    passed=csv_rows == manifest_rc,
                    message=(f"{tname}: CSV has {csv_rows} rows, manifest says {manifest_rc}"),
                )
            )

    # --- Empty tables should have 0 data rows ---
    non_empty_types = set(manifest.get("non_empty_record_types", []))
    table_name_to_record_type = {t["table_name"]: t["record_type"] for t in manifest["tables"]}
    empty_tables = [
        tname for tname, rtype in table_name_to_record_type.items() if rtype not in non_empty_types
    ]
    for tname in empty_tables:
        fname = f"{tname}.csv"
        csv_path = output_dir / fname
        if csv_path.exists():
            rows = count_csv_rows(csv_path)
            checks.append(
                RecordCountCheck(
                    table_name=f"{tname}_empty",
                    materialized_count=rows,
                    reference_count=0,
                    reference_source="manifest non_empty_record_types",
                    comparison="==",
                    passed=rows == 0,
                    message=f"{tname} expected empty, has {rows} rows",
                )
            )

    return checks


def verify_column_headers(output_dir: Path, schema_dir: Path) -> list[ColumnHeaderCheck]:
    """Verify that CSV column headers match JSON Schema property order."""
    checks: list[ColumnHeaderCheck] = []

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    for table_entry in manifest["tables"]:
        tname = table_entry["table_name"]
        fname = table_entry["file_name"]
        schema_file = table_entry.get("schema_file", f"{tname}.schema.json")

        csv_path = output_dir / fname
        schema_path = schema_dir / schema_file

        if not csv_path.exists() or not schema_path.exists():
            checks.append(
                ColumnHeaderCheck(
                    table_name=tname,
                    csv_columns=[],
                    schema_columns=[],
                    passed=False,
                    mismatches=[
                        f"File not found: csv={csv_path.exists()}, schema={schema_path.exists()}"
                    ],
                )
            )
            continue

        csv_cols = read_csv_header(csv_path)
        schema_cols = get_schema_column_order(schema_path)

        mismatches: list[str] = []
        if csv_cols != schema_cols:
            # Detail the differences
            if len(csv_cols) != len(schema_cols):
                mismatches.append(
                    f"Column count differs: CSV={len(csv_cols)}, schema={len(schema_cols)}"
                )
            for i, (c, s) in enumerate(zip(csv_cols, schema_cols)):
                if c != s:
                    mismatches.append(f"Position {i}: CSV='{c}', schema='{s}'")
            # Extra columns
            if len(csv_cols) > len(schema_cols):
                extras = csv_cols[len(schema_cols) :]
                mismatches.append(f"Extra CSV columns: {extras}")
            elif len(schema_cols) > len(csv_cols):
                extras = schema_cols[len(csv_cols) :]
                mismatches.append(f"Missing CSV columns: {extras}")

        checks.append(
            ColumnHeaderCheck(
                table_name=tname,
                csv_columns=csv_cols,
                schema_columns=schema_cols,
                passed=len(mismatches) == 0,
                mismatches=mismatches,
            )
        )

    return checks


def verify_manifest_consistency(output_dir: Path) -> ManifestConsistencyCheck:
    """Verify the manifest.json is internally consistent."""
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    tables = manifest["tables"]

    # total_records == sum of per-table record_count
    record_sum = sum(t["record_count"] for t in tables)
    total_records_ok = manifest["total_records"] == record_sum

    # total_tables == 17
    total_tables_ok = manifest["total_tables"] == 17

    # sbase == 100.0
    sbase_ok = manifest["sbase"] == 100.0

    # All referenced files exist
    missing_files: list[str] = []
    for t in tables:
        fpath = output_dir / t["file_name"]
        if not fpath.exists():
            missing_files.append(t["file_name"])
    all_files_ok = len(missing_files) == 0

    passed = total_records_ok and total_tables_ok and sbase_ok and all_files_ok

    return ManifestConsistencyCheck(
        total_records_matches_sum=total_records_ok,
        total_tables_correct=total_tables_ok,
        sbase_correct=sbase_ok,
        all_files_exist=all_files_ok,
        missing_manifest_files=missing_files,
        passed=passed,
    )


def run_materialization_verification(
    output_dir: Path,
    cleaning_summary_path: Path,
    intermediate_manifest_path: Path | None,
    schema_dir: Path,
) -> MaterializationVerification:
    """Run all verification checks and return a summary."""
    errors: list[str] = []

    # File inventory
    try:
        file_inv = verify_file_inventory(output_dir)
    except Exception as e:
        errors.append(f"File inventory check failed: {e}")
        file_inv = FileInventoryCheck(
            expected_files=EXPECTED_FILES,
            found_files=[],
            missing_files=EXPECTED_FILES,
            unexpected_files=[],
            passed=False,
        )

    # Record counts
    try:
        record_checks = verify_record_counts(
            output_dir, cleaning_summary_path, intermediate_manifest_path
        )
    except Exception as e:
        errors.append(f"Record count check failed: {e}")
        record_checks = []

    # Column headers
    try:
        header_checks = verify_column_headers(output_dir, schema_dir)
    except Exception as e:
        errors.append(f"Column header check failed: {e}")
        header_checks = []

    # Manifest consistency
    try:
        manifest_check = verify_manifest_consistency(output_dir)
    except Exception as e:
        errors.append(f"Manifest consistency check failed: {e}")
        manifest_check = ManifestConsistencyCheck(
            total_records_matches_sum=False,
            total_tables_correct=False,
            sbase_correct=False,
            all_files_exist=False,
            missing_manifest_files=[],
            passed=False,
        )

    all_passed = (
        file_inv.passed
        and all(c.passed for c in record_checks)
        and all(c.passed for c in header_checks)
        and manifest_check.passed
        and not errors
    )

    return MaterializationVerification(
        file_inventory=file_inv,
        record_count_checks=record_checks,
        column_header_checks=header_checks,
        manifest_consistency=manifest_check,
        all_passed=all_passed,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Run verification checks and print results."""
    parser = argparse.ArgumentParser(description="Verify materialized intermediate CSV artifacts.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory containing materialized CSVs and manifest.json",
    )
    parser.add_argument(
        "--cleaning-summary",
        type=Path,
        required=True,
        help="Path to summary_cleaning.json",
    )
    parser.add_argument(
        "--schema-dir",
        type=Path,
        required=True,
        help="Directory containing JSON Schema files",
    )
    parser.add_argument(
        "--intermediate-manifest",
        type=Path,
        default=None,
        help="Path to pre-filter intermediate_manifest.json (optional)",
    )
    args = parser.parse_args(argv)

    result = run_materialization_verification(
        output_dir=args.output_dir,
        cleaning_summary_path=args.cleaning_summary,
        intermediate_manifest_path=args.intermediate_manifest,
        schema_dir=args.schema_dir,
    )

    # Print summary
    print("=" * 60)
    print("MATERIALIZATION VERIFICATION REPORT")
    print("=" * 60)

    print(f"\nFile Inventory: {'PASS' if result.file_inventory.passed else 'FAIL'}")
    if result.file_inventory.missing_files:
        print(f"  Missing: {result.file_inventory.missing_files}")
    if result.file_inventory.unexpected_files:
        print(f"  Unexpected: {result.file_inventory.unexpected_files}")

    print(f"\nRecord Count Checks ({len(result.record_count_checks)}):")
    for c in result.record_count_checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"  [{status}] {c.message}")

    print(f"\nColumn Header Checks ({len(result.column_header_checks)}):")
    for c in result.column_header_checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"  [{status}] {c.table_name}")
        if c.mismatches:
            for m in c.mismatches:
                print(f"    - {m}")

    print(f"\nManifest Consistency: {'PASS' if result.manifest_consistency.passed else 'FAIL'}")
    print(f"  total_records sum: {result.manifest_consistency.total_records_matches_sum}")
    print(f"  total_tables == 17: {result.manifest_consistency.total_tables_correct}")
    print(f"  sbase == 100: {result.manifest_consistency.sbase_correct}")
    print(f"  all files exist: {result.manifest_consistency.all_files_exist}")

    if result.errors:
        print(f"\nErrors: {result.errors}")

    print(f"\nOVERALL: {'PASS' if result.all_passed else 'FAIL'}")

    sys.exit(0 if result.all_passed else 1)


if __name__ == "__main__":
    main()
