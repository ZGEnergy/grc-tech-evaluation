# PRD: dcpf_reference.py Separate-Table Support

## Overview

This deliverable updates the existing `dcpf_reference.py` script to support loading
branch and transformer data from separate CSV files, matching the intermediate format
produced by PRD-01's export pipeline. It also adds a `--manifest` argument that reads
`baseMVA` (and other system metadata) from the sidecar `manifest.json` instead of
requiring it as a CLI flag.

Today, `dcpf_reference.py` accepts a single `--branch-csv` argument containing both
transmission lines and transformers in a merged MATPOWER-style table. The v8
intermediate format splits these into separate `branch.csv` and `transformer.csv`
files with different column schemas (PSS/E Branch vs. PSS/E Transformer record
types). The transformer CSV uses PSS/E field names (`I`, `J`, `X1_2`, `WINDV1`,
`ANG1`, `STAT`, `CKT`) rather than MATPOWER-style names (`F_BUS`, `T_BUS`, `BR_X`,
`TAP`, `SHIFT`, `BR_STATUS`, `CKT`).

The update introduces a new optional `--transformer-csv` argument. When provided, the
script loads lines from `--branch-csv` and transformers from `--transformer-csv`
separately, maps their distinct column schemas to the internal `BranchRecord`
dataclass, and concatenates them before B-matrix construction. When omitted, the
existing merged-branch loading path is preserved unchanged, ensuring full backward
compatibility with the current MATPOWER-style merged CSVs.

A new `--manifest` argument enables reading `baseMVA` from the manifest's `sbase`
field. When `--manifest` is provided, `--base-mva` becomes optional (defaulting to the
manifest value). When both `--manifest` and `--base-mva` are provided, `--base-mva`
takes precedence as an explicit override. When neither is provided, `--base-mva`
defaults to `100.0` as it does today.

## Goals

1. **Add `--transformer-csv` optional CLI argument** that accepts a path to the
   separate transformer CSV file. When provided, `dcpf_reference.py` loads
   transmission lines from `--branch-csv` (which now contains only lines, no
   transformers) and transformers from `--transformer-csv`, then merges them into a
   unified `list[BranchRecord]` for downstream processing.

2. **Add a `load_transformer_table` function** that reads the PSS/E-format transformer
   CSV and maps its columns to the internal `BranchRecord` dataclass. The column
   mapping must handle the PSS/E transformer schema fields:
   - `I` -> `from_bus`
   - `J` -> `to_bus`
   - `CKT` -> `circuit_id`
   - `X1_2` -> `x_pu` (winding 1-2 reactance)
   - `WINDV1` -> `tap_ratio` (winding 1 turns ratio)
   - `ANG1` -> `shift_deg` (winding 1 phase shift angle)
   - `STAT` -> `status`
   - `is_transformer` is always set to `True`

3. **Add `--manifest` optional CLI argument** that accepts a path to `manifest.json`.
   When provided, reads the `sbase` field and uses it as `base_mva`. The manifest is
   also used to populate the `canonical_parser` metadata field if `--canonical-parser`
   is not explicitly provided.

4. **Implement baseMVA resolution precedence**: `--base-mva` (explicit CLI) >
   `manifest.sbase` (from `--manifest`) > `100.0` (hardcoded default). Log the
   resolved value and its source at INFO level.

5. **Preserve full backward compatibility** of the existing merged-branch path. When
   `--transformer-csv` is omitted, the existing `load_branch_table` function is called
   exactly as before with no behavioral changes. The `--branch-csv` argument remains
   required in all modes.

6. **Update `run_dcpf_reference` function signature** to accept an optional
   `transformer_csv_path: Path | None = None` parameter. When provided, it calls the
   new `load_transformer_table` function and concatenates the result with the branch
   records before passing them to `build_b_matrix`.

7. **Add a `_TRANSFORMER_COLUMN_MAP`** constant for the PSS/E transformer column
   name auto-detection, following the same pattern as the existing `_BUS_COLUMN_MAP`,
   `_GEN_COLUMN_MAP`, and `_BRANCH_COLUMN_MAP` dictionaries. This enables the same
   flexible column-name resolution used elsewhere in the script.

## Non-Goals

- **Creating the separate CSV files** -- handled by PRD-01 (Export Pipeline Script)
  and PRD-02 (Intermediate CSV Materialization).
- **Validating that the separate-table path reproduces the original DCPF reference** --
  handled by PRD-04 (DCPF Reference Reproducibility Validation).
- **Modifying the B-matrix construction or DCPF solver logic** -- the change is
  purely in data loading and CLI argument handling. Once branches and transformers
  are unified into `list[BranchRecord]`, all downstream computation is unchanged.
- **Supporting 3-winding transformers natively** -- the MATPOWER `.mat` format already
  flattens 3-winding transformers into equivalent 2-winding pairs. The `K` (winding 3
  bus) column in the transformer CSV is ignored; only `I`, `J`, and winding 1-2 fields
  are consumed.
- **Removing the legacy merged-branch path** -- backward compatibility is mandatory.
  The merged path will remain the default behavior when `--transformer-csv` is absent.
- **Changing output format or file structure** -- output CSVs and JSON remain identical
  regardless of which input path is used.

## Data Structures

The existing `BranchRecord` dataclass is unchanged. The new `load_transformer_table`
function produces `BranchRecord` instances by mapping transformer CSV columns to the
existing fields.

```python
# Existing -- no changes
@dataclass(frozen=True)
class BranchRecord:
    from_bus: int
    to_bus: int
    circuit_id: str
    x_pu: float
    tap_ratio: float
    shift_deg: float
    status: int
    is_transformer: bool
```

New column mapping constant:

```python
_TRANSFORMER_COLUMN_MAP: dict[str, list[str]] = {
    "I": ["i", "from_bus", "f_bus", "fbus"],
    "J": ["j", "to_bus", "t_bus", "tbus"],
    "X1_2": ["x1_2", "x12", "br_x", "x"],
    "WINDV1": ["windv1", "tap", "wind1"],
    "ANG1": ["ang1", "shift", "angle1"],
    "STAT": ["stat", "status", "st", "br_status"],
    "CKT": ["ckt", "circuit"],
}
```

New manifest loading helper return type (lightweight, not a dataclass -- just a dict):

```python
def load_manifest(manifest_path: Path) -> dict:
    """Load manifest.json and return the parsed dict.

    The caller extracts specific fields (sbase, canonical_parser) as needed.
    """
    ...
```

## API

```python
# --- New column mapping constant ---

_TRANSFORMER_COLUMN_MAP: dict[str, list[str]] = {
    "I": ["i", "from_bus", "f_bus", "fbus"],
    "J": ["j", "to_bus", "t_bus", "tbus"],
    "X1_2": ["x1_2", "x12", "br_x", "x"],
    "WINDV1": ["windv1", "tap", "wind1"],
    "ANG1": ["ang1", "shift", "angle1"],
    "STAT": ["stat", "status", "st", "br_status"],
    "CKT": ["ckt", "circuit"],
}
"""Column name mapping for PSS/E transformer CSV files. Maps canonical
field names to known variants for auto-detection via _resolve_columns."""


# --- New functions ---

def load_transformer_table(transformer_csv_path: Path) -> list[BranchRecord]:
    """Load the transformer table from a separate PSS/E-format transformer CSV.

    Reads the transformer CSV and maps PSS/E transformer field names to
    BranchRecord attributes:
      - I -> from_bus
      - J -> to_bus
      - CKT -> circuit_id
      - X1_2 -> x_pu (winding 1-2 reactance, p.u. on system MVA base)
      - WINDV1 -> tap_ratio (winding 1 turns ratio; 0.0 normalized to 1.0)
      - ANG1 -> shift_deg (winding 1 phase shift angle in degrees)
      - STAT -> status (1=in-service, 0=out-of-service; values 2-4 treated as 1)
      - is_transformer is always True

    A WINDV1 value of 0.0 is normalized to 1.0, matching the existing tap=0
    convention handling in load_branch_table.

    A STAT value in the range 1-4 is treated as in-service (mapped to 1)
    per PSS/E transformer status conventions where STAT=1 means all
    windings in service and STAT=2-4 means partial winding service.

    Args:
        transformer_csv_path: Path to the transformer CSV file.

    Returns:
        List of BranchRecord instances for all transformers, with
        is_transformer=True.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If required columns (I, J, X1_2, STAT) cannot be found.
    """
    ...


def load_manifest(manifest_path: Path) -> dict:
    """Load a manifest.json file and return the parsed dictionary.

    Reads the JSON file and returns its contents. The caller is responsible
    for extracting specific fields (e.g., sbase for baseMVA, canonical_parser).

    Args:
        manifest_path: Path to manifest.json.

    Returns:
        The parsed manifest as a Python dict.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        ValueError: If the file is not valid JSON.
    """
    ...


def resolve_base_mva(
    cli_base_mva: float | None,
    manifest: dict | None,
    default: float = 100.0,
) -> tuple[float, str]:
    """Resolve the system MVA base from CLI, manifest, or default.

    Precedence: cli_base_mva > manifest["sbase"] > default.

    Args:
        cli_base_mva: Value from --base-mva if explicitly provided, else None.
        manifest: Parsed manifest dict if --manifest was provided, else None.
        default: Fallback value (100.0).

    Returns:
        Tuple of (resolved_base_mva, source_description) where
        source_description is one of "cli --base-mva", "manifest sbase",
        or "default".
    """
    ...


# --- Modified function signature ---

def run_dcpf_reference(
    bus_csv_path: Path,
    gen_csv_path: Path,
    branch_csv_path: Path,
    exclusion_csv_path: Path,
    output_dir: Path,
    *,
    base_mva: float = 100.0,
    canonical_parser: str = "",
    transformer_csv_path: Path | None = None,    # NEW
) -> DCPFSolution:
    """Orchestrate the full DCPF reference computation pipeline.

    When transformer_csv_path is None (default), loads all branches
    (including transformers) from branch_csv_path using the existing
    load_branch_table function -- identical to current behavior.

    When transformer_csv_path is provided, loads transmission lines from
    branch_csv_path via load_branch_table and transformers from
    transformer_csv_path via load_transformer_table, then concatenates
    the two lists before passing to build_b_matrix.

    All other steps (bus loading, generator loading, exclusion filtering,
    B-matrix construction, solving, validation, output writing) are
    unchanged.

    Args:
        bus_csv_path: Path to the canonical parser's bus CSV.
        gen_csv_path: Path to the canonical parser's generator CSV.
        branch_csv_path: Path to the branch CSV (lines only when
            transformer_csv_path is provided; merged when not).
        exclusion_csv_path: Path to the D1 bus exclusion registry CSV.
        output_dir: Directory for output files.
        base_mva: System MVA base (default 100.0).
        canonical_parser: Name of the canonical parser (for metadata).
        transformer_csv_path: Optional path to the separate transformer CSV.
            When provided, branch_csv_path is expected to contain only
            transmission lines.

    Returns:
        The computed DCPFSolution.
    """
    ...


# --- Modified CLI entry point ---

def main(argv: list[str] | None = None) -> None:
    """CLI entry point for DCPF reference computation.

    Usage (legacy merged path)::

        python -m data.fnm.scripts.dcpf_reference \\
            --bus-csv path/to/bus.csv \\
            --gen-csv path/to/gen.csv \\
            --branch-csv path/to/merged_branch.csv \\
            --exclusion-csv path/to/excluded_buses.csv \\
            [--base-mva 100.0]

    Usage (separate-table path)::

        python -m data.fnm.scripts.dcpf_reference \\
            --bus-csv path/to/bus.csv \\
            --gen-csv path/to/gen.csv \\
            --branch-csv path/to/branch.csv \\
            --transformer-csv path/to/transformer.csv \\
            --exclusion-csv path/to/excluded_buses.csv \\
            --manifest path/to/manifest.json

    Usage (manifest with CLI override)::

        python -m data.fnm.scripts.dcpf_reference \\
            --bus-csv path/to/bus.csv \\
            --gen-csv path/to/gen.csv \\
            --branch-csv path/to/branch.csv \\
            --transformer-csv path/to/transformer.csv \\
            --exclusion-csv path/to/excluded_buses.csv \\
            --manifest path/to/manifest.json \\
            --base-mva 200.0

    New arguments:
      --transformer-csv  Optional path to separate transformer CSV.
      --manifest         Optional path to manifest.json (provides baseMVA).

    Args:
        argv: Command-line arguments.
    """
    ...
```

## Success Criteria

### Unit Tests

1. **`test_load_transformer_table_reads_psse_columns`** -- Create a synthetic
   transformer CSV with PSS/E column names (`I`, `J`, `K`, `CKT`, `X1_2`, `WINDV1`,
   `ANG1`, `STAT`) containing 3 rows. Verify `load_transformer_table` returns 3
   `BranchRecord` instances with correct field mappings and `is_transformer=True` on
   all records.

2. **`test_load_transformer_table_normalizes_windv1_zero`** -- Create a transformer
   CSV with one row having `WINDV1=0.0`. Verify the resulting `BranchRecord` has
   `tap_ratio=1.0` (0-to-1.0 normalization applied).

3. **`test_load_transformer_table_stat_mapping`** -- Create a transformer CSV with
   rows having `STAT` values of 0, 1, 2, 3, 4. Verify `status=0` for `STAT=0` and
   `status=1` for `STAT` values 1 through 4 (all in-service variants).

4. **`test_load_transformer_table_missing_required_column`** -- Create a transformer
   CSV missing the `X1_2` column. Verify `ValueError` is raised with a message
   mentioning the missing column.

5. **`test_load_transformer_table_file_not_found`** -- Call `load_transformer_table`
   with a nonexistent path. Verify `FileNotFoundError` is raised.

6. **`test_transformer_column_map_autodetects_variants`** -- Create transformer CSVs
   using variant column names (`from_bus` instead of `I`, `tap` instead of `WINDV1`,
   `shift` instead of `ANG1`). Verify all variants are correctly resolved.

7. **`test_load_manifest_reads_sbase`** -- Create a minimal `manifest.json` with
   `"sbase": 100.0`. Verify `load_manifest` returns a dict with `sbase == 100.0`.

8. **`test_load_manifest_file_not_found`** -- Call `load_manifest` with a nonexistent
   path. Verify `FileNotFoundError` is raised.

9. **`test_load_manifest_invalid_json`** -- Create a file with invalid JSON content.
   Verify `ValueError` is raised.

10. **`test_resolve_base_mva_cli_overrides_manifest`** -- Call `resolve_base_mva` with
    `cli_base_mva=200.0` and a manifest containing `sbase=100.0`. Verify the resolved
    value is `200.0` and source is `"cli --base-mva"`.

11. **`test_resolve_base_mva_manifest_overrides_default`** -- Call `resolve_base_mva`
    with `cli_base_mva=None` and a manifest containing `sbase=150.0`. Verify the
    resolved value is `150.0` and source is `"manifest sbase"`.

12. **`test_resolve_base_mva_falls_back_to_default`** -- Call `resolve_base_mva` with
    `cli_base_mva=None` and `manifest=None`. Verify the resolved value is `100.0` and
    source is `"default"`.

13. **`test_run_dcpf_separate_tables_produces_same_solution`** -- Given a synthetic
    network with 5 buses, 3 lines, and 2 transformers:
    (a) Run `run_dcpf_reference` with a merged branch CSV containing all 5 elements.
    (b) Run `run_dcpf_reference` with a lines-only branch CSV and a separate
    transformer CSV.
    Verify both produce identical `DCPFSolution` results (bus angles, branch flows,
    slack injection all match within `FLOW_TOLERANCE_MW`).

14. **`test_run_dcpf_legacy_path_unchanged`** -- Run `run_dcpf_reference` with
    `transformer_csv_path=None` using the same merged CSV as before this change.
    Verify the output matches the previously computed reference solution exactly
    (byte-for-byte on output CSVs or within float tolerance on numeric fields).

15. **`test_main_cli_accepts_transformer_csv_flag`** -- Call `main()` with
    `--transformer-csv` pointing to a valid file. Verify no `argparse` error is raised
    and the transformer CSV path is passed through to `run_dcpf_reference`.

16. **`test_main_cli_accepts_manifest_flag`** -- Call `main()` with `--manifest`
    pointing to a valid manifest.json. Verify `base_mva` is resolved from the manifest
    and passed to `run_dcpf_reference`.

17. **`test_main_cli_base_mva_overrides_manifest`** -- Call `main()` with both
    `--manifest` (containing `sbase=100.0`) and `--base-mva 200.0`. Verify
    `run_dcpf_reference` receives `base_mva=200.0`.

18. **`test_main_cli_backward_compat_no_new_flags`** -- Call `main()` with only the
    original arguments (`--bus-csv`, `--gen-csv`, `--branch-csv`, `--exclusion-csv`,
    `--base-mva`). Verify the script runs identically to its pre-change behavior with
    no errors or warnings about missing `--transformer-csv` or `--manifest`.

## File Location

The changes are made to the existing file:

```
data/fnm/scripts/dcpf_reference.py
```

No new files are created. Tests will be placed alongside existing test infrastructure
(location determined by the implementer, following the repo's test conventions).

## Repository

`grc-tech-evaluation`

## Dependencies

### Internal Dependencies

- **`data/fnm/scripts/dcpf_reference.py`** (existing) -- The file being modified.
  Must be read and understood before implementation.
- **PRD-01 (Export Pipeline Script)** -- Produces the separate `branch.csv` and
  `transformer.csv` files and the `manifest.json` sidecar that this update consumes.
  The column schemas are defined by `data/fnm/intermediate/schemas/branch.schema.json`
  and `data/fnm/intermediate/schemas/transformer.schema.json`.
- **`data/fnm/intermediate/schemas/transformer.schema.json`** -- Defines the column
  names and types for the transformer CSV. The `_TRANSFORMER_COLUMN_MAP` must include
  the canonical names from this schema (`I`, `J`, `K`, `CKT`, `X1_2`, `WINDV1`,
  `ANG1`, `STAT`).
- **`data/fnm/intermediate/schemas/manifest.schema.json`** -- Defines the manifest
  structure including the `sbase` field used for baseMVA resolution.

### External Dependencies

None. The script uses only Python stdlib (`argparse`, `csv`, `json`, `math`, `logging`,
`pathlib`, `dataclasses`, `sys`). No new external dependencies are introduced.

## Open Questions

None -- all design decisions have been resolved in the parent phase plan.
