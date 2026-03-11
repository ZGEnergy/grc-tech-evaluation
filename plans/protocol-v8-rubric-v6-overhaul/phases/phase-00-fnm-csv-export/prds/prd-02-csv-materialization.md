# PRD: Intermediate CSV Materialization

## Overview

This deliverable executes the export pipeline script (PRD-01) inside the devcontainer
and commits the resulting CSV files and `manifest.json` to
`data/fnm/reference/cleaned/intermediate/`. It then verifies that the materialized
artifacts are correct and complete: file counts match expectations, record counts align
with the cleaning manifest (`summary_cleaning.json`) and the intermediate manifest
(`intermediate_manifest.json`), column headers conform to JSON Schema definitions, and
all non-empty tables contain plausible data.

Unlike typical code deliverables, this PRD's primary output is committed data artifacts,
not source code. The "tests" are post-materialization verification checks that confirm
the committed files are internally consistent, schema-compliant, and concordant with
upstream reference data. A small verification script codifies these checks so they can
be re-run if the pipeline is ever re-executed.

## Goals

1. **Execute the export pipeline** by running `export_intermediate_csvs.py` (PRD-01)
   inside the devcontainer via `dc-exec`, targeting the output directory
   `data/fnm/reference/cleaned/intermediate/`.

2. **Verify file inventory completeness** -- confirm that exactly 17 CSV files plus
   one `manifest.json` are present in the output directory (18 files total).

3. **Cross-validate record counts against `summary_cleaning.json`** -- confirm that
   `bus.csv` contains 27,862 rows (matching `cleaned_network.buses`), and that
   `branch.csv` + `transformer.csv` row counts sum to no more than 32,606
   (`cleaned_network.branches_total`).

4. **Cross-validate record counts against `intermediate_manifest.json`** -- for each
   non-empty table, compare the materialized row count against the pre-filter
   `expected_record_count` from the raw PSS/E parse and confirm the post-filter count
   is strictly less than or equal to the pre-filter count (island filtering removes
   rows).

5. **Verify manifest internal consistency** -- confirm that the committed
   `manifest.json` has `total_records` equal to the sum of per-table `record_count`
   values, `total_tables == 17`, `sbase == 100.0`, and all listed `file_name` values
   correspond to files that actually exist in the output directory.

6. **Verify column-header conformance** -- for every CSV, confirm the header row's
   column names exactly match the `properties` keys in the corresponding JSON Schema
   file (same names, same order).

7. **Commit all output artifacts** to the repository so downstream deliverables
   (PRD-03, PRD-04) can reference them without re-running the pipeline.

## Non-Goals

- **Writing or modifying the export pipeline script** -- that is PRD-01's scope.
  This deliverable treats the script as a black box and only runs it.
- **Modifying JSON Schema files** -- schemas in `data/fnm/intermediate/schemas/` are
  read-only inputs. If a schema mismatch is found, the fix belongs in PRD-01.
- **Validating individual cell values or data types** -- PRD-01's built-in JSON Schema
  validation covers per-row type checking. This deliverable focuses on structural and
  count-level verification.
- **Updating `dcpf_reference.py`** -- handled by PRD-03.
- **Running DCPF from the CSV path** -- handled by PRD-04.
- **Modifying the cleaning pipeline or re-cleaning the `.mat` file** -- the cleaned
  `.mat` is a fixed input.

## Data Structures

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileInventoryCheck:
    """Result of checking that all expected files exist in the output directory."""

    expected_files: list[str]
    """Filenames that should be present (17 CSVs + manifest.json)."""

    found_files: list[str]
    """Filenames actually found in the directory."""

    missing_files: list[str]
    """Expected files not found."""

    unexpected_files: list[str]
    """Files found that were not expected."""

    passed: bool
    """True if missing_files is empty."""


@dataclass(frozen=True)
class RecordCountCheck:
    """Result of comparing a table's materialized row count against a reference."""

    table_name: str
    """Intermediate table name (e.g. 'bus', 'branch')."""

    materialized_count: int
    """Row count in the committed CSV (excluding header)."""

    reference_count: int
    """Expected count from the reference source."""

    reference_source: str
    """Which reference was used (e.g. 'summary_cleaning.json', 'intermediate_manifest.json')."""

    comparison: str
    """Comparison type: 'exact' or 'upper_bound'."""

    passed: bool
    """True if the comparison holds."""

    message: str
    """Human-readable explanation."""


@dataclass(frozen=True)
class ColumnHeaderCheck:
    """Result of comparing a CSV's header row against its JSON Schema."""

    table_name: str
    """Intermediate table name."""

    csv_columns: list[str]
    """Column names from the CSV header row."""

    schema_columns: list[str]
    """Property names from the JSON Schema (in order)."""

    passed: bool
    """True if csv_columns == schema_columns."""

    mismatches: list[str]
    """Human-readable descriptions of any differences."""


@dataclass(frozen=True)
class ManifestConsistencyCheck:
    """Result of verifying the manifest's internal consistency."""

    total_records_matches_sum: bool
    """True if total_records == sum of per-table record_count."""

    total_tables_correct: bool
    """True if total_tables == 17."""

    sbase_correct: bool
    """True if sbase == 100.0."""

    all_files_exist: bool
    """True if every file_name in the manifest exists in the output directory."""

    missing_manifest_files: list[str]
    """file_name values that don't correspond to actual files."""

    passed: bool
    """True if all sub-checks pass."""


@dataclass
class MaterializationVerification:
    """Aggregate result of all post-materialization verification checks."""

    file_inventory: FileInventoryCheck
    """File existence check."""

    record_count_checks: list[RecordCountCheck]
    """Per-table record count comparisons."""

    column_header_checks: list[ColumnHeaderCheck]
    """Per-table column header conformance checks."""

    manifest_consistency: ManifestConsistencyCheck
    """Manifest internal consistency check."""

    all_passed: bool
    """True if every sub-check passed."""

    errors: list[str] = field(default_factory=list)
    """Aggregated error messages from any failed checks."""
```

## API

```python
def verify_file_inventory(output_dir: Path) -> FileInventoryCheck:
    """Check that all 18 expected files (17 CSVs + manifest.json) exist.

    Enumerates the output directory and compares against the canonical list
    of 17 PSS/E v31 table names (as CSV filenames) plus manifest.json.

    Args:
        output_dir: Path to data/fnm/reference/cleaned/intermediate/.

    Returns:
        A FileInventoryCheck with pass/fail and any missing or unexpected files.
    """
    ...


def count_csv_rows(csv_path: Path) -> int:
    """Count data rows in a CSV file (excluding the header line).

    Args:
        csv_path: Path to a CSV file.

    Returns:
        Number of data rows. Returns 0 for header-only files.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If the file is empty (no header).
    """
    ...


def read_csv_header(csv_path: Path) -> list[str]:
    """Read and return the column names from a CSV file's header row.

    Args:
        csv_path: Path to a CSV file.

    Returns:
        List of column name strings in file order.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If the file is empty.
    """
    ...


def get_schema_column_order(schema_path: Path) -> list[str]:
    """Extract the ordered list of property names from a JSON Schema file.

    Reads the schema's "properties" key and returns names in their
    definition order (which is the canonical column order for CSVs).

    Args:
        schema_path: Path to a table's JSON Schema file.

    Returns:
        List of property name strings in schema-definition order.
    """
    ...


def verify_record_counts(
    output_dir: Path,
    cleaning_summary_path: Path,
    intermediate_manifest_path: Path,
) -> list[RecordCountCheck]:
    """Cross-validate CSV row counts against reference manifests.

    Performs two categories of checks:
      1. Exact-match checks against summary_cleaning.json:
         - bus.csv row count == cleaned_network.buses (27,862)
      2. Upper-bound checks against intermediate_manifest.json:
         - For each non-empty table, materialized count <= expected_record_count
           (because island filtering removes rows from the raw PSS/E totals)
      3. Sum check: branch.csv + transformer.csv <= branches_total (32,606)

    Args:
        output_dir: Path to the intermediate output directory.
        cleaning_summary_path: Path to summary_cleaning.json.
        intermediate_manifest_path: Path to intermediate_manifest.json.

    Returns:
        List of RecordCountCheck results, one per validated table.
    """
    ...


def verify_column_headers(
    output_dir: Path,
    schema_dir: Path,
) -> list[ColumnHeaderCheck]:
    """Verify that every CSV's column headers match its JSON Schema.

    For each CSV in the output directory, loads the corresponding schema
    from schema_dir, extracts the property order, and compares against
    the CSV header row.

    Args:
        output_dir: Path to the intermediate output directory.
        schema_dir: Path to data/fnm/intermediate/schemas/.

    Returns:
        List of ColumnHeaderCheck results, one per CSV.
    """
    ...


def verify_manifest_consistency(
    output_dir: Path,
) -> ManifestConsistencyCheck:
    """Verify the manifest.json file's internal consistency.

    Checks:
      - total_records == sum of per-table record_count
      - total_tables == 17
      - sbase == 100.0
      - Every file_name in the tables array exists in output_dir

    Args:
        output_dir: Path to the intermediate output directory.

    Returns:
        A ManifestConsistencyCheck with per-sub-check results.
    """
    ...


def run_materialization_verification(
    output_dir: Path,
    cleaning_summary_path: Path,
    intermediate_manifest_path: Path,
    schema_dir: Path,
) -> MaterializationVerification:
    """Run all post-materialization verification checks.

    Orchestrates file inventory, record count, column header, and manifest
    consistency checks, then aggregates results.

    Args:
        output_dir: Path to data/fnm/reference/cleaned/intermediate/.
        cleaning_summary_path: Path to summary_cleaning.json.
        intermediate_manifest_path: Path to intermediate_manifest.json.
        schema_dir: Path to data/fnm/intermediate/schemas/.

    Returns:
        A MaterializationVerification with all sub-results and overall pass/fail.
    """
    ...


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the verification script.

    Usage::

        python data/fnm/scripts/verify_materialization.py \\
            --output-dir data/fnm/reference/cleaned/intermediate \\
            --cleaning-summary data/fnm/reference/cleaned/summary_cleaning.json \\
            --intermediate-manifest data/fnm/reference/intermediate_manifest.json \\
            --schema-dir data/fnm/intermediate/schemas

    Prints a human-readable report and exits with code 0 on success,
    1 on any verification failure.

    Args:
        argv: Command-line arguments. If None, reads from sys.argv.
    """
    ...
```

## Success Criteria

### Verification Checks

1. **`test_output_directory_exists`** -- The directory
   `data/fnm/reference/cleaned/intermediate/` exists after pipeline execution.

2. **`test_file_inventory_complete`** -- Exactly 18 files are present: `bus.csv`,
   `load.csv`, `fixed_shunt.csv`, `generator.csv`, `branch.csv`, `transformer.csv`,
   `area.csv`, `two_terminal_dc.csv`, `vsc_dc.csv`, `impedance_correction.csv`,
   `multi_terminal_dc.csv`, `multi_section_line.csv`, `zone.csv`,
   `interarea_transfer.csv`, `owner.csv`, `facts.csv`, `switched_shunt.csv`, and
   `manifest.json`.

3. **`test_no_unexpected_files`** -- The output directory contains no files beyond
   the 18 expected artifacts (no temp files, no `.gitkeep`, etc.).

4. **`test_bus_count_matches_cleaning_summary`** -- `bus.csv` contains exactly
   27,862 data rows, matching `summary_cleaning.json`'s `cleaned_network.buses`.

5. **`test_branch_transformer_sum_within_bound`** -- The sum of `branch.csv` and
   `transformer.csv` row counts is less than or equal to 32,606
   (`cleaned_network.branches_total` from `summary_cleaning.json`).

6. **`test_generator_count_within_bound`** -- `generator.csv` row count is less
   than or equal to 5,768 (`intermediate_manifest.json`'s generator
   `expected_record_count`) and greater than 0.

7. **`test_load_count_within_bound`** -- `load.csv` row count is less than or
   equal to 15,062 (`intermediate_manifest.json`'s load `expected_record_count`)
   and greater than 0.

8. **`test_area_count_within_bound`** -- `area.csv` row count is less than or
   equal to 49 (`intermediate_manifest.json`'s area `expected_record_count`).

9. **`test_zone_count_within_bound`** -- `zone.csv` row count is less than or
   equal to 90 (`intermediate_manifest.json`'s zone `expected_record_count`).

10. **`test_empty_tables_are_header_only`** -- Each of `two_terminal_dc.csv`,
    `vsc_dc.csv`, `impedance_correction.csv`, `multi_terminal_dc.csv`,
    `multi_section_line.csv`, `interarea_transfer.csv`, `owner.csv`, and
    `facts.csv` contains exactly 1 line (header only, zero data rows).

11. **`test_bus_csv_columns_match_schema`** -- The header row of `bus.csv`
    matches the property names and order in `bus.schema.json`.

12. **`test_branch_csv_columns_match_schema`** -- The header row of `branch.csv`
    matches `branch.schema.json`.

13. **`test_transformer_csv_columns_match_schema`** -- The header row of
    `transformer.csv` matches `transformer.schema.json`.

14. **`test_all_csv_columns_match_schemas`** -- For every one of the 17 CSVs,
    the header row matches its corresponding JSON Schema property order.

15. **`test_manifest_total_records_equals_sum`** -- The `total_records` field in
    the committed `manifest.json` equals the sum of all per-table `record_count`
    values.

16. **`test_manifest_total_tables_is_17`** -- `total_tables == 17` in
    `manifest.json`.

17. **`test_manifest_sbase_is_100`** -- `sbase == 100.0` in `manifest.json`.

18. **`test_manifest_file_references_valid`** -- Every `file_name` listed in the
    manifest's `tables` array corresponds to an actual file in the output
    directory.

## File Location

Verification script:

```
data/fnm/scripts/verify_materialization.py
```

Materialized output artifacts (committed to repo):

```
data/fnm/reference/cleaned/intermediate/
    bus.csv
    load.csv
    fixed_shunt.csv
    generator.csv
    branch.csv
    transformer.csv
    area.csv
    two_terminal_dc.csv
    vsc_dc.csv
    impedance_correction.csv
    multi_terminal_dc.csv
    multi_section_line.csv
    zone.csv
    interarea_transfer.csv
    owner.csv
    facts.csv
    switched_shunt.csv
    manifest.json
```

## Repository

`grc-tech-evaluation`

## Dependencies

### Internal Dependencies

- **PRD-01 (`data/fnm/scripts/export_intermediate_csvs.py`)** -- The export pipeline
  script that produces the CSV files and manifest. Must be implemented and functional
  before this deliverable can execute.
- **`data/fnm/reference/cleaned/fnm_main_island.mat`** -- Input to the export pipeline.
  Already committed.
- **`data/fnm/reference/excluded_buses.json`** -- Input to the export pipeline.
  Already committed.
- **`data/fnm/reference/cleaned/summary_cleaning.json`** -- Reference for
  cross-validation of bus counts and branch totals. Already committed.
- **`data/fnm/reference/intermediate_manifest.json`** -- Reference for pre-filter
  record counts from the raw PSS/E parse. Used as upper bounds for post-filter
  row counts. Already committed.
- **`data/fnm/intermediate/schemas/*.schema.json`** -- JSON Schema files defining
  column names and types for each table. Used for column-header verification.
  Already committed.

### External Dependencies

- **Python 3.12** -- Available in the devcontainer.
- **Standard library only** -- The verification script uses only `csv`, `json`,
  `pathlib`, `argparse`, and `sys`. No third-party packages required beyond what
  PRD-01 already installs.

## Open Questions

None. All design decisions for this deliverable follow directly from PRD-01's output
contract and the existing reference data files.
