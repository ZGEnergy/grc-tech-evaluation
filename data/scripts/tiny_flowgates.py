"""Flowgate Identification & Calibration for TINY (case39).

Identifies congested branches in the IEEE 39-bus case using a simplified DC power
flow approximation implemented in pure Python (numpy/scipy). Analyzes branch flows
at three load levels (peak, shoulder, valley) and groups congested branches into
flowgate definitions for rubric test B-4.

Output artifacts:
  - data/timeseries/case39/flowgates.csv         (flowgate definitions)
  - data/timeseries/case39/flowgate_metadata.json (analysis metadata)
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

from scripts.reconcile_bus_gen import (
    parse_matpower_case,
)

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONGESTION_THRESHOLD: float = 0.80
DERATE_FACTOR: float = 0.95
LOAD_LEVELS: dict[str, float] = {"peak": 1.00, "shoulder": 0.75, "valley": 0.55}
MIN_FLOWGATES: int = 2
MAX_FLOWGATES: int = 8


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchData:
    """Parsed branch record from a MATPOWER .m file."""

    branch_index: int
    from_bus: int
    to_bus: int
    x_pu: float
    rate_a_mw: float


@dataclass(frozen=True)
class BusData:
    """Parsed bus data for DC power flow."""

    bus_id: int
    bus_type: int  # 1=PQ, 2=PV, 3=ref
    pd_mw: float
    qd_mvar: float


@dataclass(frozen=True)
class GenData:
    """Parsed generator data for DC power flow."""

    gen_index: int
    bus_id: int
    pg_mw: float
    pmax_mw: float
    pmin_mw: float


@dataclass(frozen=True)
class BranchFlowResult:
    """Result of branch flow computation for a single branch."""

    branch_index: int
    from_bus: int
    to_bus: int
    flow_mw: float
    rate_a_mw: float
    loading_pct: float  # |flow| / rateA * 100


@dataclass(frozen=True)
class FlowgateDefinition:
    """Definition of a single flowgate."""

    flowgate_id: str  # e.g., "FG_01"
    name: str  # descriptive name
    branches: list[int]  # branch indices
    from_buses: list[int]
    to_buses: list[int]
    weights: list[float]  # weight per branch
    limit_mw: float
    binding_load_level: str  # load level where most congested
    max_loading_pct: float  # peak loading percentage


@dataclass(frozen=True)
class FlowgateResult:
    """Complete result of flowgate identification."""

    flowgates: list[FlowgateDefinition]
    branch_flows: dict[str, list[BranchFlowResult]]  # load_level -> flows
    metadata: dict
    output_csv_path: str
    output_json_path: str


# ---------------------------------------------------------------------------
# MATPOWER .m file parsing (branch data)
# ---------------------------------------------------------------------------


def parse_matpower_case_extended(
    m_file_path: Path,
) -> tuple[list[BusData], list[GenData], list[BranchData], float]:
    """Parse bus, gen, and branch data from a MATPOWER .m file.

    Reuses parse_matpower_case for bus/gen data, then parses the branch matrix
    directly for branch data (from_bus, to_bus, x_pu, rateA).

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        Tuple of (buses, generators, branches, base_mva).
    """
    case_data = parse_matpower_case(m_file_path)

    buses = [
        BusData(
            bus_id=b.bus_id,
            bus_type=b.bus_type,
            pd_mw=b.pd,
            qd_mvar=b.qd,
        )
        for b in case_data.buses
    ]

    gens = [
        GenData(
            gen_index=i,
            bus_id=g.gen_bus,
            pg_mw=g.pg,
            pmax_mw=g.pmax,
            pmin_mw=g.pmin,
        )
        for i, g in enumerate(case_data.generators)
    ]

    branches = _parse_branches(m_file_path)

    return buses, gens, branches, case_data.base_mva


def _parse_branches(m_file_path: Path) -> list[BranchData]:
    """Parse the mpc.branch matrix from a MATPOWER .m file.

    Extracts from_bus (col 0), to_bus (col 1), x_pu (col 3), and rateA (col 5).

    Args:
        m_file_path: Path to the MATPOWER .m file.

    Returns:
        List of BranchData records.
    """
    text = m_file_path.read_text()
    pattern = re.compile(r"mpc\.branch\s*=\s*\[([^\]]*)\]", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        msg = "Could not locate mpc.branch block"
        raise ValueError(msg)

    block = match.group(1)
    branches: list[BranchData] = []
    idx = 0

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
            msg = f"Branch row has {len(float_vals)} columns, expected at least 6"
            raise ValueError(msg)

        branches.append(
            BranchData(
                branch_index=idx,
                from_bus=int(float_vals[0]),
                to_bus=int(float_vals[1]),
                x_pu=float_vals[3],
                rate_a_mw=float_vals[5],
            )
        )
        idx += 1

    return branches


# ---------------------------------------------------------------------------
# Load profile reading
# ---------------------------------------------------------------------------


def load_load_profile(csv_path: Path) -> dict[int, list[float]]:
    """Load bus-level 24h load profile from load_24h.csv.

    Args:
        csv_path: Path to load_24h.csv with columns bus_id, HR_1..HR_24.

    Returns:
        Dict mapping bus_id to list of 24 hourly MW values.
    """
    result: dict[int, list[float]] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            bus_id = int(row["bus_id"])
            hourly = [float(row[f"HR_{h}"]) for h in range(1, 25)]
            result[bus_id] = hourly
    return result


# ---------------------------------------------------------------------------
# DC Power Flow
# ---------------------------------------------------------------------------


def build_b_matrix(
    buses: list[BusData],
    branches: list[BranchData],
    ref_bus_id: int,
    base_mva: float,
) -> tuple[np.ndarray, list[int]]:
    """Build the DC power flow B matrix (bus susceptance matrix).

    Constructs the B matrix from branch reactances, then removes the row and
    column corresponding to the reference bus.

    Args:
        buses: List of bus data.
        branches: List of branch data.
        ref_bus_id: Bus ID of the reference (slack) bus.
        base_mva: System base MVA.

    Returns:
        Tuple of (B_matrix, non_ref_bus_ids) where B_matrix is (n-1, n-1)
        and non_ref_bus_ids lists the bus IDs corresponding to each row/col.
    """
    bus_ids = [b.bus_id for b in buses]
    n = len(bus_ids)
    bus_id_to_idx = {bid: i for i, bid in enumerate(bus_ids)}

    b_full = np.zeros((n, n))

    for br in branches:
        if br.x_pu == 0.0:
            continue  # skip zero-impedance branches (transformers modeled as ideal)
        susceptance = 1.0 / br.x_pu
        i = bus_id_to_idx[br.from_bus]
        j = bus_id_to_idx[br.to_bus]
        b_full[i, i] += susceptance
        b_full[j, j] += susceptance
        b_full[i, j] -= susceptance
        b_full[j, i] -= susceptance

    # Remove reference bus row/col
    ref_idx = bus_id_to_idx[ref_bus_id]
    keep = [i for i in range(n) if i != ref_idx]
    non_ref_bus_ids = [bus_ids[i] for i in keep]

    b_reduced = b_full[np.ix_(keep, keep)]

    return b_reduced, non_ref_bus_ids


def build_ptdf_matrix(
    buses: list[BusData],
    branches: list[BranchData],
    ref_bus_id: int,
    base_mva: float,
) -> tuple[np.ndarray, list[int]]:
    """Build the Power Transfer Distribution Factor (PTDF) matrix.

    PTDF maps bus injections to branch flows. For each branch k connecting
    bus i to bus j with reactance x_k:
        P_branch_k = (theta_i - theta_j) / x_k
    which gives PTDF_k = (1/x_k) * (e_i - e_j)^T * B_inv

    Args:
        buses: List of bus data.
        branches: List of branch data.
        ref_bus_id: Bus ID of the reference bus.
        base_mva: System base MVA.

    Returns:
        Tuple of (PTDF_matrix, non_ref_bus_ids) where PTDF is (n_branch, n_bus-1).
    """
    b_matrix, non_ref_bus_ids = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    n_reduced = len(non_ref_bus_ids)
    bus_id_to_reduced_idx = {bid: i for i, bid in enumerate(non_ref_bus_ids)}

    # Invert B matrix
    b_inv = np.linalg.inv(b_matrix)

    n_branch = len(branches)
    ptdf = np.zeros((n_branch, n_reduced))

    for k, br in enumerate(branches):
        if br.x_pu == 0.0:
            continue
        susceptance = 1.0 / br.x_pu

        # Build (e_i - e_j) vector in reduced space
        diff = np.zeros(n_reduced)
        if br.from_bus in bus_id_to_reduced_idx:
            diff[bus_id_to_reduced_idx[br.from_bus]] = 1.0
        if br.to_bus in bus_id_to_reduced_idx:
            diff[bus_id_to_reduced_idx[br.to_bus]] = -1.0

        # PTDF row for branch k: (1/x_k) * diff^T * B_inv
        ptdf[k, :] = susceptance * (diff @ b_inv)

    return ptdf, non_ref_bus_ids


def dispatch_generators_proportional(
    gens: list[GenData],
    total_load_mw: float,
) -> dict[int, float]:
    """Dispatch generators proportionally to their Pmax to meet total load.

    Distributes the total load across all generators proportionally to each
    generator's Pmax. If a generator's Pmin is nonzero, it is set to at least
    Pmin. The result maps bus_id to total generation at that bus.

    Args:
        gens: List of generator data.
        total_load_mw: Total system load to be served (MW).

    Returns:
        Dict mapping bus_id to total generation (MW) at that bus.
    """
    total_pmax = sum(g.pmax_mw for g in gens)
    if total_pmax <= 0.0:
        msg = "Total Pmax is zero or negative"
        raise ValueError(msg)

    # Proportional dispatch
    bus_gen: dict[int, float] = {}
    for g in gens:
        fraction = g.pmax_mw / total_pmax
        pg = fraction * total_load_mw
        # Clamp to [Pmin, Pmax]
        pg = max(g.pmin_mw, min(g.pmax_mw, pg))
        bus_gen[g.bus_id] = bus_gen.get(g.bus_id, 0.0) + pg

    return bus_gen


def solve_dc_power_flow(
    b_matrix: np.ndarray,
    p_inject: np.ndarray,
) -> np.ndarray:
    """Solve the DC power flow: theta = B_inv * P_inject.

    Uses sparse linear solver for efficiency.

    Args:
        b_matrix: Reduced B matrix (n-1, n-1).
        p_inject: Net bus injections in p.u. (n-1,).

    Returns:
        Bus voltage angles in radians (n-1,).
    """
    b_sparse = csr_matrix(b_matrix)
    theta = spsolve(b_sparse, p_inject)
    return theta


def compute_branch_flows(
    theta: np.ndarray,
    branches: list[BranchData],
    non_ref_bus_ids: list[int],
    ref_bus_id: int,
    base_mva: float,
) -> list[BranchFlowResult]:
    """Compute branch MW flows from bus angles.

    For each branch: P_branch = (theta_from - theta_to) / x_pu * base_mva.
    Positive flow means power flows from from_bus to to_bus.

    Args:
        theta: Bus voltage angles (n-1,) in radians.
        branches: List of branch data.
        non_ref_bus_ids: Bus IDs corresponding to theta entries.
        ref_bus_id: Reference bus ID (angle = 0).
        base_mva: System base MVA.

    Returns:
        List of BranchFlowResult, one per branch.
    """
    bus_id_to_idx = {bid: i for i, bid in enumerate(non_ref_bus_ids)}

    results: list[BranchFlowResult] = []
    for br in branches:
        if br.x_pu == 0.0:
            # Zero-impedance branch (ideal transformer): skip flow calc
            results.append(
                BranchFlowResult(
                    branch_index=br.branch_index,
                    from_bus=br.from_bus,
                    to_bus=br.to_bus,
                    flow_mw=0.0,
                    rate_a_mw=br.rate_a_mw,
                    loading_pct=0.0,
                )
            )
            continue

        # Get angles (ref bus angle = 0)
        theta_from = theta[bus_id_to_idx[br.from_bus]] if br.from_bus != ref_bus_id else 0.0
        theta_to = theta[bus_id_to_idx[br.to_bus]] if br.to_bus != ref_bus_id else 0.0

        flow_pu = (theta_from - theta_to) / br.x_pu
        flow_mw = flow_pu * base_mva

        loading_pct = abs(flow_mw) / br.rate_a_mw * 100.0 if br.rate_a_mw > 0 else 0.0

        results.append(
            BranchFlowResult(
                branch_index=br.branch_index,
                from_bus=br.from_bus,
                to_bus=br.to_bus,
                flow_mw=flow_mw,
                rate_a_mw=br.rate_a_mw,
                loading_pct=loading_pct,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Congestion analysis
# ---------------------------------------------------------------------------


def identify_congested_branches(
    flow_results: list[BranchFlowResult],
    threshold: float = CONGESTION_THRESHOLD,
) -> list[BranchFlowResult]:
    """Identify branches where loading >= threshold * 100%.

    Args:
        flow_results: Branch flow results from compute_branch_flows.
        threshold: Congestion threshold as a fraction (e.g. 0.80 = 80%).

    Returns:
        List of BranchFlowResult for branches at or above the threshold.
    """
    threshold_pct = threshold * 100.0
    return [r for r in flow_results if r.loading_pct >= threshold_pct]


def group_into_flowgates(
    congested: list[BranchFlowResult],
    branches: list[BranchData],
) -> list[list[BranchFlowResult]]:
    """Group congested branches into flowgates by adjacency.

    Two branches are adjacent if they share a common bus. Adjacent congested
    branches are grouped into a single multi-branch flowgate. Isolated
    congested branches form single-branch flowgates.

    Uses union-find to group adjacent branches.

    Args:
        congested: List of congested branch flow results.
        branches: All branch data (for topology reference).

    Returns:
        List of groups, where each group is a list of BranchFlowResult.
    """
    if not congested:
        return []

    n = len(congested)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Build bus-to-congested-branch-index mapping
    bus_to_indices: dict[int, list[int]] = {}
    for i, br in enumerate(congested):
        for bus_id in (br.from_bus, br.to_bus):
            if bus_id not in bus_to_indices:
                bus_to_indices[bus_id] = []
            bus_to_indices[bus_id].append(i)

    # Union branches sharing a bus
    for indices in bus_to_indices.values():
        for j in range(1, len(indices)):
            union(indices[0], indices[j])

    # Collect groups
    groups: dict[int, list[BranchFlowResult]] = {}
    for i, br in enumerate(congested):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(br)

    return list(groups.values())


def compute_flowgate_limits(
    group: list[BranchFlowResult],
    derate_factor: float = DERATE_FACTOR,
) -> float:
    """Compute the MW limit for a flowgate group.

    Limit = min(rateA across branches in group) * derate_factor.

    Args:
        group: List of branch flow results in this flowgate.
        derate_factor: Derate factor applied to the minimum rateA.

    Returns:
        Flowgate limit in MW.
    """
    min_rate_a = min(br.rate_a_mw for br in group)
    return min_rate_a * derate_factor


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------


def _make_flowgate_definitions(
    groups: list[list[BranchFlowResult]],
    branches: list[BranchData],
    all_level_flows: dict[str, list[BranchFlowResult]],
    derate_factor: float = DERATE_FACTOR,
) -> list[FlowgateDefinition]:
    """Convert flowgate groups into FlowgateDefinition records.

    Args:
        groups: Groups of congested branches.
        branches: All branch data.
        all_level_flows: Branch flows at each load level.
        derate_factor: Derate factor for limit computation.

    Returns:
        List of FlowgateDefinition records.
    """
    # Build branch index to BranchData map
    branch_map = {br.branch_index: br for br in branches}

    definitions: list[FlowgateDefinition] = []
    for fg_num, group in enumerate(groups, start=1):
        branch_indices = sorted(br.branch_index for br in group)
        from_buses = [branch_map[idx].from_bus for idx in branch_indices]
        to_buses = [branch_map[idx].to_bus for idx in branch_indices]
        weights = [1.0] * len(branch_indices)
        limit_mw = compute_flowgate_limits(group, derate_factor)

        # Find which load level has the highest loading for this flowgate
        best_level = "peak"
        best_loading = 0.0
        for level, flows in all_level_flows.items():
            flow_map = {f.branch_index: f for f in flows}
            max_loading = max(
                (flow_map[idx].loading_pct for idx in branch_indices if idx in flow_map),
                default=0.0,
            )
            if max_loading > best_loading:
                best_loading = max_loading
                best_level = level

        # Build descriptive name from bus pairs
        bus_pairs = [f"{f}-{t}" for f, t in zip(from_buses, to_buses)]
        name = f"FG_{fg_num:02d}_{'_'.join(bus_pairs)}"

        definitions.append(
            FlowgateDefinition(
                flowgate_id=f"FG_{fg_num:02d}",
                name=name,
                branches=branch_indices,
                from_buses=from_buses,
                to_buses=to_buses,
                weights=weights,
                limit_mw=limit_mw,
                binding_load_level=best_level,
                max_loading_pct=best_loading,
            )
        )

    return definitions


def write_flowgates_csv(flowgates: list[FlowgateDefinition], dest_path: Path) -> None:
    """Write flowgate definitions to CSV.

    Columns: flowgate_id, name, branches, weights, limit_mw,
    binding_load_level, max_loading_pct.

    The 'branches' column uses semicolon-delimited branch indices (from_bus-to_bus).
    The 'weights' column uses semicolon-delimited float values.

    Args:
        flowgates: List of flowgate definitions.
        dest_path: Output CSV path.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "flowgate_id",
        "name",
        "branches",
        "weights",
        "limit_mw",
        "binding_load_level",
        "max_loading_pct",
    ]

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for fg in flowgates:
            branch_strs = [f"{fb}-{tb}" for fb, tb in zip(fg.from_buses, fg.to_buses)]
            branches_str = ";".join(branch_strs)
            weights_str = ";".join(f"{w:.2f}" for w in fg.weights)
            writer.writerow(
                [
                    fg.flowgate_id,
                    fg.name,
                    branches_str,
                    weights_str,
                    f"{fg.limit_mw:.2f}",
                    fg.binding_load_level,
                    f"{fg.max_loading_pct:.2f}",
                ]
            )


def write_flowgate_metadata(
    result: FlowgateResult,
    dest_path: Path,
) -> None:
    """Write flowgate analysis metadata to JSON.

    Args:
        result: Complete flowgate result.
        dest_path: Output JSON path.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "script_version": __version__,
        "congestion_threshold": CONGESTION_THRESHOLD,
        "derate_factor": DERATE_FACTOR,
        "load_levels": LOAD_LEVELS,
        "num_flowgates": len(result.flowgates),
        "flowgates": [asdict(fg) for fg in result.flowgates],
        "branch_flow_summary": {
            level: {
                "num_branches": len(flows),
                "max_loading_pct": max((f.loading_pct for f in flows), default=0.0),
                "num_congested": sum(
                    1 for f in flows if f.loading_pct >= CONGESTION_THRESHOLD * 100
                ),
            }
            for level, flows in result.branch_flows.items()
        },
    }

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main(
    m_file_path: Path | None = None,
    load_csv_path: Path | None = None,
    output_dir: Path | None = None,
    congestion_threshold: float = CONGESTION_THRESHOLD,
    derate_factor: float = DERATE_FACTOR,
) -> FlowgateResult:
    """Entry point: identify flowgates and write output artifacts.

    Args:
        m_file_path: Path to the cleaned case39.m file. Defaults to
            <repo_root>/data/timeseries/case39/case39.m.
        load_csv_path: Path to load_24h.csv. Defaults to
            <repo_root>/data/timeseries/case39/load_24h.csv.
        output_dir: Directory for output files. Defaults to
            <repo_root>/data/timeseries/case39/.
        congestion_threshold: Fraction of rateA for congestion (default 0.80).
        derate_factor: Derate applied to flowgate limits (default 0.95).

    Returns:
        A FlowgateResult with all flowgate definitions and analysis data.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if m_file_path is None:
        m_file_path = repo_root / "timeseries" / "case39" / "case39.m"
    if load_csv_path is None:
        load_csv_path = repo_root / "timeseries" / "case39" / "load_24h.csv"
    if output_dir is None:
        output_dir = repo_root / "timeseries" / "case39"

    # Parse case data
    buses, gens, branches, base_mva = parse_matpower_case_extended(m_file_path)

    # Find reference bus
    ref_bus_id = next(b.bus_id for b in buses if b.bus_type == 3)

    # Load the 24h load profile to determine system peak
    load_profile = load_load_profile(load_csv_path)
    # System peak = sum of all bus peak loads (HR with max total)
    hourly_totals = [sum(load_profile[bus_id][h] for bus_id in load_profile) for h in range(24)]
    system_peak_mw = max(hourly_totals)

    # Build B matrix and PTDF
    b_matrix, non_ref_bus_ids = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    bus_id_to_reduced_idx = {bid: i for i, bid in enumerate(non_ref_bus_ids)}

    # Analyze at each load level
    all_level_flows: dict[str, list[BranchFlowResult]] = {}
    all_congested: dict[str, list[BranchFlowResult]] = {}

    for level_name, scale_factor in LOAD_LEVELS.items():
        total_load = system_peak_mw * scale_factor

        # Compute bus loads at this level
        bus_loads: dict[int, float] = {}
        for bus_id, hourly in load_profile.items():
            peak_hr_idx = hourly_totals.index(max(hourly_totals))
            bus_loads[bus_id] = hourly[peak_hr_idx] * scale_factor

        # Dispatch generators
        gen_dispatch = dispatch_generators_proportional(gens, total_load)

        # Build net injection vector (generation - load) in p.u.
        n_reduced = len(non_ref_bus_ids)
        p_inject = np.zeros(n_reduced)
        for bus_id in non_ref_bus_ids:
            idx = bus_id_to_reduced_idx[bus_id]
            gen_at_bus = gen_dispatch.get(bus_id, 0.0)
            load_at_bus = bus_loads.get(bus_id, 0.0)
            p_inject[idx] = (gen_at_bus - load_at_bus) / base_mva

        # Solve DC power flow
        theta = solve_dc_power_flow(b_matrix, p_inject)

        # Compute branch flows
        flows = compute_branch_flows(theta, branches, non_ref_bus_ids, ref_bus_id, base_mva)
        all_level_flows[level_name] = flows

        # Identify congested branches
        congested = identify_congested_branches(flows, congestion_threshold)
        all_congested[level_name] = congested

    # Merge congested branches across all load levels and find flowgates.
    # If the initial threshold doesn't yield enough flowgates, progressively
    # lower it (by 0.05 steps) until we reach MIN_FLOWGATES or a floor of 0.40.
    effective_threshold = congestion_threshold
    groups: list[list[BranchFlowResult]] = []

    while effective_threshold >= 0.40:
        all_congested_indices: set[int] = set()
        best_loading_per_branch: dict[int, tuple[float, str]] = {}

        for level_name, flows in all_level_flows.items():
            congested = identify_congested_branches(flows, effective_threshold)
            for br in congested:
                all_congested_indices.add(br.branch_index)
                current = best_loading_per_branch.get(br.branch_index, (0.0, ""))
                if br.loading_pct > current[0]:
                    best_loading_per_branch[br.branch_index] = (
                        br.loading_pct,
                        level_name,
                    )

        # Get the best flow result for each congested branch
        merged_congested: list[BranchFlowResult] = []
        for br_idx in sorted(all_congested_indices):
            best_level = best_loading_per_branch[br_idx][1]
            for flow in all_level_flows[best_level]:
                if flow.branch_index == br_idx:
                    merged_congested.append(flow)
                    break

        # Group into flowgates
        groups = group_into_flowgates(merged_congested, branches)

        if len(groups) >= MIN_FLOWGATES:
            break

        effective_threshold -= 0.05

    # Create flowgate definitions
    flowgates = _make_flowgate_definitions(groups, branches, all_level_flows, derate_factor)

    # Build output paths
    csv_path = output_dir / "flowgates.csv"
    json_path = output_dir / "flowgate_metadata.json"

    result = FlowgateResult(
        flowgates=flowgates,
        branch_flows=all_level_flows,
        metadata={
            "congestion_threshold": congestion_threshold,
            "derate_factor": derate_factor,
            "load_levels": LOAD_LEVELS,
            "system_peak_mw": system_peak_mw,
        },
        output_csv_path=str(csv_path),
        output_json_path=str(json_path),
    )

    # Write outputs
    write_flowgates_csv(flowgates, csv_path)
    write_flowgate_metadata(result, json_path)

    return result


if __name__ == "__main__":
    main()
