"""Cross-Network Consistency Checks (PRD 05/06).

Loads summary statistics from all three networks (TINY case39, SMALL ACTIVSg2000,
MEDIUM ACTIVSg10k), computes per-network ratios and parameter values, and compares
them against each other and against design targets.

The checks fall into four categories:
1. Parameter identity checks - BESS RTE must be identical across networks
2. Fleet ratio range checks - BESS 3-5% of peak, DR 2-8% of peak, etc.
3. Structural count checks - Bus/gen/branch counts within expected ranges
4. Statistical consistency checks - Student-t df values comparable across networks

All validation logic uses only Python stdlib modules.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from statistics import median

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class NetworkId(StrEnum):
    """Network identifiers."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class ConsistencyStatus(StrEnum):
    """Outcome status for a consistency check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


EXPECTED_BUS_COUNTS: dict[str, tuple[int, int]] = {
    "case39": (39, 39),
    "ACTIVSg2000": (1900, 2100),
    "ACTIVSg10k": (9500, 10500),
}

EXPECTED_GEN_COUNT_RANGES: dict[str, tuple[int, int]] = {
    "case39": (10, 10),
    "ACTIVSg2000": (500, 600),
    "ACTIVSg10k": (2500, 3500),
}

EXPECTED_BRANCH_COUNT_RANGES: dict[str, tuple[int, int]] = {
    "case39": (46, 46),
    "ACTIVSg2000": (2500, 3500),
    "ACTIVSg10k": (12000, 15000),
}

FLOWGATE_COUNT_MIN: int = 3
FLOWGATE_COUNT_MAX: int = 5

BESS_FLEET_PCT_MIN: float = 0.03
BESS_FLEET_PCT_MAX: float = 0.05

DR_FLEET_PCT_MIN: float = 0.02
DR_FLEET_PCT_MAX: float = 0.08

RESERVE_RATIO_MAX_DIFF: float = 0.02

RENEWABLE_PENETRATION_MIN: float = 0.10
RENEWABLE_PENETRATION_MAX: float = 0.40

STUDENT_T_DF_MIN: float = 3.0
STUDENT_T_DF_MAX: float = 15.0
STUDENT_T_DF_MAX_RATIO: float = 3.0

NETWORK_DIRS: dict[str, str] = {
    "TINY": "case39",
    "SMALL": "ACTIVSg2000",
    "MEDIUM": "ACTIVSg10k",
}

MFILE_NAMES: dict[str, str] = {
    "case39": "case39_clean.m",
    "ACTIVSg2000": "ACTIVSg2000_clean.m",
    "ACTIVSg10k": "ACTIVSg10k_clean.m",
}

HR_COLUMNS: list[str] = [f"HR_{h}" for h in range(1, 25)]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NetworkSummary:
    """Summary statistics for a single network."""

    network_id: NetworkId
    bus_count: int
    gen_count: int
    branch_count: int
    peak_load_mw: float
    bess_fleet_mw: float
    bess_rte_values: list[float]
    dr_curtail_mw: float
    spinning_reserve_peak_mw: float
    non_spinning_reserve_peak_mw: float
    renewable_peak_mw: float
    flowgate_count: int
    wind_student_t_df: float | None
    solar_student_t_df: float | None


@dataclass(frozen=True)
class ConsistencyCheckResult:
    """Result of a single cross-network consistency check."""

    check_id: str
    check_name: str
    status: ConsistencyStatus
    message: str
    per_network_values: dict[str, float | int | str | None]
    threshold_description: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossNetworkComparisonTable:
    """Tabular comparison of metrics across networks."""

    metrics: list[str]
    networks: list[str]
    values: dict[str, dict[str, float | int | str | None]]
    statuses: dict[str, dict[str, ConsistencyStatus]]


@dataclass(frozen=True)
class CrossNetworkReport:
    """Full cross-network consistency report."""

    check_results: list[ConsistencyCheckResult]
    comparison_table: CrossNetworkComparisonTable
    total_checks: int
    checks_passed: int
    checks_failed: int
    checks_skipped: int
    overall_pass: bool


# ---------------------------------------------------------------------------
# CSV / file helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return rows as list of dicts."""
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def extract_bus_gen_branch_counts(mfile_path: Path) -> tuple[int, int, int]:
    """Parse a MATPOWER .m file and count rows in bus, gen, branch matrices.

    Args:
        mfile_path: Path to the .m file.

    Returns:
        Tuple of (bus_count, gen_count, branch_count).
    """
    text = mfile_path.read_text(encoding="utf-8")

    def _count_matrix_rows(matrix_name: str) -> int:
        pattern = rf"mpc\.{matrix_name}\s*=\s*\["
        match = re.search(pattern, text)
        if match is None:
            return 0
        start = match.end()
        end_match = re.search(r"\];", text[start:])
        if end_match is None:
            return 0
        block = text[start : start + end_match.start()]
        rows = [line.strip() for line in block.strip().splitlines()]
        return sum(1 for r in rows if r and not r.startswith("%"))

    bus_count = _count_matrix_rows("bus")
    gen_count = _count_matrix_rows("gen")
    branch_count = _count_matrix_rows("branch")
    return bus_count, gen_count, branch_count


def extract_peak_load(network_dir: Path) -> float:
    """Extract peak system load from load_24h.csv.

    Sums across all buses for each hour and returns the maximum.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        Peak system load in MW.
    """
    csv_path = network_dir / "load_24h.csv"
    rows = _read_csv(csv_path)
    hourly_totals: list[float] = []
    for col in HR_COLUMNS:
        total = sum(float(row[col]) for row in rows)
        hourly_totals.append(total)
    return max(hourly_totals)


def extract_bess_summary(network_dir: Path) -> tuple[float, list[float]]:
    """Extract BESS fleet MW and round-trip efficiency values.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        Tuple of (total_fleet_mw, sorted unique RTE values).
    """
    csv_path = network_dir / "bess_units.csv"
    rows = _read_csv(csv_path)
    total_mw = 0.0
    rte_values: set[float] = set()
    for row in rows:
        total_mw += float(row["power_mw"])
        # Handle both column naming conventions
        rte_key = "roundtrip_eff" if "roundtrip_eff" in row else "efficiency"
        rte_values.add(float(row[rte_key]))
    return total_mw, sorted(rte_values)


def extract_dr_summary(network_dir: Path) -> float:
    """Extract total DR curtailment MW.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        Total DR curtailment capacity in MW.
    """
    csv_path = network_dir / "dr_buses.csv"
    rows = _read_csv(csv_path)
    total = 0.0
    for row in rows:
        # Handle both column naming conventions
        key = "max_curtail_mw" if "max_curtail_mw" in row else "max_curtailment_mw"
        total += float(row[key])
    return total


def extract_reserve_summary(network_dir: Path) -> tuple[float, float]:
    """Extract peak spinning and non-spinning reserve requirements.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        Tuple of (peak_spinning_mw, peak_non_spinning_mw).
    """
    csv_path = network_dir / "reserve_requirements_24h.csv"
    rows = _read_csv(csv_path)
    spinning_peak = 0.0
    non_spinning_peak = 0.0
    for row in rows:
        product = row["product"].strip().lower()
        hourly = [float(row[col]) for col in HR_COLUMNS]
        peak = max(hourly)
        if product == "spinning":
            spinning_peak = peak
        elif product == "non_spinning":
            non_spinning_peak = peak
    return spinning_peak, non_spinning_peak


def extract_renewable_peak(network_dir: Path) -> float:
    """Extract peak renewable (wind + solar) capacity.

    Sums wind_forecast_24h and solar_forecast_24h max values across generators.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        Peak renewable capacity in MW.
    """
    total = 0.0
    for fname in ("wind_forecast_24h.csv", "solar_forecast_24h.csv"):
        csv_path = network_dir / fname
        if not csv_path.exists():
            continue
        rows = _read_csv(csv_path)
        for row in rows:
            hourly = [float(row[col]) for col in HR_COLUMNS]
            total += max(hourly)
    return total


def extract_student_t_df(
    scenarios_dir: Path | None,
) -> tuple[float | None, float | None]:
    """Extract Student-t df values from scenario metadata.

    Tries stochastic_metadata.json first, then student_t_params.json.

    Args:
        scenarios_dir: Path to the scenarios directory. If None, returns (None, None).

    Returns:
        Tuple of (wind_df, solar_df). Either may be None if not found.
    """
    if scenarios_dir is None or not scenarios_dir.exists():
        return None, None

    wind_df: float | None = None
    solar_df: float | None = None

    for fname in ("stochastic_metadata.json", "student_t_params.json"):
        fpath = scenarios_dir / fname
        if not fpath.exists():
            continue
        data = json.loads(fpath.read_text(encoding="utf-8"))

        # Handle various JSON structures
        if "wind" in data:
            wind_section = data["wind"]
            if isinstance(wind_section, dict):
                if "df" in wind_section:
                    val = wind_section["df"]
                    if isinstance(val, list):
                        wind_df = median(val)
                    else:
                        wind_df = float(val)
                elif "params" in wind_section and "df" in wind_section["params"]:
                    val = wind_section["params"]["df"]
                    if isinstance(val, list):
                        wind_df = median(val)
                    else:
                        wind_df = float(val)

        if "solar" in data:
            solar_section = data["solar"]
            if isinstance(solar_section, dict):
                if "df" in solar_section:
                    val = solar_section["df"]
                    if isinstance(val, list):
                        solar_df = median(val)
                    else:
                        solar_df = float(val)
                elif "params" in solar_section and "df" in solar_section["params"]:
                    val = solar_section["params"]["df"]
                    if isinstance(val, list):
                        solar_df = median(val)
                    else:
                        solar_df = float(val)

        # If we found data, stop looking
        if wind_df is not None or solar_df is not None:
            break

    return wind_df, solar_df


def extract_flowgate_count(network_dir: Path) -> int:
    """Count flowgate definitions in the network directory.

    Looks for flowgates.csv or counts flowgate_*.csv files.

    Args:
        network_dir: Path to the network's timeseries directory.

    Returns:
        Number of flowgates defined.
    """
    flowgates_csv = network_dir / "flowgates.csv"
    if flowgates_csv.exists():
        rows = _read_csv(flowgates_csv)
        return len(rows)

    # Fall back to counting flowgate definition files
    count = 0
    for p in network_dir.iterdir():
        if p.name.startswith("flowgate_") and p.name.endswith(".csv"):
            count += 1
    return count


def extract_network_summary(
    network_id: NetworkId,
    network_dir: Path,
    mfile_path: Path,
    scenarios_dir: Path | None = None,
) -> NetworkSummary:
    """Extract a complete summary for a single network.

    Args:
        network_id: Network identifier.
        network_dir: Path to the network's timeseries directory.
        mfile_path: Path to the MATPOWER .m file.
        scenarios_dir: Optional path to scenario metadata directory.

    Returns:
        A NetworkSummary with all extracted statistics.
    """
    bus_count, gen_count, branch_count = extract_bus_gen_branch_counts(mfile_path)
    peak_load = extract_peak_load(network_dir)
    bess_fleet_mw, bess_rte_values = extract_bess_summary(network_dir)
    dr_curtail_mw = extract_dr_summary(network_dir)
    spinning_peak, non_spinning_peak = extract_reserve_summary(network_dir)
    renewable_peak = extract_renewable_peak(network_dir)
    flowgate_count = extract_flowgate_count(network_dir)
    wind_df, solar_df = extract_student_t_df(scenarios_dir)

    return NetworkSummary(
        network_id=network_id,
        bus_count=bus_count,
        gen_count=gen_count,
        branch_count=branch_count,
        peak_load_mw=peak_load,
        bess_fleet_mw=bess_fleet_mw,
        bess_rte_values=bess_rte_values,
        dr_curtail_mw=dr_curtail_mw,
        spinning_reserve_peak_mw=spinning_peak,
        non_spinning_reserve_peak_mw=non_spinning_peak,
        renewable_peak_mw=renewable_peak,
        flowgate_count=flowgate_count,
        wind_student_t_df=wind_df,
        solar_student_t_df=solar_df,
    )


# ---------------------------------------------------------------------------
# Consistency check functions
# ---------------------------------------------------------------------------


def check_bess_rte_identical(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that BESS round-trip efficiency values are identical across all networks.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    all_rte_sets: list[list[float]] = []

    for s in summaries:
        rte_str = ",".join(f"{v:.4f}" for v in s.bess_rte_values)
        per_network[s.network_id.value] = rte_str
        all_rte_sets.append(s.bess_rte_values)

    # Check all are identical
    identical = all(rte == all_rte_sets[0] for rte in all_rte_sets)

    if identical:
        status = ConsistencyStatus.PASS
        msg = f"BESS RTE identical across all networks: {all_rte_sets[0]}"
    else:
        status = ConsistencyStatus.FAIL
        msg = "BESS RTE differs across networks"

    return ConsistencyCheckResult(
        check_id="bess_rte_identical",
        check_name="BESS RTE Identity",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description="All networks must have identical BESS RTE values",
    )


def check_bess_fleet_pct(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that BESS fleet MW is 3-5% of peak load for each network.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    all_pass = True

    for s in summaries:
        ratio = s.bess_fleet_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
        per_network[s.network_id.value] = round(ratio, 4)
        if ratio < BESS_FLEET_PCT_MIN or ratio > BESS_FLEET_PCT_MAX:
            all_pass = False

    status = ConsistencyStatus.PASS if all_pass else ConsistencyStatus.FAIL
    msg = (
        "BESS fleet % of peak load within range"
        if all_pass
        else "BESS fleet % of peak load out of range for one or more networks"
    )

    return ConsistencyCheckResult(
        check_id="bess_fleet_pct",
        check_name="BESS Fleet % of Peak",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description=f"BESS fleet MW must be {BESS_FLEET_PCT_MIN:.0%}-"
        f"{BESS_FLEET_PCT_MAX:.0%} of peak load",
    )


def check_dr_fleet_pct(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that DR curtailment MW is 2-8% of peak load for each network.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    all_pass = True

    for s in summaries:
        ratio = s.dr_curtail_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
        per_network[s.network_id.value] = round(ratio, 4)
        if ratio < DR_FLEET_PCT_MIN or ratio > DR_FLEET_PCT_MAX:
            all_pass = False

    status = ConsistencyStatus.PASS if all_pass else ConsistencyStatus.FAIL
    msg = (
        "DR fleet % of peak load within range"
        if all_pass
        else "DR fleet % of peak load out of range for one or more networks"
    )

    return ConsistencyCheckResult(
        check_id="dr_fleet_pct",
        check_name="DR Fleet % of Peak",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description=f"DR curtailment MW must be {DR_FLEET_PCT_MIN:.0%}-"
        f"{DR_FLEET_PCT_MAX:.0%} of peak load",
    )


def check_reserve_ratio_consistency(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that spinning reserve ratios are within 2pp of each other.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    ratios: list[float] = []

    for s in summaries:
        ratio = s.spinning_reserve_peak_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
        per_network[s.network_id.value] = round(ratio, 4)
        ratios.append(ratio)

    spread = max(ratios) - min(ratios) if ratios else 0.0
    passes = spread <= RESERVE_RATIO_MAX_DIFF

    status = ConsistencyStatus.PASS if passes else ConsistencyStatus.FAIL
    msg = (
        f"Reserve ratio spread {spread:.4f} within {RESERVE_RATIO_MAX_DIFF} limit"
        if passes
        else f"Reserve ratio spread {spread:.4f} exceeds {RESERVE_RATIO_MAX_DIFF} limit"
    )

    return ConsistencyCheckResult(
        check_id="reserve_ratio_consistency",
        check_name="Reserve Ratio Consistency",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description=f"Spinning reserve ratios must be within "
        f"{RESERVE_RATIO_MAX_DIFF:.0%} of each other",
        details={"spread": spread},
    )


def check_renewable_penetration(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that renewable penetration is 10-40% of peak load for each network.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    all_pass = True

    for s in summaries:
        ratio = s.renewable_peak_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
        per_network[s.network_id.value] = round(ratio, 4)
        if ratio < RENEWABLE_PENETRATION_MIN or ratio > RENEWABLE_PENETRATION_MAX:
            all_pass = False

    status = ConsistencyStatus.PASS if all_pass else ConsistencyStatus.FAIL
    msg = (
        "Renewable penetration within range"
        if all_pass
        else "Renewable penetration out of range for one or more networks"
    )

    return ConsistencyCheckResult(
        check_id="renewable_penetration",
        check_name="Renewable Penetration",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description=f"Renewable MW must be {RENEWABLE_PENETRATION_MIN:.0%}-"
        f"{RENEWABLE_PENETRATION_MAX:.0%} of peak load",
    )


def check_student_t_df_consistency(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that Student-t df values are comparable across networks.

    If all networks have None df values, the check is SKIPPED. Otherwise,
    non-None values must be in [STUDENT_T_DF_MIN, STUDENT_T_DF_MAX] and the
    ratio of max to min must not exceed STUDENT_T_DF_MAX_RATIO.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    wind_dfs: list[float] = []
    solar_dfs: list[float] = []

    for s in summaries:
        per_network[f"{s.network_id.value}_wind"] = s.wind_student_t_df
        per_network[f"{s.network_id.value}_solar"] = s.solar_student_t_df
        if s.wind_student_t_df is not None:
            wind_dfs.append(s.wind_student_t_df)
        if s.solar_student_t_df is not None:
            solar_dfs.append(s.solar_student_t_df)

    all_dfs = wind_dfs + solar_dfs
    if not all_dfs:
        return ConsistencyCheckResult(
            check_id="student_t_df_consistency",
            check_name="Student-t df Consistency",
            status=ConsistencyStatus.SKIPPED,
            message="No Student-t df values found across any network",
            per_network_values=per_network,
            threshold_description=f"df values must be in [{STUDENT_T_DF_MIN}, "
            f"{STUDENT_T_DF_MAX}] with max/min ratio <= {STUDENT_T_DF_MAX_RATIO}",
        )

    # Check bounds
    all_in_bounds = all(STUDENT_T_DF_MIN <= d <= STUDENT_T_DF_MAX for d in all_dfs)

    # Check ratio consistency within each resource type
    ratio_ok = True
    for dfs in (wind_dfs, solar_dfs):
        if len(dfs) >= 2:
            r = max(dfs) / min(dfs) if min(dfs) > 0 else float("inf")
            if r > STUDENT_T_DF_MAX_RATIO:
                ratio_ok = False

    passes = all_in_bounds and ratio_ok
    status = ConsistencyStatus.PASS if passes else ConsistencyStatus.FAIL

    parts: list[str] = []
    if not all_in_bounds:
        parts.append("some df values outside bounds")
    if not ratio_ok:
        parts.append("max/min ratio too large")

    msg = (
        "Student-t df values consistent across networks"
        if passes
        else f"Student-t df inconsistency: {'; '.join(parts)}"
    )

    return ConsistencyCheckResult(
        check_id="student_t_df_consistency",
        check_name="Student-t df Consistency",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description=f"df values must be in [{STUDENT_T_DF_MIN}, "
        f"{STUDENT_T_DF_MAX}] with max/min ratio <= {STUDENT_T_DF_MAX_RATIO}",
    )


def check_flowgate_count_range(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that flowgate counts are within [3, 5] for each network.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    all_pass = True

    for s in summaries:
        per_network[s.network_id.value] = s.flowgate_count
        if s.flowgate_count < FLOWGATE_COUNT_MIN or s.flowgate_count > FLOWGATE_COUNT_MAX:
            all_pass = False

    status = ConsistencyStatus.PASS if all_pass else ConsistencyStatus.FAIL
    msg = (
        "Flowgate counts within range"
        if all_pass
        else "Flowgate counts out of range for one or more networks"
    )

    return ConsistencyCheckResult(
        check_id="flowgate_count_range",
        check_name="Flowgate Count Range",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description=f"Flowgate count must be in "
        f"[{FLOWGATE_COUNT_MIN}, {FLOWGATE_COUNT_MAX}]",
    )


def check_structural_counts(
    summaries: list[NetworkSummary],
) -> ConsistencyCheckResult:
    """Check that bus, gen, and branch counts are within expected ranges.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        A ConsistencyCheckResult.
    """
    per_network: dict[str, float | int | str | None] = {}
    all_pass = True
    failures: list[str] = []

    for s in summaries:
        nid = s.network_id.value
        per_network[f"{nid}_bus"] = s.bus_count
        per_network[f"{nid}_gen"] = s.gen_count
        per_network[f"{nid}_branch"] = s.branch_count

        if nid in EXPECTED_BUS_COUNTS:
            lo, hi = EXPECTED_BUS_COUNTS[nid]
            if not (lo <= s.bus_count <= hi):
                all_pass = False
                failures.append(f"{nid} bus_count={s.bus_count} not in [{lo}, {hi}]")

        if nid in EXPECTED_GEN_COUNT_RANGES:
            lo, hi = EXPECTED_GEN_COUNT_RANGES[nid]
            if not (lo <= s.gen_count <= hi):
                all_pass = False
                failures.append(f"{nid} gen_count={s.gen_count} not in [{lo}, {hi}]")

        if nid in EXPECTED_BRANCH_COUNT_RANGES:
            lo, hi = EXPECTED_BRANCH_COUNT_RANGES[nid]
            if not (lo <= s.branch_count <= hi):
                all_pass = False
                failures.append(f"{nid} branch_count={s.branch_count} not in [{lo}, {hi}]")

    status = ConsistencyStatus.PASS if all_pass else ConsistencyStatus.FAIL
    msg = (
        "Structural counts within expected ranges"
        if all_pass
        else f"Structural count failures: {'; '.join(failures)}"
    )

    return ConsistencyCheckResult(
        check_id="structural_counts",
        check_name="Structural Counts",
        status=status,
        message=msg,
        per_network_values=per_network,
        threshold_description="Bus/gen/branch counts must be within expected ranges",
        details={"failures": failures} if failures else {},
    )


# ---------------------------------------------------------------------------
# Comparison table builder
# ---------------------------------------------------------------------------


def build_comparison_table(
    summaries: list[NetworkSummary],
    check_results: list[ConsistencyCheckResult],
) -> CrossNetworkComparisonTable:
    """Build a tabular comparison of metrics across networks.

    The table includes 12 metrics:
    - bus_count, gen_count, branch_count
    - peak_load_mw, bess_fleet_pct, dr_fleet_pct
    - spinning_reserve_pct, non_spinning_reserve_pct
    - renewable_penetration_pct, flowgate_count
    - wind_student_t_df, solar_student_t_df

    Args:
        summaries: List of NetworkSummary for each network.
        check_results: List of ConsistencyCheckResult from all checks.

    Returns:
        A CrossNetworkComparisonTable.
    """
    metrics = [
        "bus_count",
        "gen_count",
        "branch_count",
        "peak_load_mw",
        "bess_fleet_pct",
        "dr_fleet_pct",
        "spinning_reserve_pct",
        "non_spinning_reserve_pct",
        "renewable_penetration_pct",
        "flowgate_count",
        "wind_student_t_df",
        "solar_student_t_df",
    ]
    networks = [s.network_id.value for s in summaries]

    values: dict[str, dict[str, float | int | str | None]] = {}
    statuses: dict[str, dict[str, ConsistencyStatus]] = {}

    for metric in metrics:
        values[metric] = {}
        statuses[metric] = {}
        for s in summaries:
            nid = s.network_id.value
            if metric == "bus_count":
                values[metric][nid] = s.bus_count
            elif metric == "gen_count":
                values[metric][nid] = s.gen_count
            elif metric == "branch_count":
                values[metric][nid] = s.branch_count
            elif metric == "peak_load_mw":
                values[metric][nid] = round(s.peak_load_mw, 2)
            elif metric == "bess_fleet_pct":
                pct = s.bess_fleet_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
                values[metric][nid] = round(pct, 4)
            elif metric == "dr_fleet_pct":
                pct = s.dr_curtail_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
                values[metric][nid] = round(pct, 4)
            elif metric == "spinning_reserve_pct":
                pct = s.spinning_reserve_peak_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
                values[metric][nid] = round(pct, 4)
            elif metric == "non_spinning_reserve_pct":
                pct = s.non_spinning_reserve_peak_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
                values[metric][nid] = round(pct, 4)
            elif metric == "renewable_penetration_pct":
                pct = s.renewable_peak_mw / s.peak_load_mw if s.peak_load_mw > 0 else 0.0
                values[metric][nid] = round(pct, 4)
            elif metric == "flowgate_count":
                values[metric][nid] = s.flowgate_count
            elif metric == "wind_student_t_df":
                values[metric][nid] = s.wind_student_t_df
            elif metric == "solar_student_t_df":
                values[metric][nid] = s.solar_student_t_df

            # Derive status from check results
            statuses[metric][nid] = _derive_metric_status(metric, s, check_results)

    return CrossNetworkComparisonTable(
        metrics=metrics,
        networks=networks,
        values=values,
        statuses=statuses,
    )


def _derive_metric_status(
    metric: str,
    summary: NetworkSummary,
    check_results: list[ConsistencyCheckResult],
) -> ConsistencyStatus:
    """Derive per-network status for a metric from check results."""
    # Map metrics to check IDs
    metric_to_check: dict[str, str] = {
        "bus_count": "structural_counts",
        "gen_count": "structural_counts",
        "branch_count": "structural_counts",
        "bess_fleet_pct": "bess_fleet_pct",
        "dr_fleet_pct": "dr_fleet_pct",
        "spinning_reserve_pct": "reserve_ratio_consistency",
        "non_spinning_reserve_pct": "reserve_ratio_consistency",
        "renewable_penetration_pct": "renewable_penetration",
        "flowgate_count": "flowgate_count_range",
        "wind_student_t_df": "student_t_df_consistency",
        "solar_student_t_df": "student_t_df_consistency",
    }

    check_id = metric_to_check.get(metric)
    if check_id is None:
        return ConsistencyStatus.PASS

    for cr in check_results:
        if cr.check_id == check_id:
            if cr.status == ConsistencyStatus.PASS:
                return ConsistencyStatus.PASS
            elif cr.status == ConsistencyStatus.SKIPPED:
                return ConsistencyStatus.SKIPPED
            else:
                return ConsistencyStatus.FAIL

    return ConsistencyStatus.PASS


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_all_cross_network_checks(
    summaries: list[NetworkSummary],
) -> list[ConsistencyCheckResult]:
    """Run all cross-network consistency checks.

    Args:
        summaries: List of NetworkSummary for each network.

    Returns:
        List of ConsistencyCheckResult from all checks.
    """
    return [
        check_bess_rte_identical(summaries),
        check_bess_fleet_pct(summaries),
        check_dr_fleet_pct(summaries),
        check_reserve_ratio_consistency(summaries),
        check_renewable_penetration(summaries),
        check_student_t_df_consistency(summaries),
        check_flowgate_count_range(summaries),
        check_structural_counts(summaries),
    ]


def validate_cross_network(
    timeseries_base_dir: Path | None = None,
    networks_base_dir: Path | None = None,
) -> CrossNetworkReport:
    """Run full cross-network validation across all three networks.

    Args:
        timeseries_base_dir: Base directory containing network timeseries subdirs.
            Defaults to <repo_root>/data/timeseries/.
        networks_base_dir: Base directory containing .m files.
            Defaults to <repo_root>/data/networks/.

    Returns:
        A CrossNetworkReport with all check results.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "data" / "timeseries"

    if networks_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        networks_base_dir = repo_root / "data" / "networks"

    summaries: list[NetworkSummary] = []
    for _tier, dir_name in NETWORK_DIRS.items():
        network_id = NetworkId(dir_name)
        network_dir = timeseries_base_dir / dir_name
        mfile_name = MFILE_NAMES.get(dir_name, f"{dir_name}.m")
        mfile_path = networks_base_dir / mfile_name

        # Scenarios directory: check inside the timeseries dir
        scenarios_dir = network_dir / "scenarios"
        if not scenarios_dir.exists():
            scenarios_dir = None

        summary = extract_network_summary(
            network_id=network_id,
            network_dir=network_dir,
            mfile_path=mfile_path,
            scenarios_dir=scenarios_dir,
        )
        summaries.append(summary)

    check_results = run_all_cross_network_checks(summaries)
    comparison_table = build_comparison_table(summaries, check_results)

    passed = sum(1 for r in check_results if r.status == ConsistencyStatus.PASS)
    failed = sum(1 for r in check_results if r.status == ConsistencyStatus.FAIL)
    skipped = sum(1 for r in check_results if r.status == ConsistencyStatus.SKIPPED)
    total = len(check_results)

    return CrossNetworkReport(
        check_results=check_results,
        comparison_table=comparison_table,
        total_checks=total,
        checks_passed=passed,
        checks_failed=failed,
        checks_skipped=skipped,
        overall_pass=(failed == 0),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    report = validate_cross_network()
    print(
        f"Results: {report.checks_passed} passed, {report.checks_failed} failed, "
        f"{report.checks_skipped} skipped out of {report.total_checks} checks"
    )
    for r in report.check_results:
        print(f"  [{r.status}] {r.check_id}: {r.message}")
