"""Flowgate & Scenario Validation (PRD 05/05).

Validates the complete flowgate definition layer and stochastic scenario layer
across all three networks (TINY, SMALL, MEDIUM). Flowgate checks (a-e) verify
structural correctness of each flowgate definition. Scenario checks (f-l) verify
both dimensional correctness and statistical quality of scenario multipliers.

This module is consumed by the consolidated ``scripts/validate.py`` entry point
and can also be run standalone for development.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np
from scipy import stats

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CORRELATION_FROBENIUS_THRESHOLD: float = 0.10
"""Default Frobenius norm threshold for correlation fidelity check (j)."""

DEFAULT_ENSEMBLE_MEAN_TOLERANCE: float = 0.05
"""Default tolerance for ensemble mean check (i). Mean must be within 5% of 1.0."""

MIN_FLOWGATES: int = 3
"""Minimum flowgates per network (check e)."""

MAX_FLOWGATES: int = 5
"""Maximum flowgates per network (check e)."""

EXPECTED_N_SCENARIOS: int = 50
"""Expected number of scenarios in each multiplier file (check f)."""

EXPECTED_N_HOURS: int = 24
"""Expected number of hourly columns HR_1..HR_24 (check f)."""

NETWORK_M_FILE_NAMES: dict[str, str] = {
    "case39": "case39.m",
    "ACTIVSg2000": "case_ACTIVSg2000.m",
    "ACTIVSg10k": "case_ACTIVSg10k.m",
}

MAX_DETAILS: int = 20
"""Maximum number of detail entries per check to avoid oversized JSON."""

_HOUR_COLUMNS: list[str] = [f"HR_{k}" for k in range(1, 25)]


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ValidationNetworkId(StrEnum):
    """Network identifiers for Phase 5 validation."""

    TINY = "case39"
    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class CheckStatus(StrEnum):
    """Outcome of a single validation check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class ResourceType(StrEnum):
    """Renewable resource types for scenario validation."""

    WIND = "wind"
    SOLAR = "solar"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchRecord:
    """Minimal branch record extracted from the cleaned .m file."""

    branch_idx: int  # 1-based index into the branch table
    from_bus: int
    to_bus: int
    rate_a_mw: float  # long-term thermal rating


@dataclass(frozen=True)
class NetworkBranchTopology:
    """Extracted branch topology from the cleaned .m file for flowgate validation.

    Pre-computed lookup structures for efficient cross-referencing.
    """

    network_id: str
    branches: list[BranchRecord]
    branch_idx_set: frozenset[int]  # set of valid 1-based branch indices
    branch_rate_map: dict[int, float]  # branch_idx -> rate_a_mw


@dataclass(frozen=True)
class FlowgateRecord:
    """Flowgate record loaded from flowgates.csv for validation."""

    flowgate_id: str
    flowgate_name: str
    branch_ids: list[int]  # parsed from semicolon-separated branch_id_list
    weights: list[float]  # parsed from semicolon-separated weight_list
    limit_mw: float
    direction: str


@dataclass(frozen=True)
class ScenarioMultiplierData:
    """Loaded scenario multiplier data for one network and resource type.

    The multiplier array has shape (n_scenarios, n_generators, 24).
    """

    network_id: str
    resource_type: ResourceType
    generator_ids: list[str]
    pmax_values: list[float]  # per generator, in MW
    multipliers: list[list[list[float]]]  # [scenario][generator][hour]
    n_scenarios: int
    n_generators: int
    n_hours: int


@dataclass(frozen=True)
class ForecastData:
    """Loaded forecast and actual profiles for one network and resource type."""

    network_id: str
    resource_type: ResourceType
    generator_ids: list[str]
    pmax_values: list[float]  # per generator, in MW
    forecast: list[list[float]]  # [generator][hour], MW values
    actual: list[list[float]]  # [generator][hour], MW values
    night_hours: list[int]  # hours where all solar generators have zero forecast


@dataclass(frozen=True)
class FlowgateCheckResult:
    """Result of a single flowgate validation check for one network."""

    check_id: str  # "a", "b", "c", "d", or "e"
    check_name: str  # human-readable
    status: CheckStatus
    message: str  # summary
    details: list[str]  # per-item failure details (empty if PASS)
    items_checked: int
    items_passed: int
    items_failed: int


@dataclass(frozen=True)
class ScenarioCheckResult:
    """Result of a single scenario validation check for one network."""

    check_id: str  # "f", "g", "h", "i", "j", "k", or "l"
    check_name: str  # human-readable
    status: CheckStatus
    measured_value: float | None  # the diagnostic metric
    threshold: float | None  # the pass/fail boundary
    message: str  # summary
    details: list[str]  # per-item failure details (empty if PASS)
    resource_type: ResourceType | None  # None if cross-resource
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowgateScenarioValidationResult:
    """Complete flowgate and scenario validation result for one network."""

    network_id: str
    flowgate_checks: list[FlowgateCheckResult]
    scenario_checks: list[ScenarioCheckResult]
    total_checks: int
    passed: int
    warned: int
    failed: int
    skipped: int
    overall_pass: bool  # True if no check has status FAIL


@dataclass(frozen=True)
class FlowgateScenarioValidationConfig:
    """Configurable thresholds for flowgate and scenario validation."""

    # Flowgate checks
    min_flowgates_per_network: int = 3
    max_flowgates_per_network: int = 5

    # Scenario checks
    expected_n_scenarios: int = 50
    expected_n_hours: int = 24
    ensemble_mean_tolerance: float = 0.05  # within 5% of 1.0
    correlation_frobenius_threshold: float = 0.10  # Frobenius norm < 0.10
    pmax_tolerance_mw: float = 1e-6  # floating-point tolerance for Pmax check
    wind_rmse_pct_range: tuple[float, float] = (10.0, 30.0)
    solar_rmse_pct_range: tuple[float, float] = (5.0, 15.0)


# ---------------------------------------------------------------------------
# MATPOWER branch parsing
# ---------------------------------------------------------------------------


def _parse_branches_from_m_file(m_file_path: Path) -> list[BranchRecord]:
    """Parse branch data from a MATPOWER .m file.

    Extracts from_bus (col 0), to_bus (col 1), and rateA (col 5) from the
    mpc.branch matrix. Branch indices are 1-based (first row = branch 1).

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        List of BranchRecord with 1-based branch indices.

    Raises:
        FileNotFoundError: If m_file_path does not exist.
        ValueError: If mpc.branch block cannot be located.
    """
    if not m_file_path.exists():
        msg = f"MATPOWER .m file not found: {m_file_path}"
        raise FileNotFoundError(msg)

    text = m_file_path.read_text(encoding="utf-8")
    pattern = re.compile(r"mpc\.branch\s*=\s*\[([^\]]*)\]", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        msg = f"Could not locate mpc.branch block in {m_file_path}"
        raise ValueError(msg)

    block = match.group(1)
    branches: list[BranchRecord] = []
    idx = 1  # 1-based

    for line in block.split(";"):
        line = line.strip()
        if "%" in line:
            line = line[: line.index("%")]
        line = line.strip()
        if not line:
            continue
        values = line.split()
        try:
            float_vals = [float(v) for v in values]
        except ValueError:
            continue

        if len(float_vals) < 6:
            continue

        branches.append(
            BranchRecord(
                branch_idx=idx,
                from_bus=int(float_vals[0]),
                to_bus=int(float_vals[1]),
                rate_a_mw=float_vals[5],
            )
        )
        idx += 1

    return branches


# ---------------------------------------------------------------------------
# Topology loading
# ---------------------------------------------------------------------------


def load_branch_topology(
    network_dir: Path,
    network_id: str,
) -> NetworkBranchTopology:
    """Load branch data from the cleaned .m file for flowgate validation.

    Parses the branch data section for branch indices, from_bus, to_bus,
    and rate_a. Constructs lookup sets and maps for efficient
    cross-referencing during flowgate checks.

    Args:
        network_dir: Path to the directory containing the cleaned .m file.
        network_id: Network identifier used to locate the .m file.

    Returns:
        A NetworkBranchTopology with branch data and lookup structures.

    Raises:
        FileNotFoundError: If the cleaned .m file is not found.
    """
    m_file_name = NETWORK_M_FILE_NAMES.get(network_id)
    if m_file_name is None:
        msg = f"Unknown network_id: {network_id}"
        raise ValueError(msg)

    m_file_path = network_dir / m_file_name
    branches = _parse_branches_from_m_file(m_file_path)

    branch_idx_set = frozenset(b.branch_idx for b in branches)
    branch_rate_map = {b.branch_idx: b.rate_a_mw for b in branches}

    return NetworkBranchTopology(
        network_id=network_id,
        branches=branches,
        branch_idx_set=branch_idx_set,
        branch_rate_map=branch_rate_map,
    )


# ---------------------------------------------------------------------------
# Flowgate loading
# ---------------------------------------------------------------------------


def load_flowgates(
    csv_path: Path,
) -> list[FlowgateRecord]:
    """Load flowgate records from flowgates.csv for validation.

    Handles both TINY schema (columns: flowgate_id, name, branches, weights,
    limit_mw, binding_load_level, max_loading_pct) and SMALL/MEDIUM schema
    (columns: flowgate_id, flowgate_name, branch_id_list, weight_list,
    limit_mw, direction, calibration_load_level).

    For TINY, the 'branches' column contains bus-pair strings like '16-19;16-21',
    which are NOT branch indices. The branch_ids will be parsed as integers from
    semicolon-separated values when the column contains plain integers (SMALL/MEDIUM),
    or will need special handling for TINY.

    Args:
        csv_path: Path to flowgates.csv.

    Returns:
        A list of FlowgateRecord, one per flowgate.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If required columns are missing.
    """
    if not csv_path.exists():
        msg = f"Flowgates CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    records: list[FlowgateRecord] = []

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            msg = "Flowgates CSV has no header row"
            raise ValueError(msg)

        cols = set(reader.fieldnames)

        # Detect schema variant
        is_small_medium = "branch_id_list" in cols
        is_tiny = "branches" in cols and "branch_id_list" not in cols

        for row in reader:
            if is_small_medium:
                flowgate_id = row["flowgate_id"]
                flowgate_name = row.get("flowgate_name", "")
                branch_id_str = row["branch_id_list"]
                weight_str = row["weight_list"]
                limit_mw = float(row["limit_mw"])
                direction = row.get("direction", "both")

                branch_ids = [int(x) for x in branch_id_str.split(";") if x.strip()]
                weights = [float(x) for x in weight_str.split(";") if x.strip()]

            elif is_tiny:
                flowgate_id = row["flowgate_id"]
                flowgate_name = row.get("name", "")
                branches_str = row["branches"]
                weight_str = row["weights"]
                limit_mw = float(row["limit_mw"])
                direction = "both"  # TINY doesn't have a direction column

                # TINY branches column contains bus-pair strings like "16-19;16-21"
                # We need to extract branch indices. For TINY, the branch indices
                # are embedded in the flowgate_id or must be looked up.
                # Parse as integer indices if possible, otherwise store bus pairs.
                parts = [x.strip() for x in branches_str.split(";") if x.strip()]
                branch_ids = []
                for part in parts:
                    try:
                        branch_ids.append(int(part))
                    except ValueError:
                        # Bus-pair format like "16-19" -- store as-is for now
                        # These will need to be resolved against the branch table
                        branch_ids.append(-1)  # placeholder

                weights = [float(x) for x in weight_str.split(";") if x.strip()]
            else:
                msg = f"Unrecognized flowgates.csv schema. Columns: {cols}"
                raise ValueError(msg)

            records.append(
                FlowgateRecord(
                    flowgate_id=flowgate_id,
                    flowgate_name=flowgate_name,
                    branch_ids=branch_ids,
                    weights=weights,
                    limit_mw=limit_mw,
                    direction=direction,
                )
            )

    return records


def _resolve_tiny_branch_ids(
    flowgates: list[FlowgateRecord],
    csv_path: Path,
    topology: NetworkBranchTopology,
) -> list[FlowgateRecord]:
    """Resolve TINY flowgate bus-pair branches to actual branch indices.

    TINY flowgates.csv uses bus-pair format (e.g., '16-19') instead of branch
    indices. This function maps each bus pair to the corresponding branch index
    in the topology.

    Args:
        flowgates: Flowgate records with potentially unresolved branch_ids (-1).
        csv_path: Path to flowgates.csv for re-reading bus pairs.
        topology: Branch topology for bus-pair to branch-index lookup.

    Returns:
        Updated flowgate records with resolved branch indices.
    """
    # Check if resolution is needed
    needs_resolution = any(bid == -1 for fg in flowgates for bid in fg.branch_ids)
    if not needs_resolution:
        return flowgates

    # Build bus-pair to branch index map
    pair_to_idx: dict[tuple[int, int], int] = {}
    for br in topology.branches:
        pair_to_idx[(br.from_bus, br.to_bus)] = br.branch_idx
        pair_to_idx[(br.to_bus, br.from_bus)] = br.branch_idx

    # Re-read the CSV to get the raw bus-pair strings
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    resolved: list[FlowgateRecord] = []
    for i, fg in enumerate(flowgates):
        if all(bid != -1 for bid in fg.branch_ids):
            resolved.append(fg)
            continue

        # Parse bus pairs from the raw CSV
        branches_str = rows[i].get("branches", "")
        parts = [x.strip() for x in branches_str.split(";") if x.strip()]
        new_branch_ids: list[int] = []
        for part in parts:
            if "-" in part:
                nums = part.split("-")
                from_bus = int(nums[0])
                to_bus = int(nums[1])
                idx = pair_to_idx.get((from_bus, to_bus))
                if idx is not None:
                    new_branch_ids.append(idx)
                else:
                    new_branch_ids.append(-1)  # unresolvable
            else:
                try:
                    new_branch_ids.append(int(part))
                except ValueError:
                    new_branch_ids.append(-1)

        resolved.append(
            FlowgateRecord(
                flowgate_id=fg.flowgate_id,
                flowgate_name=fg.flowgate_name,
                branch_ids=new_branch_ids,
                weights=fg.weights,
                limit_mw=fg.limit_mw,
                direction=fg.direction,
            )
        )

    return resolved


# ---------------------------------------------------------------------------
# Scenario data loading
# ---------------------------------------------------------------------------


def load_scenario_multipliers(
    csv_path: Path,
) -> ScenarioMultiplierData:
    """Load scenario multipliers from a wide-format CSV file.

    Handles both Phase 4 schema (separate wind/solar files with columns:
    scenario_id, generator_id, HR_1..HR_24) and Phase 2b schema (combined
    file with columns: scenario, gen_uid, HR_1..HR_24).

    Args:
        csv_path: Path to the scenario multiplier CSV file.

    Returns:
        A ScenarioMultiplierData with parsed multiplier values.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If the CSV does not contain the expected columns.
    """
    if not csv_path.exists():
        msg = f"Scenario multipliers CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            msg = "Scenario multipliers CSV has no header row"
            raise ValueError(msg)
        cols = set(reader.fieldnames)
        rows = list(reader)

    if not rows:
        msg = "Scenario multipliers CSV is empty"
        raise ValueError(msg)

    # Detect scenario ID column
    if "scenario_id" in cols:
        scenario_col = "scenario_id"
    elif "scenario" in cols:
        scenario_col = "scenario"
    else:
        msg = f"No scenario ID column found. Columns: {cols}"
        raise ValueError(msg)

    # Detect generator ID column
    if "generator_id" in cols:
        gen_col = "generator_id"
    elif "gen_uid" in cols:
        gen_col = "gen_uid"
    else:
        msg = f"No generator ID column found. Columns: {cols}"
        raise ValueError(msg)

    # Verify hour columns exist
    missing_hours = [h for h in _HOUR_COLUMNS if h not in cols]
    if missing_hours:
        msg = f"Missing hour columns: {missing_hours}"
        raise ValueError(msg)

    # Collect unique generators (preserving order) and scenarios
    gen_order: list[str] = []
    seen_gens: set[str] = set()
    scenario_ids: set[int] = set()

    for row in rows:
        gen_id = row[gen_col]
        if gen_id not in seen_gens:
            gen_order.append(gen_id)
            seen_gens.add(gen_id)
        scenario_ids.add(int(row[scenario_col]))

    n_scenarios = len(scenario_ids)
    n_generators = len(gen_order)
    gen_id_to_idx = {gid: i for i, gid in enumerate(gen_order)}

    # Build 3-D multiplier array
    multipliers: list[list[list[float]]] = [
        [[0.0] * 24 for _ in range(n_generators)] for _ in range(n_scenarios)
    ]

    for row in rows:
        s_idx = int(row[scenario_col]) - 1  # 1-based to 0-based
        g_idx = gen_id_to_idx[row[gen_col]]
        for h in range(24):
            multipliers[s_idx][g_idx][h] = float(row[_HOUR_COLUMNS[h]])

    # Determine resource type from file name
    name_lower = csv_path.name.lower()
    if "wind" in name_lower:
        resource_type = ResourceType.WIND
    elif "solar" in name_lower:
        resource_type = ResourceType.SOLAR
    else:
        resource_type = ResourceType.WIND  # default for combined files

    # Extract network_id from parent path
    network_id = csv_path.parent.parent.name

    return ScenarioMultiplierData(
        network_id=network_id,
        resource_type=resource_type,
        generator_ids=gen_order,
        pmax_values=[0.0] * n_generators,  # populated later from forecast
        multipliers=multipliers,
        n_scenarios=n_scenarios,
        n_generators=n_generators,
        n_hours=24,
    )


def load_forecast_data(
    network_dir: Path,
    resource_type: ResourceType,
) -> ForecastData:
    """Load forecast and actual profiles for one network and resource type.

    Reads the canonical forecast and actual CSV files from the network
    directory. Extracts generator IDs, Pmax values, and hourly profiles.

    Args:
        network_dir: Path to the network's timeseries directory.
        resource_type: WIND or SOLAR.

    Returns:
        A ForecastData with forecast, actual, and metadata.

    Raises:
        FileNotFoundError: If forecast or actual CSV files are missing.
    """
    forecast_csv = network_dir / f"{resource_type.value}_forecast_24h.csv"
    actual_csv = network_dir / f"{resource_type.value}_actual_24h.csv"

    if not forecast_csv.exists():
        msg = f"Forecast CSV not found: {forecast_csv}"
        raise FileNotFoundError(msg)
    if not actual_csv.exists():
        msg = f"Actual CSV not found: {actual_csv}"
        raise FileNotFoundError(msg)

    forecast_profiles = _load_profile_csv(forecast_csv)
    actual_profiles = _load_profile_csv(actual_csv)

    generator_ids = [p[0] for p in forecast_profiles]
    pmax_values = [p[1] for p in forecast_profiles]
    forecast = [p[2] for p in forecast_profiles]
    actual = [p[2] for p in actual_profiles]

    # Identify nighttime hours for solar
    night_hours: list[int] = []
    if resource_type == ResourceType.SOLAR:
        for h in range(24):
            if all(forecast[g][h] == 0.0 for g in range(len(generator_ids))):
                night_hours.append(h)

    network_id = network_dir.name

    return ForecastData(
        network_id=network_id,
        resource_type=resource_type,
        generator_ids=generator_ids,
        pmax_values=pmax_values,
        forecast=forecast,
        actual=actual,
        night_hours=night_hours,
    )


def _load_profile_csv(
    csv_path: Path,
) -> list[tuple[str, float, list[float]]]:
    """Load profiles from a canonical gen_uid + HR_1..HR_24 CSV.

    Returns:
        List of (gen_uid, pmax_mw, hourly_values) tuples.
    """
    profiles: list[tuple[str, float, list[float]]] = []

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            msg = f"CSV has no header: {csv_path}"
            raise ValueError(msg)

        cols = set(reader.fieldnames)

        for row in reader:
            gen_uid = row["gen_uid"]
            values = [float(row[col]) for col in _HOUR_COLUMNS if col in cols]
            if len(values) < 24:
                msg = f"Expected 24 hour columns, got {len(values)} in {csv_path}"
                raise ValueError(msg)

            # Pmax from explicit column or inferred from max value
            if "pmax_mw" in cols:
                pmax = float(row["pmax_mw"])
            else:
                pmax = max(values) if any(v > 0 for v in values) else 0.0

            profiles.append((gen_uid, pmax, values))

    return profiles


def load_target_correlation_matrix(
    network_id: str,
    resource_type: ResourceType,
    timeseries_dir: Path,
) -> list[list[float]] | None:
    """Load the target rank correlation matrix for a network and resource type.

    For SMALL/MEDIUM: reads from scenarios/rank_correlation_matrix.json.
    For TINY: reads from scenarios/stochastic_metadata.json.

    Args:
        network_id: Network identifier.
        resource_type: WIND or SOLAR.
        timeseries_dir: Base timeseries directory (data/timeseries/).

    Returns:
        A 2-D list of correlation values, or None if not available.
    """
    network_dir = timeseries_dir / network_id

    if network_id == ValidationNetworkId.TINY.value:
        # TINY: correlation is in stochastic_metadata.json
        meta_path = network_dir / "scenarios" / "stochastic_metadata.json"
        if not meta_path.exists():
            logger.warning("TINY stochastic metadata not found: %s", meta_path)
            return None
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        corr_data = meta.get("correlation", {})
        matrix = corr_data.get("matrix")
        if matrix is None:
            logger.warning("No correlation matrix in %s", meta_path)
            return None
        return matrix  # type: ignore[no-any-return]
    else:
        # SMALL/MEDIUM: correlation is in rank_correlation_matrix.json
        # Try network-specific first, then shared
        corr_path = network_dir / "scenarios" / "rank_correlation_matrix.json"
        if not corr_path.exists():
            corr_path = timeseries_dir / "scenarios" / "rank_correlation_matrix.json"
        if not corr_path.exists():
            logger.warning("Correlation matrix not found for %s", network_id)
            return None

        with open(corr_path, encoding="utf-8") as fh:
            corr_data = json.load(fh)

        # The JSON may have per-resource-type sub-blocks or a flat matrix
        if isinstance(corr_data, dict):
            if resource_type.value in corr_data:
                return corr_data[resource_type.value].get("matrix")  # type: ignore[union-attr]
            if "matrix" in corr_data:
                return corr_data["matrix"]  # type: ignore[return-value]
        if isinstance(corr_data, list):
            return corr_data

        return None


# ---------------------------------------------------------------------------
# Flowgate validation checks (a-e)
# ---------------------------------------------------------------------------


def check_flowgate_branch_existence(
    flowgates: list[FlowgateRecord],
    topology: NetworkBranchTopology,
) -> FlowgateCheckResult:
    """Check (a): all flowgate branch IDs exist in the .m branch table.

    Args:
        flowgates: Flowgate records from flowgates.csv.
        topology: Branch topology from the cleaned .m file.

    Returns:
        A FlowgateCheckResult with check_id="a".
    """
    details: list[str] = []
    items_checked = len(flowgates)
    items_failed = 0

    for fg in flowgates:
        for bid in fg.branch_ids:
            if bid not in topology.branch_idx_set:
                details.append(
                    f"Flowgate {fg.flowgate_id}: branch index {bid} not found in "
                    f"branch table (valid range: 1-{len(topology.branches)})"
                )
                items_failed += 1

    status = CheckStatus.PASS if not details else CheckStatus.FAIL
    message = (
        f"All {items_checked} flowgates have valid branch references"
        if not details
        else f"{items_failed} orphaned branch reference(s) found"
    )

    return FlowgateCheckResult(
        check_id="a",
        check_name="Branch existence",
        status=status,
        message=message,
        details=details[:MAX_DETAILS],
        items_checked=items_checked,
        items_passed=items_checked - min(items_failed, items_checked),
        items_failed=min(items_failed, items_checked),
    )


def check_flowgate_limits(
    flowgates: list[FlowgateRecord],
    topology: NetworkBranchTopology,
) -> FlowgateCheckResult:
    """Check (b): MW limits are positive and < sum of branch thermal ratings.

    Args:
        flowgates: Flowgate records from flowgates.csv.
        topology: Branch topology for rate_a lookup.

    Returns:
        A FlowgateCheckResult with check_id="b".
    """
    details: list[str] = []
    items_checked = len(flowgates)
    items_failed = 0

    for fg in flowgates:
        if fg.limit_mw <= 0:
            details.append(
                f"Flowgate {fg.flowgate_id}: limit_mw={fg.limit_mw} is not positive"
            )
            items_failed += 1
            continue

        # Sum of rate_a for constituent branches
        sum_rate_a = sum(
            topology.branch_rate_map.get(bid, 0.0) for bid in fg.branch_ids
        )

        if sum_rate_a > 0 and fg.limit_mw >= sum_rate_a:
            details.append(
                f"Flowgate {fg.flowgate_id}: limit_mw={fg.limit_mw:.1f} >= "
                f"sum_of_rate_a={sum_rate_a:.1f}"
            )
            items_failed += 1

    status = CheckStatus.PASS if not details else CheckStatus.FAIL
    message = (
        f"All {items_checked} flowgates have valid MW limits"
        if not details
        else f"{items_failed} flowgate(s) have invalid MW limits"
    )

    return FlowgateCheckResult(
        check_id="b",
        check_name="MW limit bounds",
        status=status,
        message=message,
        details=details[:MAX_DETAILS],
        items_checked=items_checked,
        items_passed=items_checked - items_failed,
        items_failed=items_failed,
    )


def check_flowgate_weights(
    flowgates: list[FlowgateRecord],
) -> FlowgateCheckResult:
    """Check (c): all weights are nonzero and finite.

    Args:
        flowgates: Flowgate records from flowgates.csv.

    Returns:
        A FlowgateCheckResult with check_id="c".
    """
    details: list[str] = []
    items_checked = len(flowgates)
    items_failed = 0
    flowgates_with_errors: set[str] = set()

    for fg in flowgates:
        for pos, w in enumerate(fg.weights):
            if math.isnan(w):
                details.append(
                    f"Flowgate {fg.flowgate_id}: weight at position {pos} is NaN"
                )
                flowgates_with_errors.add(fg.flowgate_id)
            elif math.isinf(w):
                details.append(
                    f"Flowgate {fg.flowgate_id}: weight at position {pos} is infinite"
                )
                flowgates_with_errors.add(fg.flowgate_id)
            elif abs(w) < 1e-12:
                details.append(
                    f"Flowgate {fg.flowgate_id}: weight at position {pos} is zero"
                )
                flowgates_with_errors.add(fg.flowgate_id)

    items_failed = len(flowgates_with_errors)
    status = CheckStatus.PASS if not details else CheckStatus.FAIL
    message = (
        f"All weights in {items_checked} flowgates are nonzero and finite"
        if not details
        else f"{items_failed} flowgate(s) have invalid weights"
    )

    return FlowgateCheckResult(
        check_id="c",
        check_name="Weight validity",
        status=status,
        message=message,
        details=details[:MAX_DETAILS],
        items_checked=items_checked,
        items_passed=items_checked - items_failed,
        items_failed=items_failed,
    )


def check_flowgate_branch_disjoint(
    flowgates: list[FlowgateRecord],
) -> FlowgateCheckResult:
    """Check (d): no branch appears in more than one flowgate.

    Args:
        flowgates: Flowgate records from flowgates.csv.

    Returns:
        A FlowgateCheckResult with check_id="d".
    """
    details: list[str] = []
    branch_to_flowgate: dict[int, str] = {}
    items_checked = len(flowgates)
    duplicate_branches: set[int] = set()

    for fg in flowgates:
        for bid in fg.branch_ids:
            if bid in branch_to_flowgate:
                other_fg = branch_to_flowgate[bid]
                details.append(
                    f"Branch {bid} appears in both {other_fg} and {fg.flowgate_id}"
                )
                duplicate_branches.add(bid)
            else:
                branch_to_flowgate[bid] = fg.flowgate_id

    items_failed = len(duplicate_branches)
    status = CheckStatus.PASS if not details else CheckStatus.FAIL
    message = (
        f"All branches are disjoint across {items_checked} flowgates"
        if not details
        else f"{items_failed} branch(es) appear in multiple flowgates"
    )

    return FlowgateCheckResult(
        check_id="d",
        check_name="Branch disjointness",
        status=status,
        message=message,
        details=details[:MAX_DETAILS],
        items_checked=items_checked,
        items_passed=items_checked if not details else 0,
        items_failed=items_failed,
    )


def check_flowgate_count(
    flowgates: list[FlowgateRecord],
    config: FlowgateScenarioValidationConfig,
) -> FlowgateCheckResult:
    """Check (e): network has 3-5 flowgates.

    Args:
        flowgates: Flowgate records from flowgates.csv.
        config: Validation configuration with min/max flowgate counts.

    Returns:
        A FlowgateCheckResult with check_id="e".
    """
    n = len(flowgates)
    lo = config.min_flowgates_per_network
    hi = config.max_flowgates_per_network

    if lo <= n <= hi:
        status = CheckStatus.PASS
        message = f"Flowgate count {n} is within [{lo}, {hi}]"
        details: list[str] = []
    elif n < lo:
        status = CheckStatus.FAIL
        message = f"Flowgate count {n} is below minimum {lo}"
        details = [f"Expected at least {lo} flowgates, found {n}"]
    else:
        status = CheckStatus.FAIL
        message = f"Flowgate count {n} exceeds maximum {hi}"
        details = [f"Expected at most {hi} flowgates, found {n}"]

    return FlowgateCheckResult(
        check_id="e",
        check_name="Flowgate count",
        status=status,
        message=message,
        details=details,
        items_checked=1,
        items_passed=1 if status == CheckStatus.PASS else 0,
        items_failed=0 if status == CheckStatus.PASS else 1,
    )


# ---------------------------------------------------------------------------
# Scenario validation checks (f-l)
# ---------------------------------------------------------------------------


def check_scenario_dimensions(
    data: ScenarioMultiplierData,
    config: FlowgateScenarioValidationConfig,
) -> ScenarioCheckResult:
    """Check (f): scenario file has 50 scenarios x 24 hours.

    Args:
        data: Loaded scenario multiplier data.
        config: Validation configuration with expected dimensions.

    Returns:
        A ScenarioCheckResult with check_id="f".
    """
    details: list[str] = []
    if data.n_scenarios != config.expected_n_scenarios:
        details.append(
            f"Expected {config.expected_n_scenarios} scenarios, found {data.n_scenarios}"
        )
    if data.n_hours != config.expected_n_hours:
        details.append(
            f"Expected {config.expected_n_hours} hours, found {data.n_hours}"
        )

    status = CheckStatus.PASS if not details else CheckStatus.FAIL
    message = (
        f"Dimensions correct: {data.n_scenarios} scenarios x {data.n_hours} hours"
        if not details
        else f"Dimension mismatch: {data.n_scenarios} scenarios x {data.n_hours} hours"
    )

    return ScenarioCheckResult(
        check_id="f",
        check_name="Scenario dimensions",
        status=status,
        measured_value=float(data.n_scenarios),
        threshold=float(config.expected_n_scenarios),
        message=message,
        details=details,
        resource_type=data.resource_type,
    )


def check_multiplier_non_negative(
    data: ScenarioMultiplierData,
) -> ScenarioCheckResult:
    """Check (g): all multiplier values are non-negative.

    Args:
        data: Loaded scenario multiplier data.

    Returns:
        A ScenarioCheckResult with check_id="g".
    """
    total_entries = data.n_scenarios * data.n_generators * data.n_hours
    negative_count = 0
    details: list[str] = []

    for s in range(data.n_scenarios):
        for g in range(data.n_generators):
            for h in range(data.n_hours):
                val = data.multipliers[s][g][h]
                if val < 0.0:
                    negative_count += 1
                    if len(details) < MAX_DETAILS:
                        details.append(
                            f"Scenario {s + 1}, generator "
                            f"{data.generator_ids[g]}, hour {h + 1}: "
                            f"multiplier={val:.6f}"
                        )

    fraction = negative_count / total_entries if total_entries > 0 else 0.0
    status = CheckStatus.PASS if negative_count == 0 else CheckStatus.FAIL
    message = (
        f"All {total_entries} multiplier values are non-negative"
        if not details
        else f"{negative_count} negative multiplier(s) ({fraction:.2%})"
    )

    return ScenarioCheckResult(
        check_id="g",
        check_name="Multiplier non-negativity",
        status=status,
        measured_value=fraction,
        threshold=0.0,
        message=message,
        details=details[:MAX_DETAILS],
        resource_type=data.resource_type,
    )


def check_multiplier_pmax_bound(
    data: ScenarioMultiplierData,
    forecast: ForecastData,
    config: FlowgateScenarioValidationConfig,
) -> ScenarioCheckResult:
    """Check (h): no multiplier produces generation > Pmax.

    Args:
        data: Loaded scenario multiplier data.
        forecast: Forecast data with pmax_values.
        config: Validation configuration with Pmax tolerance.

    Returns:
        A ScenarioCheckResult with check_id="h".
    """
    violations = 0
    worst_exceedance = 0.0
    details: list[str] = []

    for s in range(data.n_scenarios):
        for g in range(data.n_generators):
            pmax = forecast.pmax_values[g] if g < len(forecast.pmax_values) else 0.0
            for h in range(data.n_hours):
                forecast_val = (
                    forecast.forecast[g][h] if g < len(forecast.forecast) else 0.0
                )
                realization = forecast_val * data.multipliers[s][g][h]
                exceedance = realization - pmax
                if exceedance > config.pmax_tolerance_mw:
                    violations += 1
                    if exceedance > worst_exceedance:
                        worst_exceedance = exceedance
                    if len(details) < MAX_DETAILS:
                        details.append(
                            f"Scenario {s + 1}, gen "
                            f"{data.generator_ids[g]}, hour {h + 1}: "
                            f"realization={realization:.2f} > "
                            f"Pmax={pmax:.2f} (excess={exceedance:.4f})"
                        )

    status = CheckStatus.PASS if violations == 0 else CheckStatus.FAIL
    message = (
        "No Pmax violations"
        if violations == 0
        else (
            f"{violations} Pmax violation(s), worst exceedance={worst_exceedance:.4f} MW"
        )
    )

    return ScenarioCheckResult(
        check_id="h",
        check_name="Pmax bound",
        status=status,
        measured_value=float(violations),
        threshold=0.0,
        message=message,
        details=details[:MAX_DETAILS],
        resource_type=data.resource_type,
        metadata={"worst_exceedance_mw": worst_exceedance},
    )


def check_ensemble_mean(
    data: ScenarioMultiplierData,
    config: FlowgateScenarioValidationConfig,
) -> ScenarioCheckResult:
    """Check (i): ensemble mean multiplier within 5% of 1.0.

    Args:
        data: Loaded scenario multiplier data.
        config: Validation configuration with ensemble mean tolerance.

    Returns:
        A ScenarioCheckResult with check_id="i".
    """
    # Convert to numpy for efficient mean computation
    arr = np.array(data.multipliers)  # (n_scenarios, n_generators, n_hours)

    # Per-generator mean across scenarios and hours
    per_gen_means: dict[str, float] = {}
    all_vals: list[float] = []
    for g in range(data.n_generators):
        gen_mean = float(np.mean(arr[:, g, :]))
        per_gen_means[data.generator_ids[g]] = gen_mean
        all_vals.append(gen_mean)

    grand_mean = float(np.mean(all_vals)) if all_vals else 1.0

    deviation = abs(grand_mean - 1.0)
    status = (
        CheckStatus.PASS
        if deviation <= config.ensemble_mean_tolerance
        else CheckStatus.FAIL
    )

    details: list[str] = []
    if status == CheckStatus.FAIL:
        for gen_id, gen_mean in per_gen_means.items():
            details.append(f"Generator {gen_id}: mean multiplier = {gen_mean:.6f}")

    message = (
        f"Ensemble mean = {grand_mean:.6f} (within {config.ensemble_mean_tolerance:.0%} of 1.0)"
        if status == CheckStatus.PASS
        else (
            f"Ensemble mean = {grand_mean:.6f} "
            f"(deviation {deviation:.4f} > tolerance {config.ensemble_mean_tolerance})"
        )
    )

    return ScenarioCheckResult(
        check_id="i",
        check_name="Ensemble mean unbiasedness",
        status=status,
        measured_value=grand_mean,
        threshold=config.ensemble_mean_tolerance,
        message=message,
        details=details[:MAX_DETAILS],
        resource_type=data.resource_type,
        metadata={"per_generator_means": per_gen_means},
    )


def check_correlation_fidelity(
    data: ScenarioMultiplierData,
    target_correlation: list[list[float]],
    config: FlowgateScenarioValidationConfig,
) -> ScenarioCheckResult:
    """Check (j): empirical rank correlation matches target.

    Args:
        data: Loaded scenario multiplier data.
        target_correlation: Target rank correlation matrix from D2/D8.
        config: Validation configuration with Frobenius threshold.

    Returns:
        A ScenarioCheckResult with check_id="j".
    """
    if data.n_generators <= 1:
        return ScenarioCheckResult(
            check_id="j",
            check_name="Correlation fidelity",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=config.correlation_frobenius_threshold,
            message="Skipped: single generator (correlation trivially 1.0)",
            details=[],
            resource_type=data.resource_type,
        )

    arr = np.array(data.multipliers)  # (n_scenarios, n_generators, n_hours)
    target = np.array(target_correlation)

    # Handle dimension mismatch between target and data
    n_gen = data.n_generators
    if target.shape[0] != n_gen or target.shape[1] != n_gen:
        # Try to extract sub-block matching the generator count
        if target.shape[0] >= n_gen:
            target = target[:n_gen, :n_gen]
        else:
            return ScenarioCheckResult(
                check_id="j",
                check_name="Correlation fidelity",
                status=CheckStatus.SKIPPED,
                measured_value=None,
                threshold=config.correlation_frobenius_threshold,
                message=(
                    f"Skipped: target correlation matrix size "
                    f"{target.shape} doesn't match {n_gen} generators"
                ),
                details=[],
                resource_type=data.resource_type,
            )

    per_hour_norms: list[float] = []

    for h in range(24):
        hour_data = arr[:, :, h]  # (n_scenarios, n_generators)

        # Compute empirical Spearman rank correlation
        empirical_corr, _ = stats.spearmanr(hour_data)
        if empirical_corr.ndim == 0:
            # Only 2 generators: spearmanr returns a scalar
            empirical_corr = np.array(
                [[1.0, float(empirical_corr)], [float(empirical_corr), 1.0]]
            )

        diff = empirical_corr - target
        frob_norm = float(np.linalg.norm(diff, "fro"))
        per_hour_norms.append(frob_norm)

    avg_frob = float(np.mean(per_hour_norms))

    status = (
        CheckStatus.PASS
        if avg_frob < config.correlation_frobenius_threshold
        else CheckStatus.FAIL
    )

    details: list[str] = []
    if status == CheckStatus.FAIL:
        for h, norm in enumerate(per_hour_norms):
            details.append(f"Hour {h + 1}: Frobenius norm = {norm:.6f}")

    message = (
        f"Average Frobenius norm = {avg_frob:.6f} "
        f"(threshold = {config.correlation_frobenius_threshold})"
    )

    return ScenarioCheckResult(
        check_id="j",
        check_name="Correlation fidelity",
        status=status,
        measured_value=avg_frob,
        threshold=config.correlation_frobenius_threshold,
        message=message,
        details=details[:MAX_DETAILS],
        resource_type=data.resource_type,
        metadata={"per_hour_frobenius_norms": per_hour_norms},
    )


def check_solar_nighttime_zero(
    data: ScenarioMultiplierData,
    forecast: ForecastData,
) -> ScenarioCheckResult:
    """Check (k): solar scenario multipliers are 1.0 at nighttime hours.

    Args:
        data: Loaded scenario multiplier data.
        forecast: Forecast data with nighttime hour classification.

    Returns:
        A ScenarioCheckResult with check_id="k".
    """
    if data.resource_type != ResourceType.SOLAR:
        return ScenarioCheckResult(
            check_id="k",
            check_name="Solar nighttime zero",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=None,
            message="Skipped: not a solar resource",
            details=[],
            resource_type=data.resource_type,
        )

    if not forecast.night_hours:
        return ScenarioCheckResult(
            check_id="k",
            check_name="Solar nighttime zero",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=None,
            message="Skipped: no nighttime hours identified",
            details=[],
            resource_type=data.resource_type,
        )

    violations = 0
    details: list[str] = []
    tolerance = 1e-10

    for s in range(data.n_scenarios):
        for g in range(data.n_generators):
            for h in forecast.night_hours:
                if h >= data.n_hours:
                    continue
                val = data.multipliers[s][g][h]
                if abs(val - 1.0) > tolerance:
                    violations += 1
                    if len(details) < MAX_DETAILS:
                        details.append(
                            f"Scenario {s + 1}, gen "
                            f"{data.generator_ids[g]}, hour {h + 1}: "
                            f"multiplier={val:.6f} (expected 1.0)"
                        )

    status = CheckStatus.PASS if violations == 0 else CheckStatus.FAIL
    message = (
        f"All solar multipliers are 1.0 at nighttime hours {forecast.night_hours}"
        if violations == 0
        else f"{violations} solar nighttime violation(s)"
    )

    return ScenarioCheckResult(
        check_id="k",
        check_name="Solar nighttime zero",
        status=status,
        measured_value=float(violations),
        threshold=0.0,
        message=message,
        details=details[:MAX_DETAILS],
        resource_type=data.resource_type,
    )


def check_forecast_rmse(
    forecast: ForecastData,
    config: FlowgateScenarioValidationConfig,
) -> ScenarioCheckResult:
    """Check (l): forecast RMSE in plausible range.

    Args:
        forecast: Forecast data with forecast, actual, and Pmax arrays.
        config: Validation configuration with RMSE range thresholds.

    Returns:
        A ScenarioCheckResult with check_id="l".
    """
    if forecast.resource_type == ResourceType.WIND:
        rmse_range = config.wind_rmse_pct_range
    else:
        rmse_range = config.solar_rmse_pct_range

    forecast_arr = np.array(forecast.forecast)  # (n_gen, 24)
    actual_arr = np.array(forecast.actual)  # (n_gen, 24)

    # For solar, only use daytime hours
    if forecast.resource_type == ResourceType.SOLAR and forecast.night_hours:
        daytime_mask = np.ones(24, dtype=bool)
        for h in forecast.night_hours:
            if h < 24:
                daytime_mask[h] = False
        forecast_arr = forecast_arr[:, daytime_mask]
        actual_arr = actual_arr[:, daytime_mask]

    if forecast_arr.size == 0:
        return ScenarioCheckResult(
            check_id="l",
            check_name="Forecast RMSE",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=None,
            message="Skipped: no data for RMSE computation",
            details=[],
            resource_type=forecast.resource_type,
        )

    # Compute RMSE
    errors = forecast_arr - actual_arr
    rmse_mw = float(np.sqrt(np.mean(errors**2)))

    # Normalize by total capacity
    total_capacity = sum(forecast.pmax_values)
    if total_capacity <= 0:
        return ScenarioCheckResult(
            check_id="l",
            check_name="Forecast RMSE",
            status=CheckStatus.SKIPPED,
            measured_value=None,
            threshold=None,
            message="Skipped: total capacity is zero",
            details=[],
            resource_type=forecast.resource_type,
        )

    rmse_pct = (rmse_mw / total_capacity) * 100.0

    lo, hi = rmse_range
    status = CheckStatus.PASS if lo <= rmse_pct <= hi else CheckStatus.FAIL

    message = (
        f"RMSE = {rmse_mw:.2f} MW ({rmse_pct:.1f}% of {total_capacity:.1f} MW "
        f"total capacity), expected [{lo:.0f}%, {hi:.0f}%]"
    )

    details: list[str] = []
    if status == CheckStatus.FAIL:
        if rmse_pct < lo:
            details.append(f"RMSE {rmse_pct:.1f}% is below lower bound {lo:.0f}%")
        else:
            details.append(f"RMSE {rmse_pct:.1f}% is above upper bound {hi:.0f}%")

    return ScenarioCheckResult(
        check_id="l",
        check_name="Forecast RMSE",
        status=status,
        measured_value=rmse_pct,
        threshold=None,
        message=message,
        details=details,
        resource_type=forecast.resource_type,
        metadata={
            "rmse_mw": rmse_mw,
            "rmse_pct": rmse_pct,
            "total_capacity_mw": total_capacity,
            "range_lo": lo,
            "range_hi": hi,
        },
    )


# ---------------------------------------------------------------------------
# Per-network orchestration
# ---------------------------------------------------------------------------


def validate_flowgates(
    network_id: str,
    timeseries_dir: Path,
    config: FlowgateScenarioValidationConfig,
) -> list[FlowgateCheckResult]:
    """Run all flowgate validation checks (a-e) for one network.

    Args:
        network_id: Network identifier.
        timeseries_dir: Base timeseries directory (data/timeseries/).
        config: Validation configuration.

    Returns:
        A list of 5 FlowgateCheckResult, one per check (a-e).
    """
    network_dir = timeseries_dir / network_id
    flowgate_csv = network_dir / "flowgates.csv"

    if not flowgate_csv.exists():
        # All checks fail if file is missing
        fail_result = FlowgateCheckResult(
            check_id="?",
            check_name="File existence",
            status=CheckStatus.FAIL,
            message=f"flowgates.csv not found at {flowgate_csv}",
            details=[str(flowgate_csv)],
            items_checked=0,
            items_passed=0,
            items_failed=1,
        )
        return [
            FlowgateCheckResult(
                check_id=cid,
                check_name=fail_result.check_name,
                status=fail_result.status,
                message=fail_result.message,
                details=fail_result.details,
                items_checked=0,
                items_passed=0,
                items_failed=1,
            )
            for cid in ["a", "b", "c", "d", "e"]
        ]

    try:
        topology = load_branch_topology(network_dir, network_id)
    except (FileNotFoundError, ValueError) as exc:
        fail_msg = f"Could not load branch topology: {exc}"
        return [
            FlowgateCheckResult(
                check_id=cid,
                check_name="Topology loading",
                status=CheckStatus.FAIL,
                message=fail_msg,
                details=[str(exc)],
                items_checked=0,
                items_passed=0,
                items_failed=1,
            )
            for cid in ["a", "b", "c", "d", "e"]
        ]

    flowgates = load_flowgates(flowgate_csv)

    # Resolve TINY branch IDs if needed
    flowgates = _resolve_tiny_branch_ids(flowgates, flowgate_csv, topology)

    checks: list[FlowgateCheckResult] = [
        check_flowgate_branch_existence(flowgates, topology),
        check_flowgate_limits(flowgates, topology),
        check_flowgate_weights(flowgates),
        check_flowgate_branch_disjoint(flowgates),
        check_flowgate_count(flowgates, config),
    ]

    return checks


def validate_scenarios(
    network_id: str,
    timeseries_dir: Path,
    config: FlowgateScenarioValidationConfig,
) -> list[ScenarioCheckResult]:
    """Run all scenario validation checks (f-l) for one network.

    Args:
        network_id: Network identifier.
        timeseries_dir: Base timeseries directory (data/timeseries/).
        config: Validation configuration.

    Returns:
        A list of ScenarioCheckResult for all applicable checks.
    """
    network_dir = timeseries_dir / network_id
    scenarios_dir = network_dir / "scenarios"
    results: list[ScenarioCheckResult] = []

    # Determine which scenario files to look for
    if network_id == ValidationNetworkId.TINY.value:
        # TINY: combined file
        multiplier_files = [
            (scenarios_dir / "scenario_multipliers_50x24.csv", None),
        ]
    else:
        # SMALL/MEDIUM: separate per-resource-type files
        multiplier_files = [
            (
                scenarios_dir / "scenario_multipliers_wind_50x24.csv",
                ResourceType.WIND,
            ),
            (
                scenarios_dir / "scenario_multipliers_solar_50x24.csv",
                ResourceType.SOLAR,
            ),
        ]

    for csv_path, explicit_resource_type in multiplier_files:
        if not csv_path.exists():
            # Skip with SKIPPED status
            resource_label = (
                explicit_resource_type.value if explicit_resource_type else "combined"
            )
            skipped = ScenarioCheckResult(
                check_id="f",
                check_name="Scenario dimensions",
                status=CheckStatus.SKIPPED,
                measured_value=None,
                threshold=None,
                message=f"Scenario file not found: {csv_path.name} ({resource_label})",
                details=[],
                resource_type=explicit_resource_type,
            )
            results.append(skipped)
            continue

        try:
            scenario_data = load_scenario_multipliers(csv_path)
        except (ValueError, FileNotFoundError) as exc:
            results.append(
                ScenarioCheckResult(
                    check_id="f",
                    check_name="Scenario loading",
                    status=CheckStatus.FAIL,
                    measured_value=None,
                    threshold=None,
                    message=f"Failed to load scenario data: {exc}",
                    details=[str(exc)],
                    resource_type=explicit_resource_type,
                )
            )
            continue

        # Override resource type if explicitly given
        if explicit_resource_type is not None:
            scenario_data = ScenarioMultiplierData(
                network_id=scenario_data.network_id,
                resource_type=explicit_resource_type,
                generator_ids=scenario_data.generator_ids,
                pmax_values=scenario_data.pmax_values,
                multipliers=scenario_data.multipliers,
                n_scenarios=scenario_data.n_scenarios,
                n_generators=scenario_data.n_generators,
                n_hours=scenario_data.n_hours,
            )

        # For TINY combined file, we run checks for all generators together
        resource_types = (
            [scenario_data.resource_type]
            if explicit_resource_type is not None
            else [ResourceType.WIND, ResourceType.SOLAR]
        )

        for resource_type in resource_types:
            # Load forecast data for this resource type
            try:
                forecast_data = load_forecast_data(network_dir, resource_type)
            except FileNotFoundError:
                results.append(
                    ScenarioCheckResult(
                        check_id="f",
                        check_name="Forecast loading",
                        status=CheckStatus.SKIPPED,
                        measured_value=None,
                        threshold=None,
                        message=(f"Forecast data not found for {resource_type.value}"),
                        details=[],
                        resource_type=resource_type,
                    )
                )
                continue

            # For combined files (TINY), filter to matching generators
            if explicit_resource_type is None:
                # Filter scenario data to only generators matching this resource type
                matching_gen_ids = set(forecast_data.generator_ids)
                gen_indices = [
                    i
                    for i, gid in enumerate(scenario_data.generator_ids)
                    if gid in matching_gen_ids
                ]

                if not gen_indices:
                    continue

                filtered_multipliers = [
                    [
                        [scenario_data.multipliers[s][g][h] for h in range(24)]
                        for g in gen_indices
                    ]
                    for s in range(scenario_data.n_scenarios)
                ]
                filtered_gen_ids = [scenario_data.generator_ids[g] for g in gen_indices]

                filtered_data = ScenarioMultiplierData(
                    network_id=scenario_data.network_id,
                    resource_type=resource_type,
                    generator_ids=filtered_gen_ids,
                    pmax_values=forecast_data.pmax_values,
                    multipliers=filtered_multipliers,
                    n_scenarios=scenario_data.n_scenarios,
                    n_generators=len(gen_indices),
                    n_hours=24,
                )
            else:
                # Update pmax from forecast
                filtered_data = ScenarioMultiplierData(
                    network_id=scenario_data.network_id,
                    resource_type=resource_type,
                    generator_ids=scenario_data.generator_ids,
                    pmax_values=forecast_data.pmax_values,
                    multipliers=scenario_data.multipliers,
                    n_scenarios=scenario_data.n_scenarios,
                    n_generators=scenario_data.n_generators,
                    n_hours=scenario_data.n_hours,
                )

            # Run checks (f) through (l)
            results.append(check_scenario_dimensions(filtered_data, config))
            results.append(check_multiplier_non_negative(filtered_data))
            results.append(
                check_multiplier_pmax_bound(filtered_data, forecast_data, config)
            )
            results.append(check_ensemble_mean(filtered_data, config))

            # Correlation check (j)
            target_corr = load_target_correlation_matrix(
                network_id, resource_type, timeseries_dir
            )
            if target_corr is not None:
                results.append(
                    check_correlation_fidelity(filtered_data, target_corr, config)
                )
            else:
                results.append(
                    ScenarioCheckResult(
                        check_id="j",
                        check_name="Correlation fidelity",
                        status=CheckStatus.SKIPPED,
                        measured_value=None,
                        threshold=config.correlation_frobenius_threshold,
                        message="Skipped: target correlation matrix not available",
                        details=[],
                        resource_type=resource_type,
                    )
                )

            # Solar nighttime (k)
            results.append(check_solar_nighttime_zero(filtered_data, forecast_data))

            # Forecast RMSE (l)
            results.append(check_forecast_rmse(forecast_data, config))

    return results


def validate_network_flowgate_scenario(
    network_id: str,
    timeseries_dir: Path,
    *,
    config: FlowgateScenarioValidationConfig | None = None,
) -> FlowgateScenarioValidationResult:
    """Run all flowgate and scenario checks for a single network.

    Args:
        network_id: Network identifier.
        timeseries_dir: Base timeseries directory (data/timeseries/).
        config: Validation configuration.

    Returns:
        A FlowgateScenarioValidationResult for the network.
    """
    if config is None:
        config = FlowgateScenarioValidationConfig()

    fg_checks = validate_flowgates(network_id, timeseries_dir, config)
    sc_checks = validate_scenarios(network_id, timeseries_dir, config)

    all_statuses = [c.status for c in fg_checks] + [c.status for c in sc_checks]
    total = len(all_statuses)
    passed = sum(1 for s in all_statuses if s == CheckStatus.PASS)
    warned = sum(1 for s in all_statuses if s == CheckStatus.WARN)
    failed = sum(1 for s in all_statuses if s == CheckStatus.FAIL)
    skipped = sum(1 for s in all_statuses if s == CheckStatus.SKIPPED)
    overall_pass = failed == 0

    return FlowgateScenarioValidationResult(
        network_id=network_id,
        flowgate_checks=fg_checks,
        scenario_checks=sc_checks,
        total_checks=total,
        passed=passed,
        warned=warned,
        failed=failed,
        skipped=skipped,
        overall_pass=overall_pass,
    )


# ---------------------------------------------------------------------------
# Report output
# ---------------------------------------------------------------------------


def serialize_results(
    results: list[FlowgateScenarioValidationResult],
) -> dict:
    """Serialize validation results to a JSON-compatible dict.

    Args:
        results: Validation results for all networks.

    Returns:
        A JSON-serializable dict.
    """
    overall_pass = all(r.overall_pass for r in results)

    networks: dict[str, dict] = {}
    for r in results:
        fg_list = [
            {
                "check_id": c.check_id,
                "check_name": c.check_name,
                "status": c.status.value,
                "message": c.message,
                "details": c.details[:MAX_DETAILS],
                "items_checked": c.items_checked,
                "items_passed": c.items_passed,
                "items_failed": c.items_failed,
            }
            for c in r.flowgate_checks
        ]

        sc_list = [
            {
                "check_id": c.check_id,
                "check_name": c.check_name,
                "status": c.status.value,
                "measured_value": c.measured_value,
                "threshold": c.threshold,
                "message": c.message,
                "details": c.details[:MAX_DETAILS],
                "resource_type": (c.resource_type.value if c.resource_type else None),
            }
            for c in r.scenario_checks
        ]

        networks[r.network_id] = {
            "overall_pass": r.overall_pass,
            "flowgate_checks": fg_list,
            "scenario_checks": sc_list,
            "summary": {
                "total": r.total_checks,
                "passed": r.passed,
                "warned": r.warned,
                "failed": r.failed,
                "skipped": r.skipped,
            },
        }

    return {
        "deliverable": "flowgate_scenario_validation",
        "overall_pass": overall_pass,
        "networks": networks,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(
    timeseries_base_dir: Path | None = None,
    *,
    config: FlowgateScenarioValidationConfig | None = None,
) -> list[FlowgateScenarioValidationResult]:
    """Entry point: run flowgate and scenario validation for all networks.

    Args:
        timeseries_base_dir: Base directory for input files. Defaults
            to <repo_root>/data/timeseries/.
        config: Validation configuration.

    Returns:
        A list of FlowgateScenarioValidationResult, one per network.
    """
    if timeseries_base_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        timeseries_base_dir = repo_root / "data" / "timeseries"

    if config is None:
        config = FlowgateScenarioValidationConfig()

    results: list[FlowgateScenarioValidationResult] = []

    for network_id in ValidationNetworkId:
        logger.info("Validating flowgate/scenario for %s...", network_id.value)
        result = validate_network_flowgate_scenario(
            network_id=network_id.value,
            timeseries_dir=timeseries_base_dir,
            config=config,
        )
        results.append(result)
        logger.info(
            "  %s: %d passed, %d warned, %d failed, %d skipped",
            network_id.value,
            result.passed,
            result.warned,
            result.failed,
            result.skipped,
        )

    # Serialize and write
    report = serialize_results(results)
    report_path = timeseries_base_dir / "flowgate_scenario_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    overall = "PASSED" if report["overall_pass"] else "FAILED"
    logger.info("Overall flowgate/scenario validation: %s", overall)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
