# PRD: DCPF Reference Reproducibility Validation

## Overview

This deliverable is the capstone validation for Phase 0, proving that the format change
from MATPOWER `.mat` to intermediate CSVs is lossless for DCPF computation. It creates a
validation script that runs `dcpf_reference.py` using the intermediate CSV artifacts
(produced by PRD-01/02) via the separate-table CLI path (implemented by PRD-03), then
compares the resulting DCPF solution against the existing committed reference in
`data/fnm/reference/dcpf/`.

The existing DCPF reference consists of three files:
- `buses_dcpf.csv` -- per-bus voltage angles and metadata (27,862 buses)
- `branches_dcpf.csv` -- per-branch MW flows (32,532 branches)
- `summary_dcpf.json` -- aggregate statistics (generation, load, slack bus, counts)

The validation confirms numerical equivalence within defined tolerances: bus voltage
angles must match within 0.001 degrees and branch power flows must match within 0.1 MW.
These tolerances match the constants `ANGLE_TOLERANCE_DEG` and `FLOW_TOLERANCE_MW`
already defined in `dcpf_reference.py`. A comparison report is written to disk
summarizing the results and any discrepancies.

If the validation passes, it certifies that all downstream protocol v8 tests can safely
consume intermediate CSVs instead of parsing `.mat` files, with no loss of DCPF fidelity.

## Goals

1. **Create `validate_dcpf_reproducibility.py`** -- a standalone script in
   `data/fnm/scripts/` that orchestrates the full round-trip validation: load
   intermediate CSVs, run DCPF via the separate-table path, compare against the
   committed reference, and produce a structured comparison report.

2. **Run `dcpf_reference.py` via the separate-table path** using intermediate CSV
   artifacts:
   - `--bus-csv data/fnm/reference/cleaned/intermediate/bus.csv`
   - `--gen-csv data/fnm/reference/cleaned/intermediate/generator.csv`
   - `--branch-csv data/fnm/reference/cleaned/intermediate/branch.csv`
   - `--transformer-csv data/fnm/reference/cleaned/intermediate/transformer.csv`
   - `--exclusion-csv data/fnm/reference/excluded_buses.json`
   - `--manifest data/fnm/reference/cleaned/intermediate/manifest.json`
   - `-o` pointing to a temporary output directory (not overwriting the reference)

3. **Load the existing committed reference** from `data/fnm/reference/dcpf/` --
   `buses_dcpf.csv`, `branches_dcpf.csv`, and `summary_dcpf.json` -- and parse them
   into comparable data structures.

4. **Compare bus-level results** by matching on `bus_number` and computing the absolute
   difference in `va_deg` (voltage angle in degrees). Flag any bus where the difference
   exceeds `ANGLE_TOLERANCE_DEG` (0.001 degrees). Report max, mean, and count of
   exceedances.

5. **Compare branch-level results** by matching on `(from_bus, to_bus)` and computing
   the absolute difference in `pf_mw` (branch flow in MW). Flag any branch where the
   difference exceeds `FLOW_TOLERANCE_MW` (0.1 MW). Report max, mean, and count of
   exceedances.

6. **Compare summary-level statistics** by checking that scalar fields in
   `summary_dcpf.json` match: `n_buses`, `n_branches`, `n_gens`, `slack_bus`,
   `total_gen_mw` (within 0.1 MW), `total_load_mw` (within 0.1 MW), and `success`.

7. **Produce a comparison report** written to
   `data/fnm/reference/dcpf/reproducibility_report.json` containing:
   - Overall pass/fail status
   - Bus angle comparison: max absolute difference, mean absolute difference, count of
     exceedances, total buses compared
   - Branch flow comparison: max absolute difference, mean absolute difference, count of
     exceedances, total branches compared
   - Summary field comparison: per-field expected vs. actual values with pass/fail
   - Tolerances used
   - Timestamp of validation run
   - Paths to the reference and reproduced artifacts

8. **Exit with code 0 on success, 1 on mismatch** -- exit code 0 means all comparisons
   are within tolerance; exit code 1 means at least one comparison exceeded tolerance,
   with diagnostic output to stderr identifying the failing checks.

9. **Log detailed diagnostics** at INFO level showing progress (loading reference,
   running DCPF, comparing buses, comparing branches) and at WARNING level for any
   near-tolerance values (within 10x of the tolerance threshold).

## Non-Goals

- **Creating the intermediate CSV artifacts** -- handled by PRD-01 (Export Pipeline
  Script) and PRD-02 (Intermediate CSV Materialization).
- **Modifying `dcpf_reference.py`** -- handled by PRD-03 (Separate-Table Support). This
  PRD only invokes it.
- **Overwriting the committed reference files** -- the reproduced DCPF output is written
  to a temporary directory. The existing reference in `data/fnm/reference/dcpf/` is
  read-only for comparison purposes.
- **Comparing non-DCPF reference files** (e.g., ACPF references) -- this validation is
  scoped exclusively to the DCPF solution.
- **Performance benchmarking** -- the script reports wall-clock time for informational
  purposes but does not assert performance constraints.
- **Modifying tolerances** -- the tolerances are fixed at 0.001 degrees and 0.1 MW,
  matching the constants already in `dcpf_reference.py`.

## Data Structures

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BusComparison:
    """Result of comparing bus-level DCPF results."""

    total_buses: int
    """Number of buses compared."""

    max_angle_diff_deg: float
    """Maximum absolute difference in voltage angle (degrees)."""

    mean_angle_diff_deg: float
    """Mean absolute difference in voltage angle (degrees)."""

    exceedance_count: int
    """Number of buses exceeding ANGLE_TOLERANCE_DEG."""

    tolerance_deg: float
    """Tolerance used for comparison (0.001 degrees)."""

    passed: bool
    """True if exceedance_count == 0."""

    missing_in_reproduced: list[int]
    """Bus numbers present in reference but absent from reproduced output."""

    missing_in_reference: list[int]
    """Bus numbers present in reproduced output but absent from reference."""


@dataclass(frozen=True)
class BranchComparison:
    """Result of comparing branch-level DCPF results."""

    total_branches: int
    """Number of branches compared."""

    max_flow_diff_mw: float
    """Maximum absolute difference in branch flow (MW)."""

    mean_flow_diff_mw: float
    """Mean absolute difference in branch flow (MW)."""

    exceedance_count: int
    """Number of branches exceeding FLOW_TOLERANCE_MW."""

    tolerance_mw: float
    """Tolerance used for comparison (0.1 MW)."""

    passed: bool
    """True if exceedance_count == 0."""

    missing_in_reproduced: list[tuple[int, int]]
    """(from_bus, to_bus) pairs in reference but absent from reproduced output."""

    missing_in_reference: list[tuple[int, int]]
    """(from_bus, to_bus) pairs in reproduced output but absent from reference."""


@dataclass(frozen=True)
class SummaryFieldCheck:
    """Result of comparing one summary-level field."""

    field_name: str
    """Name of the field (e.g., 'n_buses', 'total_gen_mw')."""

    expected: int | float | bool
    """Value from the committed reference."""

    actual: int | float | bool
    """Value from the reproduced run."""

    tolerance: float | None
    """Tolerance for numeric comparison, None for exact-match fields."""

    passed: bool
    """True if values match within tolerance (or exactly for non-numeric)."""


@dataclass(frozen=True)
class SummaryComparison:
    """Result of comparing summary-level DCPF statistics."""

    field_checks: list[SummaryFieldCheck]
    """Per-field comparison results."""

    passed: bool
    """True if all field checks passed."""


@dataclass(frozen=True)
class ReproducibilityReport:
    """Full comparison report for DCPF reproducibility validation."""

    passed: bool
    """True if all comparisons (bus, branch, summary) passed."""

    bus_comparison: BusComparison
    """Bus-level angle comparison results."""

    branch_comparison: BranchComparison
    """Branch-level flow comparison results."""

    summary_comparison: SummaryComparison
    """Summary-level statistic comparison results."""

    reference_dir: str
    """Path to the committed reference directory."""

    reproduced_dir: str
    """Path to the temporary reproduced output directory."""

    tolerances: dict[str, float]
    """Tolerances used: angle_deg, flow_mw."""

    timestamp: str
    """ISO 8601 timestamp of validation run."""

    wall_clock_seconds: float
    """Total elapsed time for the validation run."""
```

## API

```python
def load_reference_buses(buses_csv_path: Path) -> dict[int, float]:
    """Load the committed reference bus angles from buses_dcpf.csv.

    Reads the CSV and returns a mapping from bus_number to va_deg
    (voltage angle in degrees).

    Args:
        buses_csv_path: Path to buses_dcpf.csv.

    Returns:
        Dict mapping bus_number (int) to voltage angle (float, degrees).

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If the CSV is missing required columns.
    """
    ...


def load_reference_branches(branches_csv_path: Path) -> dict[tuple[int, int], float]:
    """Load the committed reference branch flows from branches_dcpf.csv.

    Reads the CSV and returns a mapping from (from_bus, to_bus) to pf_mw
    (power flow in MW).

    Note: if parallel branches exist (same from_bus/to_bus, different
    circuits), they are stored as separate entries. The comparison key
    includes the row index to handle duplicates.

    Args:
        branches_csv_path: Path to branches_dcpf.csv.

    Returns:
        Dict mapping (from_bus, to_bus) to flow (float, MW). For parallel
        branches, a list-based structure is used internally.

    Raises:
        FileNotFoundError: If the CSV does not exist.
        ValueError: If the CSV is missing required columns.
    """
    ...


def load_reference_summary(summary_json_path: Path) -> dict:
    """Load the committed reference summary from summary_dcpf.json.

    Args:
        summary_json_path: Path to summary_dcpf.json.

    Returns:
        The parsed JSON as a Python dict.

    Raises:
        FileNotFoundError: If the JSON does not exist.
        ValueError: If the file is not valid JSON.
    """
    ...


def compare_bus_angles(
    reference: dict[int, float],
    reproduced: dict[int, float],
    tolerance_deg: float = 0.001,
) -> BusComparison:
    """Compare bus voltage angles between reference and reproduced solutions.

    Matches buses by bus_number. Computes absolute difference in va_deg
    for each matched bus. Reports exceedances, max/mean differences,
    and any buses present in one set but not the other.

    Args:
        reference: Bus angles from the committed reference.
        reproduced: Bus angles from the reproduced DCPF run.
        tolerance_deg: Maximum allowable absolute angle difference.

    Returns:
        A BusComparison with detailed results.
    """
    ...


def compare_branch_flows(
    reference_csv_path: Path,
    reproduced_csv_path: Path,
    tolerance_mw: float = 0.1,
) -> BranchComparison:
    """Compare branch power flows between reference and reproduced solutions.

    Loads both CSVs and matches branches by row order (both are produced
    by the same dcpf_reference.py code, so branch ordering is deterministic
    given the same input data). Computes absolute difference in pf_mw for
    each matched branch. Reports exceedances, max/mean differences, and
    any count mismatches.

    Args:
        reference_csv_path: Path to the committed branches_dcpf.csv.
        reproduced_csv_path: Path to the reproduced branches_dcpf.csv.
        tolerance_mw: Maximum allowable absolute flow difference.

    Returns:
        A BranchComparison with detailed results.
    """
    ...


def compare_summaries(
    reference: dict,
    reproduced: dict,
    flow_tolerance_mw: float = 0.1,
) -> SummaryComparison:
    """Compare summary-level DCPF statistics.

    Checks the following fields:
      - n_buses: exact match (int)
      - n_branches: exact match (int)
      - n_gens: exact match (int)
      - slack_bus: exact match (int)
      - success: exact match (bool/int)
      - total_gen_mw: within flow_tolerance_mw (float)
      - total_load_mw: within flow_tolerance_mw (float)

    Args:
        reference: Summary dict from the committed reference.
        reproduced: Summary dict from the reproduced run.
        flow_tolerance_mw: Tolerance for generation/load MW comparison.

    Returns:
        A SummaryComparison with per-field results.
    """
    ...


def write_report(report: ReproducibilityReport, output_path: Path) -> None:
    """Serialize a ReproducibilityReport to JSON and write to disk.

    Args:
        report: The comparison report to write.
        output_path: Destination path for reproducibility_report.json.
    """
    ...


def run_dcpf_via_csv_path(
    intermediate_dir: Path,
    exclusion_path: Path,
    output_dir: Path,
) -> Path:
    """Run dcpf_reference.py using the separate-table CSV path.

    Invokes dcpf_reference.run_dcpf_reference() programmatically with:
      - bus_csv_path = intermediate_dir / "bus.csv"
      - gen_csv_path = intermediate_dir / "generator.csv"
      - branch_csv_path = intermediate_dir / "branch.csv"
      - transformer_csv_path = intermediate_dir / "transformer.csv"
      - exclusion_csv_path = exclusion_path
      - manifest loaded from intermediate_dir / "manifest.json" for baseMVA
      - output_dir = output_dir

    Args:
        intermediate_dir: Path to data/fnm/reference/cleaned/intermediate/.
        exclusion_path: Path to data/fnm/reference/excluded_buses.json.
        output_dir: Temporary output directory for reproduced DCPF files.

    Returns:
        Path to the output directory containing reproduced DCPF files.

    Raises:
        FileNotFoundError: If any required input file is missing.
        RuntimeError: If the DCPF computation fails.
    """
    ...


def run_validation(
    reference_dir: Path,
    intermediate_dir: Path,
    exclusion_path: Path,
    report_output_path: Path,
) -> ReproducibilityReport:
    """Orchestrate the full reproducibility validation.

    Steps:
      1. Create a temporary output directory for the reproduced DCPF.
      2. Run dcpf_reference.py via the separate-table CSV path.
      3. Load the committed reference files.
      4. Load the reproduced output files.
      5. Compare bus angles.
      6. Compare branch flows.
      7. Compare summary statistics.
      8. Assemble and write the comparison report.
      9. Clean up the temporary directory (or preserve on failure for debugging).

    Args:
        reference_dir: Path to data/fnm/reference/dcpf/.
        intermediate_dir: Path to data/fnm/reference/cleaned/intermediate/.
        exclusion_path: Path to data/fnm/reference/excluded_buses.json.
        report_output_path: Path to write reproducibility_report.json.

    Returns:
        The ReproducibilityReport.
    """
    ...


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for DCPF reproducibility validation.

    Usage::

        python data/fnm/scripts/validate_dcpf_reproducibility.py

    All paths are derived from repository-relative defaults:
      - Reference: data/fnm/reference/dcpf/
      - Intermediate CSVs: data/fnm/reference/cleaned/intermediate/
      - Exclusion registry: data/fnm/reference/excluded_buses.json
      - Report output: data/fnm/reference/dcpf/reproducibility_report.json

    Optional overrides:
      --reference-dir     Path to committed DCPF reference directory.
      --intermediate-dir  Path to intermediate CSV directory.
      --exclusion-csv     Path to excluded_buses.json.
      --report-output     Path to write the comparison report.

    Exit codes:
      - 0: All comparisons within tolerance.
      - 1: One or more comparisons exceeded tolerance.
      - 2: Input error (missing files, DCPF computation failure).

    Args:
        argv: Command-line arguments. If None, reads from sys.argv.
    """
    ...
```

## Success Criteria

### Unit Tests

1. **`test_load_reference_buses_returns_correct_count`** -- Load the committed
   `buses_dcpf.csv` and verify the returned dict contains 27,862 entries (matching
   `summary_dcpf.json` `n_buses`).

2. **`test_load_reference_buses_parses_angle`** -- Load `buses_dcpf.csv` and verify
   that bus 29421 (the slack bus) has `va_deg == 0.0`.

3. **`test_load_reference_branches_returns_correct_count`** -- Load the committed
   `branches_dcpf.csv` and verify the returned structure contains 32,532 entries
   (matching `summary_dcpf.json` `n_branches`).

4. **`test_load_reference_summary_parses_fields`** -- Load `summary_dcpf.json` and
   verify `n_buses == 27862`, `slack_bus == 29421`, `success == 1`.

5. **`test_compare_bus_angles_identical_passes`** -- Construct two identical bus angle
   dicts (5 buses). Verify `BusComparison.passed == True`, `max_angle_diff_deg == 0.0`,
   and `exceedance_count == 0`.

6. **`test_compare_bus_angles_within_tolerance_passes`** -- Construct two bus angle
   dicts differing by 0.0005 degrees (within 0.001 tolerance). Verify
   `BusComparison.passed == True`.

7. **`test_compare_bus_angles_exceeds_tolerance_fails`** -- Construct two bus angle
   dicts differing by 0.002 degrees (exceeds 0.001 tolerance). Verify
   `BusComparison.passed == False` and `exceedance_count == 1`.

8. **`test_compare_bus_angles_missing_bus_reported`** -- Reference has buses {1, 2, 3},
   reproduced has {1, 2}. Verify `missing_in_reproduced == [3]`.

9. **`test_compare_branch_flows_identical_passes`** -- Create two identical branch CSV
   files (3 branches). Verify `BranchComparison.passed == True` and
   `max_flow_diff_mw == 0.0`.

10. **`test_compare_branch_flows_exceeds_tolerance_fails`** -- Create two branch CSV
    files differing by 0.2 MW on one branch (exceeds 0.1 MW tolerance). Verify
    `BranchComparison.passed == False` and `exceedance_count == 1`.

11. **`test_compare_summaries_exact_match_passes`** -- Construct two identical summary
    dicts. Verify `SummaryComparison.passed == True` and all field checks pass.

12. **`test_compare_summaries_count_mismatch_fails`** -- Construct summaries where
    `n_buses` differs (27862 vs 27861). Verify `SummaryComparison.passed == False` and
    the `n_buses` field check has `passed == False`.

13. **`test_compare_summaries_gen_mw_within_tolerance_passes`** -- Construct summaries
    where `total_gen_mw` differs by 0.05 MW (within 0.1 MW tolerance). Verify the
    `total_gen_mw` field check passes.

14. **`test_write_report_produces_valid_json`** -- Construct a synthetic
    `ReproducibilityReport` and write it. Read back the JSON and verify all fields
    are present and correctly typed.

15. **`test_run_validation_end_to_end`** -- Run the full `run_validation` function
    using the committed reference directory and intermediate CSVs. Verify:
    - `ReproducibilityReport.passed == True`
    - `bus_comparison.exceedance_count == 0`
    - `branch_comparison.exceedance_count == 0`
    - `summary_comparison.passed == True`
    - The report JSON file exists at the specified output path.
    This is the definitive test proving the Phase 0 format change is lossless.

16. **`test_main_exit_code_zero_on_success`** -- Run `main()` with default paths
    (assuming intermediate CSVs are materialized). Verify exit code is 0.

17. **`test_main_exit_code_two_on_missing_input`** -- Run `main()` with
    `--intermediate-dir` pointing to a nonexistent directory. Verify exit code is 2.

18. **`test_report_contains_tolerances`** -- Run validation and verify the report JSON
    includes `tolerances.angle_deg == 0.001` and `tolerances.flow_mw == 0.1`.

## File Location

New file:

```
data/fnm/scripts/validate_dcpf_reproducibility.py
```

Output artifact:

```
data/fnm/reference/dcpf/reproducibility_report.json
```

Tests will be placed alongside existing test infrastructure (location determined by the
implementer, following the repo's test conventions).

## Repository

`grc-tech-evaluation`

## Dependencies

### Internal Dependencies

- **PRD-01 (Export Pipeline Script)** -- Produces the intermediate CSV files and
  `manifest.json` consumed by this validation. Must be implemented first.
- **PRD-02 (Intermediate CSV Materialization)** -- Commits the intermediate CSV
  artifacts to `data/fnm/reference/cleaned/intermediate/`. Must be completed before
  this validation can run against real data.
- **PRD-03 (dcpf_reference.py Separate-Table Support)** -- Adds the `--transformer-csv`
  and `--manifest` CLI arguments that this validation exercises. Must be implemented
  before this validation script can invoke the separate-table path.
- **`data/fnm/scripts/dcpf_reference.py`** (existing + PRD-03 modifications) -- The
  DCPF solver invoked by this validation. Specifically uses `run_dcpf_reference()` with
  the `transformer_csv_path` parameter and `load_manifest()` for baseMVA resolution.
- **`data/fnm/reference/dcpf/buses_dcpf.csv`** -- Committed reference bus angles
  (27,862 rows). The ground truth for bus-level comparison.
- **`data/fnm/reference/dcpf/branches_dcpf.csv`** -- Committed reference branch flows
  (32,532 rows). The ground truth for branch-level comparison.
- **`data/fnm/reference/dcpf/summary_dcpf.json`** -- Committed reference summary
  statistics. The ground truth for summary-level comparison.
- **`data/fnm/reference/excluded_buses.json`** -- Bus exclusion registry, passed to
  `dcpf_reference.py` for consistency with the original reference computation.
- **`data/fnm/reference/cleaned/intermediate/bus.csv`** -- Intermediate bus table.
- **`data/fnm/reference/cleaned/intermediate/generator.csv`** -- Intermediate generator table.
- **`data/fnm/reference/cleaned/intermediate/branch.csv`** -- Intermediate branch table
  (transmission lines only, no transformers).
- **`data/fnm/reference/cleaned/intermediate/transformer.csv`** -- Intermediate
  transformer table (PSS/E column names).
- **`data/fnm/reference/cleaned/intermediate/manifest.json`** -- Intermediate manifest
  providing `sbase` for baseMVA resolution.

### External Dependencies

None. The script uses only Python stdlib (`argparse`, `csv`, `json`, `logging`,
`pathlib`, `dataclasses`, `sys`, `tempfile`, `time`). It imports `dcpf_reference`
functions from the same `data/fnm/scripts/` directory.

## Open Questions

None -- all design decisions have been resolved in the parent phase plan.
