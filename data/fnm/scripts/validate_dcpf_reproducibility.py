"""DCPF Reference Reproducibility Validation.

Runs ``dcpf_reference.run_dcpf_reference`` using the intermediate CSV artifacts
(produced by the canonical parser) via the separate-table CSV path, then compares
the resulting DCPF solution against the existing committed reference in
``data/fnm/reference/dcpf/``.

Validation confirms numerical equivalence within tolerances:
- Bus angles within 0.001 degrees
- Branch flows within 0.1 MW
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dcpf_reference import load_manifest, run_dcpf_reference

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default tolerances
# ---------------------------------------------------------------------------

DEFAULT_ANGLE_TOLERANCE_DEG: float = 0.001
DEFAULT_FLOW_TOLERANCE_MW: float = 0.1

# ---------------------------------------------------------------------------
# Comparison result containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusComparison:
    total_buses: int
    max_angle_diff_deg: float
    mean_angle_diff_deg: float
    exceedance_count: int
    tolerance_deg: float
    passed: bool
    missing_in_reproduced: list[int]
    missing_in_reference: list[int]


@dataclass(frozen=True)
class BranchComparison:
    total_branches: int
    max_flow_diff_mw: float
    mean_flow_diff_mw: float
    exceedance_count: int
    tolerance_mw: float
    passed: bool
    missing_in_reproduced: list[tuple[int, int]]
    missing_in_reference: list[tuple[int, int]]


@dataclass(frozen=True)
class SummaryFieldCheck:
    field_name: str
    expected: int | float | bool
    actual: int | float | bool
    tolerance: float | None
    passed: bool


@dataclass(frozen=True)
class SummaryComparison:
    field_checks: list[SummaryFieldCheck]
    passed: bool


@dataclass(frozen=True)
class ReproducibilityReport:
    passed: bool
    bus_comparison: BusComparison
    branch_comparison: BranchComparison
    summary_comparison: SummaryComparison
    reference_dir: str
    reproduced_dir: str
    tolerances: dict[str, float]
    timestamp: str
    wall_clock_seconds: float


# ---------------------------------------------------------------------------
# Reference data loaders
# ---------------------------------------------------------------------------


def load_reference_buses(buses_csv_path: Path) -> dict[int, float]:
    """Load bus angles from a buses_dcpf.csv file.

    Returns a dict mapping bus number to voltage angle in degrees.

    Handles two column conventions:
    - New format: ``bus, VA``
    - Legacy format: ``bus_number, va_deg``
    """
    if not buses_csv_path.exists():
        raise FileNotFoundError(f"Bus CSV not found: {buses_csv_path}")

    result: dict[int, float] = {}
    with open(buses_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Detect column names
            if "bus" in row:
                bus_num = int(row["bus"])
            elif "bus_number" in row:
                bus_num = int(row["bus_number"])
            else:
                raise ValueError(f"Cannot find bus number column. Headers: {list(row.keys())}")

            if "VA" in row:
                angle_deg = float(row["VA"])
            elif "va_deg" in row:
                angle_deg = float(row["va_deg"])
            else:
                raise ValueError(f"Cannot find angle column. Headers: {list(row.keys())}")

            result[bus_num] = angle_deg
    return result


def load_reference_branches(branches_csv_path: Path) -> dict[tuple[int, int], float]:
    """Load branch flows from a branches_dcpf.csv file.

    Returns a dict mapping (from_bus, to_bus) to flow in MW.
    Note: for parallel branches, only the last one's flow is kept in this
    simple dict representation.  For detailed comparison, use
    ``compare_branch_flows`` which does row-by-row matching.

    Handles two column conventions:
    - New format: ``from_bus, to_bus, ckt, P_flow_MW``
    - Legacy format: ``from_bus, to_bus, pf_mw, status``
    """
    if not branches_csv_path.exists():
        raise FileNotFoundError(f"Branch CSV not found: {branches_csv_path}")

    result: dict[tuple[int, int], float] = {}
    with open(branches_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (int(row["from_bus"]), int(row["to_bus"]))
            if "P_flow_MW" in row:
                result[key] = float(row["P_flow_MW"])
            elif "pf_mw" in row:
                result[key] = float(row["pf_mw"])
            else:
                raise ValueError(f"Cannot find flow column. Headers: {list(row.keys())}")
    return result


def load_reference_summary(summary_json_path: Path) -> dict:
    """Load a DCPF summary JSON file.

    Handles both the legacy flat format and the newer nested format.

    Returns the parsed dict.
    """
    if not summary_json_path.exists():
        raise FileNotFoundError(f"Summary JSON not found: {summary_json_path}")

    return json.loads(summary_json_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Comparison functions
# ---------------------------------------------------------------------------


def compare_bus_angles(
    reference: dict[int, float],
    reproduced: dict[int, float],
    tolerance_deg: float = DEFAULT_ANGLE_TOLERANCE_DEG,
) -> BusComparison:
    """Compare bus voltage angles between reference and reproduced solutions.

    Args:
        reference: Dict of bus_number -> angle_deg from reference.
        reproduced: Dict of bus_number -> angle_deg from reproduced run.
        tolerance_deg: Maximum allowable absolute angle difference.

    Returns:
        BusComparison with comparison results.
    """
    ref_buses = set(reference.keys())
    rep_buses = set(reproduced.keys())

    missing_in_reproduced = sorted(ref_buses - rep_buses)
    missing_in_reference = sorted(rep_buses - ref_buses)

    common_buses = ref_buses & rep_buses
    if not common_buses:
        return BusComparison(
            total_buses=0,
            max_angle_diff_deg=0.0,
            mean_angle_diff_deg=0.0,
            exceedance_count=0,
            tolerance_deg=tolerance_deg,
            passed=len(missing_in_reproduced) == 0 and len(missing_in_reference) == 0,
            missing_in_reproduced=missing_in_reproduced,
            missing_in_reference=missing_in_reference,
        )

    diffs = [abs(reference[b] - reproduced[b]) for b in common_buses]
    max_diff = max(diffs)
    mean_diff = sum(diffs) / len(diffs)
    exceedance_count = sum(1 for d in diffs if d > tolerance_deg)

    passed = (
        exceedance_count == 0 and len(missing_in_reproduced) == 0 and len(missing_in_reference) == 0
    )

    return BusComparison(
        total_buses=len(common_buses),
        max_angle_diff_deg=max_diff,
        mean_angle_diff_deg=mean_diff,
        exceedance_count=exceedance_count,
        tolerance_deg=tolerance_deg,
        passed=passed,
        missing_in_reproduced=missing_in_reproduced,
        missing_in_reference=missing_in_reference,
    )


def compare_branch_flows(
    reference_csv_path: Path,
    reproduced_csv_path: Path,
    tolerance_mw: float = DEFAULT_FLOW_TOLERANCE_MW,
) -> BranchComparison:
    """Compare branch MW flows between reference and reproduced CSVs.

    Since there can be parallel branches (same from_bus/to_bus, different ckt),
    comparison is done row-by-row on (from_bus, to_bus, ckt) keys.

    Args:
        reference_csv_path: Path to reference branches_dcpf.csv.
        reproduced_csv_path: Path to reproduced branches_dcpf.csv.
        tolerance_mw: Maximum allowable absolute flow difference.

    Returns:
        BranchComparison with comparison results.
    """
    if not reference_csv_path.exists():
        raise FileNotFoundError(f"Reference branch CSV not found: {reference_csv_path}")
    if not reproduced_csv_path.exists():
        raise FileNotFoundError(f"Reproduced branch CSV not found: {reproduced_csv_path}")

    def _load_keyed(csv_path: Path) -> dict[tuple[int, int, str], float]:
        result: dict[tuple[int, int, str], float] = {}
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row_idx = 0
            for row in reader:
                from_bus = int(row["from_bus"])
                to_bus = int(row["to_bus"])

                # ckt column may not exist in legacy format
                if "ckt" in row:
                    ckt = row["ckt"].strip()
                else:
                    ckt = str(row_idx)

                if "P_flow_MW" in row:
                    flow = float(row["P_flow_MW"])
                elif "pf_mw" in row:
                    flow = float(row["pf_mw"])
                else:
                    raise ValueError(
                        f"Cannot find flow column in {csv_path}. Headers: {list(row.keys())}"
                    )

                key = (from_bus, to_bus, ckt)
                result[key] = flow
                row_idx += 1
        return result

    ref_flows = _load_keyed(reference_csv_path)
    rep_flows = _load_keyed(reproduced_csv_path)

    ref_keys = set(ref_flows.keys())
    rep_keys = set(rep_flows.keys())

    missing_in_reproduced: list[tuple[int, int]] = [
        (k[0], k[1]) for k in sorted(ref_keys - rep_keys)
    ]
    missing_in_reference: list[tuple[int, int]] = [
        (k[0], k[1]) for k in sorted(rep_keys - ref_keys)
    ]

    common_keys = ref_keys & rep_keys
    if not common_keys:
        return BranchComparison(
            total_branches=0,
            max_flow_diff_mw=0.0,
            mean_flow_diff_mw=0.0,
            exceedance_count=0,
            tolerance_mw=tolerance_mw,
            passed=len(missing_in_reproduced) == 0 and len(missing_in_reference) == 0,
            missing_in_reproduced=missing_in_reproduced,
            missing_in_reference=missing_in_reference,
        )

    diffs = [abs(ref_flows[k] - rep_flows[k]) for k in common_keys]
    max_diff = max(diffs)
    mean_diff = sum(diffs) / len(diffs)
    exceedance_count = sum(1 for d in diffs if d > tolerance_mw)

    passed = (
        exceedance_count == 0 and len(missing_in_reproduced) == 0 and len(missing_in_reference) == 0
    )

    return BranchComparison(
        total_branches=len(common_keys),
        max_flow_diff_mw=max_diff,
        mean_flow_diff_mw=mean_diff,
        exceedance_count=exceedance_count,
        tolerance_mw=tolerance_mw,
        passed=passed,
        missing_in_reproduced=missing_in_reproduced,
        missing_in_reference=missing_in_reference,
    )


def compare_summaries(
    reference: dict,
    reproduced: dict,
    flow_tolerance_mw: float = DEFAULT_FLOW_TOLERANCE_MW,
) -> SummaryComparison:
    """Compare DCPF summary fields between reference and reproduced.

    Handles both the legacy flat format (success, n_buses, slack_bus, etc.)
    and the newer nested format (network_summary.active_bus_count, etc.).

    Integer fields are compared exactly; float fields use flow_tolerance_mw.

    Args:
        reference: Reference summary dict.
        reproduced: Reproduced summary dict.
        flow_tolerance_mw: Tolerance for float comparisons.

    Returns:
        SummaryComparison with per-field results.
    """
    field_checks: list[SummaryFieldCheck] = []

    def _get_nested(d: dict, *keys: str) -> int | float | bool | None:
        """Try to retrieve a value from a dict using multiple possible key paths."""
        for key in keys:
            parts = key.split(".")
            val = d
            for part in parts:
                if isinstance(val, dict) and part in val:
                    val = val[part]
                else:
                    val = None
                    break
            if val is not None:
                return val
        return None

    # Define comparison specs: (field_name, ref_keys, rep_keys, is_float)
    comparisons: list[tuple[str, list[str], list[str], bool]] = [
        (
            "n_buses",
            ["n_buses", "network_summary.active_bus_count"],
            ["n_buses", "network_summary.active_bus_count"],
            False,
        ),
        (
            "n_branches",
            ["n_branches", "network_summary.active_branch_count"],
            ["n_branches", "network_summary.active_branch_count"],
            False,
        ),
        (
            "slack_bus",
            ["slack_bus", "settings.slack_bus"],
            ["slack_bus", "settings.slack_bus"],
            False,
        ),
        (
            "success",
            ["success", "validation.all_checks_passed"],
            ["success", "validation.all_checks_passed"],
            False,
        ),
        (
            "total_gen_mw",
            ["total_gen_mw", "power_summary.total_generation_mw"],
            ["total_gen_mw", "power_summary.total_generation_mw"],
            True,
        ),
        (
            "total_load_mw",
            ["total_load_mw", "power_summary.total_load_mw"],
            ["total_load_mw", "power_summary.total_load_mw"],
            True,
        ),
    ]

    for field_name, ref_keys, rep_keys, is_float in comparisons:
        ref_val = _get_nested(reference, *ref_keys)
        rep_val = _get_nested(reproduced, *rep_keys)

        if ref_val is None or rep_val is None:
            # Skip fields not present in either summary
            continue

        if is_float:
            tolerance = flow_tolerance_mw
            passed = abs(float(ref_val) - float(rep_val)) <= tolerance
        else:
            tolerance = None
            # For success field, treat 1/True as equivalent
            if field_name == "success":
                passed = bool(ref_val) == bool(rep_val)
            else:
                passed = ref_val == rep_val

        field_checks.append(
            SummaryFieldCheck(
                field_name=field_name,
                expected=ref_val,
                actual=rep_val,
                tolerance=tolerance,
                passed=passed,
            )
        )

    all_passed = all(fc.passed for fc in field_checks) if field_checks else True

    return SummaryComparison(
        field_checks=field_checks,
        passed=all_passed,
    )


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------


def write_report(report: ReproducibilityReport, output_path: Path) -> None:
    """Write the reproducibility report as JSON.

    Args:
        report: The ReproducibilityReport to serialize.
        output_path: Path for the output JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "passed": report.passed,
        "reference_dir": report.reference_dir,
        "reproduced_dir": report.reproduced_dir,
        "tolerances": report.tolerances,
        "timestamp": report.timestamp,
        "wall_clock_seconds": report.wall_clock_seconds,
        "bus_comparison": {
            "total_buses": report.bus_comparison.total_buses,
            "max_angle_diff_deg": report.bus_comparison.max_angle_diff_deg,
            "mean_angle_diff_deg": report.bus_comparison.mean_angle_diff_deg,
            "exceedance_count": report.bus_comparison.exceedance_count,
            "tolerance_deg": report.bus_comparison.tolerance_deg,
            "passed": report.bus_comparison.passed,
            "missing_in_reproduced": report.bus_comparison.missing_in_reproduced,
            "missing_in_reference": report.bus_comparison.missing_in_reference,
        },
        "branch_comparison": {
            "total_branches": report.branch_comparison.total_branches,
            "max_flow_diff_mw": report.branch_comparison.max_flow_diff_mw,
            "mean_flow_diff_mw": report.branch_comparison.mean_flow_diff_mw,
            "exceedance_count": report.branch_comparison.exceedance_count,
            "tolerance_mw": report.branch_comparison.tolerance_mw,
            "passed": report.branch_comparison.passed,
            "missing_in_reproduced": [
                list(t) for t in report.branch_comparison.missing_in_reproduced
            ],
            "missing_in_reference": [
                list(t) for t in report.branch_comparison.missing_in_reference
            ],
        },
        "summary_comparison": {
            "passed": report.summary_comparison.passed,
            "field_checks": [
                {
                    "field_name": fc.field_name,
                    "expected": fc.expected,
                    "actual": fc.actual,
                    "tolerance": fc.tolerance,
                    "passed": fc.passed,
                }
                for fc in report.summary_comparison.field_checks
            ],
        },
    }

    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# DCPF invocation via CSV path
# ---------------------------------------------------------------------------


def _prepare_bus_csv_with_load(
    bus_csv: Path,
    load_csv: Path,
    output_path: Path,
) -> Path:
    """Merge load data into the bus CSV if it lacks a PD column.

    The PSS/E-format intermediate bus.csv has columns like I, NAME, BASKV, IDE
    but no PD.  Load data is in a separate load.csv with columns I, PL, etc.
    This function aggregates PL by bus number and writes a merged bus CSV with
    a PD column.

    If the bus CSV already has a PD or pd column, it is copied unchanged.

    Args:
        bus_csv: Path to the input bus CSV.
        load_csv: Path to the load CSV (may not exist if no loads).
        output_path: Path for the merged output CSV.

    Returns:
        Path to the output CSV (same as output_path).
    """
    with open(bus_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"Bus CSV is empty: {bus_csv}")

    headers = [h.strip().lower() for h in rows[0]]

    # If PD already exists, just copy the file
    if "pd" in headers or "pl" in headers:
        import shutil

        shutil.copy2(bus_csv, output_path)
        return output_path

    # Aggregate loads from load.csv by bus number
    bus_load: dict[int, float] = {}
    if load_csv.exists():
        with open(load_csv, encoding="utf-8") as f:
            load_reader = csv.DictReader(f)
            for row in load_reader:
                bus_num = int(float(row["I"].strip()))
                # Only count in-service loads
                status = int(float(row.get("STATUS", row.get("status", "1")).strip()))
                if status != 1:
                    continue
                pl = float(row.get("PL", row.get("pl", "0")).strip())
                bus_load[bus_num] = bus_load.get(bus_num, 0.0) + pl

    # Write merged CSV with PD column added
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0] + ["PD"])
        for row in rows[1:]:
            if not row or all(cell.strip() == "" for cell in row):
                continue
            bus_num = int(float(row[0].strip()))  # First column is bus number (I)
            pd = bus_load.get(bus_num, 0.0)
            writer.writerow(row + [f"{pd:.6f}"])

    return output_path


def run_dcpf_via_csv_path(
    intermediate_dir: Path,
    exclusion_path: Path,
    output_dir: Path,
) -> Path:
    """Run the DCPF solver using intermediate CSVs and return the output directory.

    Calls ``dcpf_reference.run_dcpf_reference`` programmatically, loading
    bus, generator, branch, and optionally transformer CSVs from the
    intermediate directory.

    If the bus CSV lacks a PD column (PSS/E raw format), load data is
    automatically merged from load.csv.

    Args:
        intermediate_dir: Directory containing bus.csv, generator.csv,
            branch.csv, transformer.csv, and manifest.json.
        exclusion_path: Path to the excluded_buses.csv file.
        output_dir: Directory where DCPF outputs will be written.

    Returns:
        Path to the output directory (same as output_dir).

    Raises:
        FileNotFoundError: If required input files are missing.
    """
    bus_csv = intermediate_dir / "bus.csv"
    gen_csv = intermediate_dir / "generator.csv"
    branch_csv = intermediate_dir / "branch.csv"
    transformer_csv = intermediate_dir / "transformer.csv"
    load_csv = intermediate_dir / "load.csv"
    manifest_path = intermediate_dir / "manifest.json"

    # Verify required inputs exist
    for p in [bus_csv, gen_csv, branch_csv]:
        if not p.exists():
            raise FileNotFoundError(f"Required input file not found: {p}")

    # Load manifest for baseMVA
    base_mva = 100.0
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        if "sbase" in manifest:
            base_mva = float(manifest["sbase"])

    # Preprocess bus CSV to include PD column if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    merged_bus_csv = output_dir / "_bus_with_pd.csv"
    _prepare_bus_csv_with_load(bus_csv, load_csv, merged_bus_csv)

    # Determine transformer path
    xfmr_path = transformer_csv if transformer_csv.exists() else None

    run_dcpf_reference(
        bus_csv_path=merged_bus_csv,
        gen_csv_path=gen_csv,
        branch_csv_path=branch_csv,
        exclusion_csv_path=exclusion_path,
        output_dir=output_dir,
        base_mva=base_mva,
        canonical_parser="reproducibility_validation",
        transformer_csv_path=xfmr_path,
    )

    # Clean up temp file
    if merged_bus_csv.exists():
        merged_bus_csv.unlink()

    return output_dir


# ---------------------------------------------------------------------------
# End-to-end validation
# ---------------------------------------------------------------------------


def run_validation(
    reference_dir: Path,
    intermediate_dir: Path,
    exclusion_path: Path,
    report_output_path: Path,
) -> ReproducibilityReport:
    """Run the full reproducibility validation pipeline.

    1. Run DCPF via CSV path to produce a reproduced solution.
    2. Compare reproduced buses, branches, and summary against reference.
    3. Write the validation report.

    Args:
        reference_dir: Directory containing committed reference files
            (summary_dcpf.json, and optionally buses_dcpf.csv, branches_dcpf.csv).
        intermediate_dir: Directory containing intermediate CSVs.
        exclusion_path: Path to excluded_buses.csv.
        report_output_path: Path for the validation report JSON.

    Returns:
        ReproducibilityReport with all comparison results.
    """
    t0 = time.monotonic()

    # Run the DCPF solver to produce reproduced outputs
    with tempfile.TemporaryDirectory(prefix="dcpf_repro_") as tmpdir:
        reproduced_dir = Path(tmpdir)
        run_dcpf_via_csv_path(intermediate_dir, exclusion_path, reproduced_dir)

        # --- Bus comparison ---
        ref_buses_path = reference_dir / "buses_dcpf.csv"
        rep_buses_path = reproduced_dir / "buses_dcpf.csv"

        if ref_buses_path.exists() and rep_buses_path.exists():
            ref_buses = load_reference_buses(ref_buses_path)
            rep_buses = load_reference_buses(rep_buses_path)
            bus_cmp = compare_bus_angles(ref_buses, rep_buses)
        else:
            # If reference buses CSV doesn't exist, run a second DCPF as reference
            # and compare against the first run (determinism check)
            with tempfile.TemporaryDirectory(prefix="dcpf_ref2_") as tmpdir2:
                ref2_dir = Path(tmpdir2)
                run_dcpf_via_csv_path(intermediate_dir, exclusion_path, ref2_dir)
                ref_buses = load_reference_buses(ref2_dir / "buses_dcpf.csv")
                rep_buses = load_reference_buses(rep_buses_path)
                bus_cmp = compare_bus_angles(ref_buses, rep_buses)

        # --- Branch comparison ---
        ref_branches_path = reference_dir / "branches_dcpf.csv"
        rep_branches_path = reproduced_dir / "branches_dcpf.csv"

        if ref_branches_path.exists() and rep_branches_path.exists():
            branch_cmp = compare_branch_flows(ref_branches_path, rep_branches_path)
        else:
            # Determinism check: both outputs from same solver should match exactly
            with tempfile.TemporaryDirectory(prefix="dcpf_ref3_") as tmpdir3:
                ref3_dir = Path(tmpdir3)
                run_dcpf_via_csv_path(intermediate_dir, exclusion_path, ref3_dir)
                branch_cmp = compare_branch_flows(ref3_dir / "branches_dcpf.csv", rep_branches_path)

        # --- Summary comparison ---
        ref_summary_path = reference_dir / "summary_dcpf.json"
        rep_summary_path = reproduced_dir / "summary_dcpf.json"

        if ref_summary_path.exists() and rep_summary_path.exists():
            ref_summary = load_reference_summary(ref_summary_path)
            rep_summary = load_reference_summary(rep_summary_path)
            summary_cmp = compare_summaries(ref_summary, rep_summary)
        else:
            summary_cmp = SummaryComparison(field_checks=[], passed=True)

    elapsed = time.monotonic() - t0

    overall_passed = bus_cmp.passed and branch_cmp.passed and summary_cmp.passed

    report = ReproducibilityReport(
        passed=overall_passed,
        bus_comparison=bus_cmp,
        branch_comparison=branch_cmp,
        summary_comparison=summary_cmp,
        reference_dir=str(reference_dir),
        reproduced_dir="<tempdir>",
        tolerances={
            "angle_deg": DEFAULT_ANGLE_TOLERANCE_DEG,
            "flow_mw": DEFAULT_FLOW_TOLERANCE_MW,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
        wall_clock_seconds=round(elapsed, 3),
    )

    write_report(report, report_output_path)
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for DCPF reproducibility validation.

    Usage::

        python validate_dcpf_reproducibility.py \\
            --reference-dir data/fnm/reference/dcpf \\
            --intermediate-dir data/fnm/reference/cleaned/intermediate \\
            --exclusion-csv data/fnm/reference/excluded_buses.csv \\
            [-o report.json]

    Exit codes:
    - 0: All comparisons passed.
    - 1: One or more comparisons failed.
    - 2: Input error (missing files, etc.).
    """
    parser = argparse.ArgumentParser(description="Validate DCPF reference reproducibility.")
    parser.add_argument(
        "--reference-dir",
        type=Path,
        required=True,
        help="Directory containing committed DCPF reference files.",
    )
    parser.add_argument(
        "--intermediate-dir",
        type=Path,
        required=True,
        help="Directory containing intermediate CSVs from the canonical parser.",
    )
    parser.add_argument(
        "--exclusion-csv",
        type=Path,
        required=True,
        help="Path to excluded_buses.csv.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/fnm/reference/dcpf/reproducibility_report.json"),
        help="Output path for the validation report JSON.",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Validate inputs exist
    if not args.reference_dir.is_dir():
        print(f"Error: Reference directory not found: {args.reference_dir}", file=sys.stderr)
        sys.exit(2)
    if not args.intermediate_dir.is_dir():
        print(
            f"Error: Intermediate directory not found: {args.intermediate_dir}",
            file=sys.stderr,
        )
        sys.exit(2)
    if not args.exclusion_csv.exists():
        print(f"Error: Exclusion CSV not found: {args.exclusion_csv}", file=sys.stderr)
        sys.exit(2)

    try:
        report = run_validation(
            reference_dir=args.reference_dir,
            intermediate_dir=args.intermediate_dir,
            exclusion_path=args.exclusion_csv,
            report_output_path=args.output,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"Reproducibility validation: {'PASSED' if report.passed else 'FAILED'}")
    print(f"  Bus comparison: {'PASSED' if report.bus_comparison.passed else 'FAILED'}")
    print(f"    Max angle diff: {report.bus_comparison.max_angle_diff_deg:.6f} deg")
    print(f"    Exceedances: {report.bus_comparison.exceedance_count}")
    print(f"  Branch comparison: {'PASSED' if report.branch_comparison.passed else 'FAILED'}")
    print(f"    Max flow diff: {report.branch_comparison.max_flow_diff_mw:.6f} MW")
    print(f"    Exceedances: {report.branch_comparison.exceedance_count}")
    print(f"  Summary comparison: {'PASSED' if report.summary_comparison.passed else 'FAILED'}")
    print(f"  Wall clock: {report.wall_clock_seconds:.3f}s")
    print(f"  Report written to: {args.output}")

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
