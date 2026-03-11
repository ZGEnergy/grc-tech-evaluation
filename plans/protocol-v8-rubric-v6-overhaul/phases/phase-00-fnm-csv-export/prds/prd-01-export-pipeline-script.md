# PRD: Export Pipeline Script

## Overview

This deliverable creates a standalone Python script that reads the cleaned MATPOWER
case file (`data/fnm/reference/cleaned/fnm_main_island.mat`), extracts all 17 PSS/E
v31 record types into separate intermediate-format CSV files, writes a sidecar
`manifest.json` with system-level metadata (baseMVA, frequency, case ID), and validates
every output artifact against the existing JSON Schema files in
`data/fnm/intermediate/schemas/`. The script also applies two critical data
transformations at export time: splitting the MATPOWER `branch` matrix into separate
`branch.csv` and `transformer.csv` tables, and converting tap ratio values of 0 (the
MATPOWER sentinel for "nominal tap") to the PSS/E-standard 1.0.

The export pipeline eliminates the MATPOWER-format bias identified in the v7 protocol
by materializing a format-neutral intermediate representation. Downstream consumers
(v8 protocol tests, `dcpf_reference.py`, evaluate-tool skill) will read these CSVs
instead of parsing `.mat` files directly, ensuring all six tools under evaluation
start from identical tabular data.

## Goals

1. **Read the cleaned MATPOWER `.mat` case** using Python stdlib or scipy.io and
   extract all data matrices (bus, gen, branch, gencost, areas, dcline, bus_name)
   plus scalar fields (baseMVA, version).

2. **Split MATPOWER branch data into separate branch and transformer CSVs** by
   detecting rows with nonzero tap ratio (column index 8) or nonzero phase shift
   (column index 9) -- these are transformers in MATPOWER's merged representation.
   Produce `branch.csv` with columns matching `branch.schema.json` and
   `transformer.csv` with columns matching `transformer.schema.json`.

3. **Apply tap=0 to 1.0 normalization** so that MATPOWER's sentinel value 0 (meaning
   "nominal turns ratio") is converted to the PSS/E-standard explicit 1.0 before
   writing transformer CSV rows. This prevents every downstream tool from independently
   re-implementing this convention.

4. **Filter to main-island buses** using the excluded bus set from
   `data/fnm/reference/excluded_buses.json`, removing all rows referencing excluded
   buses from every table (bus, load, generator, branch, transformer, shunt, etc.).

5. **Write a `manifest.json` sidecar** conforming to `manifest.schema.json` that
   records baseMVA (sbase), base frequency (basfrq), case ID, canonical parser name,
   per-table metadata (file name, record count, column count, schema file path),
   totals, and a generation timestamp.

6. **Validate all output CSVs and the manifest against their JSON Schema files**
   using the `jsonschema` library, failing with a nonzero exit code and diagnostic
   message if any row or the manifest violates its schema.

## Non-Goals

- **Executing the pipeline and committing artifacts** -- handled by PRD-02
  (Intermediate CSV Materialization).
- **Modifying `dcpf_reference.py` to consume separate CSVs** -- handled by PRD-03
  (Separate-Table Support).
- **Reproducing the DCPF reference from the CSV path** -- handled by PRD-04
  (Reproducibility Validation).
- **Parsing the raw PSS/E `.raw` file directly** -- the script reads only the
  pre-cleaned MATPOWER `.mat` file produced by the existing cleaning pipeline.
- **Handling 3-winding transformers with full PSS/E fidelity** -- the MATPOWER `.mat`
  format already flattens 3-winding transformers into equivalent 2-winding pairs
  during `psse2mpc`; this script preserves that representation.
- **Exporting record types that MATPOWER drops entirely** (Two-Terminal DC, VSC DC,
  Multi-Terminal DC, Multi-Section Line, Impedance Correction, FACTS) -- these have
  zero rows in the MATPOWER case and will be written as empty CSVs (header only) to
  satisfy manifest completeness.

## Data Structures

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MatpowerCase:
    """Parsed contents of a MATPOWER .mat case file."""

    baseMVA: float
    """System MVA base (typically 100.0)."""

    version: str
    """MATPOWER case version string (e.g. '2')."""

    bus: list[list[float]]
    """Bus matrix: each inner list is one bus row, 13 columns."""

    gen: list[list[float]]
    """Generator matrix: each inner list is one generator row, 21 columns."""

    branch: list[list[float]]
    """Branch matrix (includes transformers): each inner list is one row, 13 columns."""

    gencost: list[list[float]]
    """Generator cost matrix (variable width)."""

    areas: list[list[float]]
    """Area interchange data matrix."""

    bus_name: list[str]
    """Bus names indexed by row position (parallel to bus matrix)."""

    dcline: list[list[float]]
    """DC line matrix (often empty)."""


@dataclass(frozen=True)
class TableExport:
    """Metadata about one exported CSV table."""

    table_name: str
    """Intermediate format table name (e.g. 'bus', 'branch', 'transformer')."""

    record_type: str
    """PSS/E v31 record type name (e.g. 'Bus', 'Branch', 'Transformer')."""

    file_name: str
    """Output CSV filename (e.g. 'bus.csv')."""

    file_path: Path
    """Absolute path to the written CSV file."""

    record_count: int
    """Number of data rows written (excluding header)."""

    column_count: int
    """Number of columns in the CSV (including all schema fields)."""

    schema_file: str
    """Relative path to the JSON Schema file for this table."""


@dataclass(frozen=True)
class ExportManifest:
    """Top-level manifest for the intermediate CSV export."""

    sbase: float
    """System MVA base."""

    basfrq: float
    """System base frequency in Hz (60.0 for ERCOT)."""

    rev: float
    """PSS/E revision number (31 for v31 format)."""

    case_id: str
    """Case identification string."""

    canonical_parser: str
    """Parser that produced the source data ('matpower')."""

    tables: list[TableExport]
    """Metadata for each exported table."""

    total_records: int
    """Sum of record_count across all tables."""

    total_tables: int
    """Number of tables exported."""

    non_empty_record_types: list[str]
    """Table names with record_count > 0."""

    schema_version: str
    """Intermediate format schema version (e.g. '1.0')."""

    generated_timestamp: str
    """ISO 8601 timestamp of export."""


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating one CSV or manifest against its JSON Schema."""

    artifact_name: str
    """Name of the validated artifact (e.g. 'bus.csv', 'manifest.json')."""

    is_valid: bool
    """True if all rows/the manifest pass schema validation."""

    errors: list[str]
    """Human-readable error descriptions, empty if is_valid."""

    rows_checked: int
    """Number of rows validated (0 for manifest)."""


@dataclass
class ExportResult:
    """Aggregate result of the full export pipeline."""

    manifest: ExportManifest
    """The written manifest."""

    table_exports: list[TableExport]
    """Per-table export metadata."""

    validations: list[ValidationResult]
    """Per-artifact validation results."""

    output_dir: Path
    """Directory where all artifacts were written."""

    success: bool
    """True if all exports and validations passed."""

    errors: list[str] = field(default_factory=list)
    """Top-level errors, empty on success."""
```

## API

```python
def load_matpower_case(mat_path: Path) -> MatpowerCase:
    """Load a MATPOWER .mat case file into a structured container.

    Reads the .mat file using scipy.io.loadmat, extracts the mpc struct,
    and normalizes all matrices to list-of-lists with Python-native floats.

    Args:
        mat_path: Absolute path to the .mat file.

    Returns:
        A MatpowerCase with all extracted matrices and scalars.

    Raises:
        FileNotFoundError: If mat_path does not exist.
        ValueError: If the .mat file lacks the expected mpc struct or baseMVA.
    """
    ...


def load_excluded_buses(excluded_buses_path: Path) -> set[int]:
    """Load the set of excluded bus numbers from the JSON registry.

    Reads the excluded_buses.json produced by bus_exclusion_registry.py and
    extracts all bus numbers regardless of exclusion reason.

    Args:
        excluded_buses_path: Path to excluded_buses.json.

    Returns:
        Set of integer bus numbers to exclude from export.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON structure is invalid.
    """
    ...


def split_branches_and_transformers(
    branch_matrix: list[list[float]],
    bus_numbers: set[int],
) -> tuple[list[dict[str, int | float | str]], list[dict[str, int | float | str]]]:
    """Split the MATPOWER branch matrix into branch and transformer rows.

    A row is classified as a transformer if tap ratio (column 8) != 0 or
    phase shift angle (column 9) != 0. Rows where both endpoints are in
    bus_numbers are retained; others are filtered out.

    For transformer rows, a tap ratio of 0 is converted to 1.0.

    Args:
        branch_matrix: Raw MATPOWER branch matrix (13 columns per row).
        bus_numbers: Set of bus numbers in the main island.

    Returns:
        Tuple of (branch_rows, transformer_rows) where each row is a dict
        keyed by the intermediate schema field names.
    """
    ...


def normalize_tap_ratio(tap: float) -> float:
    """Convert MATPOWER tap=0 sentinel to PSS/E-standard 1.0.

    MATPOWER uses 0.0 to mean 'nominal turns ratio' while PSS/E stores
    the explicit value 1.0. All other values pass through unchanged.

    Args:
        tap: Raw tap ratio value from the MATPOWER branch matrix.

    Returns:
        1.0 if tap == 0.0, otherwise tap unchanged.
    """
    ...


def filter_rows_by_bus(
    rows: list[dict[str, int | float | str]],
    bus_numbers: set[int],
    bus_key: str = "I",
) -> list[dict[str, int | float | str]]:
    """Filter table rows to retain only those referencing main-island buses.

    For tables with a single bus reference (bus, load, generator, shunt),
    filters on the bus_key column. For branch/transformer tables, filters
    on both I and J columns.

    Args:
        rows: List of row dicts.
        bus_numbers: Allowed bus numbers.
        bus_key: Column name containing the bus number to filter on.

    Returns:
        Filtered list of row dicts.
    """
    ...


def export_table_to_csv(
    rows: list[dict[str, int | float | str]],
    schema_path: Path,
    output_path: Path,
) -> TableExport:
    """Write a list of row dicts to a CSV file with column order from the schema.

    Reads the JSON Schema to determine column names and ordering, then writes
    a header row followed by data rows. Integer-typed fields are written without
    decimal points; number-typed fields preserve full precision.

    Args:
        rows: Data rows as dicts keyed by field name.
        schema_path: Path to the JSON Schema for this table.
        output_path: Destination CSV file path.

    Returns:
        A TableExport with metadata about the written file.

    Raises:
        ValueError: If any row contains a key not in the schema.
    """
    ...


def build_manifest(
    case: MatpowerCase,
    table_exports: list[TableExport],
    schema_version: str = "1.0",
) -> ExportManifest:
    """Construct the export manifest from case metadata and table exports.

    Populates all required fields from manifest.schema.json including sbase,
    basfrq, rev, case_id, table metadata, totals, and timestamp.

    Args:
        case: The loaded MATPOWER case (for baseMVA, version).
        table_exports: List of per-table export metadata.
        schema_version: Intermediate format schema version.

    Returns:
        A fully populated ExportManifest.
    """
    ...


def write_manifest(manifest: ExportManifest, output_path: Path) -> None:
    """Serialize an ExportManifest to JSON and write to disk.

    Output conforms to manifest.schema.json.

    Args:
        manifest: The manifest to write.
        output_path: Destination path for manifest.json.
    """
    ...


def validate_csv_against_schema(
    csv_path: Path,
    schema_path: Path,
) -> ValidationResult:
    """Validate every row of a CSV file against its JSON Schema.

    Reads the CSV, converts each row to a typed dict (using schema type
    information for int/float/string coercion), and validates against the
    schema using jsonschema.validate().

    Args:
        csv_path: Path to the CSV file.
        schema_path: Path to the JSON Schema file.

    Returns:
        A ValidationResult with per-row error details if invalid.
    """
    ...


def validate_manifest_against_schema(
    manifest_path: Path,
    schema_path: Path,
) -> ValidationResult:
    """Validate a manifest.json file against manifest.schema.json.

    Args:
        manifest_path: Path to the manifest JSON.
        schema_path: Path to manifest.schema.json.

    Returns:
        A ValidationResult.
    """
    ...


def run_export_pipeline(
    mat_path: Path,
    excluded_buses_path: Path,
    schema_dir: Path,
    output_dir: Path,
) -> ExportResult:
    """Orchestrate the full export pipeline.

    Steps:
      1. Load the MATPOWER case.
      2. Load excluded buses.
      3. Compute the main-island bus set.
      4. Extract and filter each table.
      5. Split branch/transformer.
      6. Apply tap normalization.
      7. Write CSVs.
      8. Build and write manifest.
      9. Validate all artifacts.

    Args:
        mat_path: Path to the cleaned .mat file.
        excluded_buses_path: Path to excluded_buses.json.
        schema_dir: Path to the directory containing JSON Schema files.
        output_dir: Directory for all output artifacts.

    Returns:
        An ExportResult summarizing the pipeline execution.
    """
    ...


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Usage::

        python -m fnm.scripts.export_intermediate_csvs \\
            --mat-path data/fnm/reference/cleaned/fnm_main_island.mat \\
            --excluded-buses data/fnm/reference/excluded_buses.json \\
            --schema-dir data/fnm/intermediate/schemas \\
            --output-dir data/fnm/reference/cleaned/intermediate

    Args:
        argv: Command-line arguments. If None, reads from sys.argv.
    """
    ...
```

## Success Criteria

### Unit Tests

1. **`test_load_matpower_case_extracts_basemva`** -- Load the cleaned `.mat` file and
   verify `baseMVA == 100.0`.

2. **`test_load_matpower_case_extracts_bus_matrix_shape`** -- Verify the bus matrix
   has the expected number of rows (30,307 pre-filter) and 13 columns.

3. **`test_load_excluded_buses_count`** -- Load `excluded_buses.json` and verify the
   set contains 2,445 bus numbers matching the registry's `excluded_total`.

4. **`test_split_branches_separates_transformers`** -- Given a synthetic branch matrix
   with 3 plain branches (tap=0, shift=0) and 2 transformers (tap!=0), verify the
   split produces 3 branch rows and 2 transformer rows.

5. **`test_normalize_tap_zero_becomes_one`** -- Verify `normalize_tap_ratio(0.0)`
   returns `1.0` and `normalize_tap_ratio(1.05)` returns `1.05`.

6. **`test_normalize_tap_on_transformer_rows`** -- After splitting, verify every
   transformer row has `WINDV1 != 0.0` (i.e., the 0-to-1.0 conversion was applied).

7. **`test_filter_rows_removes_excluded_buses`** -- Given bus rows with IDs {1, 2, 3}
   and excluded set {2}, verify only buses 1 and 3 remain.

8. **`test_filter_branch_rows_removes_both_endpoints`** -- Given branch rows
   [(1,2), (2,3), (1,3)] and excluded set {2}, verify only the (1,3) row remains.

9. **`test_export_csv_column_order_matches_schema`** -- Export a bus table and verify
   the CSV header row matches the property order in `bus.schema.json`.

10. **`test_export_csv_integer_fields_no_decimal`** -- Verify integer-typed fields
    (e.g., bus I, IDE) are written without `.0` suffixes in the CSV.

11. **`test_manifest_contains_all_tables`** -- Verify the manifest lists exactly the
    17 PSS/E v31 record types (some with record_count=0 for dropped types).

12. **`test_manifest_sbase_matches_case`** -- Verify `manifest.sbase == 100.0`.

13. **`test_manifest_total_records_is_sum`** -- Verify `total_records` equals the sum
    of all per-table `record_count` values.

14. **`test_validate_bus_csv_passes_schema`** -- Run schema validation on the exported
    `bus.csv` and verify `is_valid == True` with zero errors.

15. **`test_validate_manifest_passes_schema`** -- Run schema validation on
    `manifest.json` and verify it passes `manifest.schema.json`.

16. **`test_validate_csv_detects_invalid_row`** -- Construct a CSV with a deliberately
    invalid row (e.g., string in an integer field) and verify validation catches it.

17. **`test_empty_table_produces_header_only_csv`** -- For a record type with zero
    rows (e.g., `two_terminal_dc`), verify the CSV contains exactly one line (the
    header).

18. **`test_run_export_pipeline_end_to_end`** -- Run the full pipeline on the actual
    cleaned `.mat` file and verify: all CSVs exist, manifest exists, all validations
    pass, bus count equals 27,862 (main island), branch + transformer counts sum to
    match the original branch matrix rows minus excluded.

## File Location

```
data/fnm/scripts/export_intermediate_csvs.py
```

Output artifacts written to:

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

- **`data/fnm/reference/cleaned/fnm_main_island.mat`** -- The cleaned MATPOWER case
  file produced by the existing cleaning pipeline. Must exist before the script runs.
- **`data/fnm/reference/excluded_buses.json`** -- The bus exclusion registry produced
  by `bus_exclusion_registry.py`. Provides the set of bus numbers to filter out.
- **`data/fnm/intermediate/schemas/*.schema.json`** -- The 17 table schemas plus
  `manifest.schema.json` defining column names, types, required fields, and valid
  ranges. Already committed to the repo.
- **`data/fnm/scripts/intermediate_schema.py`** -- Contains `TableSchema`,
  `FieldSpec`, and `PSSE_V31_RECORD_TYPES` definitions. May be used for
  record-type enumeration and field-type lookups.
- **`data/fnm/reference/cleaned/summary_cleaning.json`** -- Documents the cleaning
  steps and expected network statistics (27,862 buses, baseMVA=100.0). Used for
  cross-validation in tests.

### External Dependencies

- **`scipy`** (>=1.11) -- `scipy.io.loadmat` for reading MATPOWER `.mat` files.
  Already available in the devcontainer Python environment.
- **`jsonschema`** (>=4.0) -- For validating CSV rows and manifest against JSON
  Schema Draft 2020-12. Must be added to the devcontainer if not already present.

## Open Questions

1. **MATPOWER branch-to-transformer classification heuristic** -- The plan specifies
   using tap!=0 OR shift!=0 as the transformer indicator. Should the script also
   check the MATPOWER `TAP` column default behavior where tap=1.0 with shift=0 is
   still a branch (not a transformer)? The MATPOWER manual states that tap=0 means
   "transmission line" and tap!=0 means "transformer" -- confirm this is the sole
   classification criterion.

2. **Record types with partial MATPOWER support** -- Switched shunts and fixed shunts
   are "lossy" in MATPOWER's conversion (per `matpower_parser.py`). Should the
   exported CSVs for these types contain the MATPOWER-approximated data (what the
   `.mat` file contains) or should they be exported as empty tables with a note in the
   manifest? The current assumption is to export whatever data the `.mat` file
   contains.

3. **Base frequency derivation** -- The MATPOWER `.mat` file does not store base
   frequency. The manifest schema requires `basfrq`. Should this be hardcoded to
   60.0 Hz (ERCOT) or read from a configuration parameter?
