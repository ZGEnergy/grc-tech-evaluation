"""Flowgate Definition & Calibration for SMALL (ACTIVSg2000) and MEDIUM (ACTIVSg10k) networks.

Consumes the congestion analysis output from Phase 3 Deliverable 5 (DC OPF Congestion
Analysis) -- specifically the clustered corridor groups and per-branch utilization data
at peak, shoulder, and valley load levels -- and transforms them into complete flowgate
definitions with calibrated limits.

For each network, 3-5 flowgates are selected from the top congested corridors. Weights
are derived from DC OPF flow distribution. Limits are set at 95% of the maximum observed
weighted flow sum across load levels.

Output artifacts per network:
  - data/timeseries/<network>/flowgates.csv
  - data/timeseries/<network>/flowgate_calibration/flowgate_narrative.md
  - data/timeseries/<network>/flowgate_calibration/flowgate_definition_log.json
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.dcopf_congestion import (
    BranchLoading,
    CongestedCorridor,
    CongestionCandidate,
    CongestionNetworkId,
    LoadLevel,
    parse_branch_loading_csv,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FLOWGATE_LIMIT_FACTOR: float = 0.95
"""Derating factor applied to the maximum observed weighted flow.

The flowgate MW limit is set to 95% of the binding weighted flow sum
observed in DC OPF, providing margin for AC/DC model divergence.
Consistent with Phase 2b PRD-07.
"""

MIN_FLOWGATES: int = 3
"""Minimum number of flowgates to define per network."""

MAX_FLOWGATES: int = 5
"""Maximum number of flowgates to define per network.

The phase plan specifies 3-5 flowgates per network.
"""

SINGLE_BRANCH_WEIGHT: float = 1.0
"""Weight for a branch in a single-branch flowgate. Always 1.0."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class FlowgateDirection(StrEnum):
    """Direction convention for flowgate monitoring.

    Consistent with Phase 2b PRD-07 FlowgateDirection.
    """

    FORWARD = "forward"  # flow in the from-bus -> to-bus direction
    BOTH = "both"  # absolute flow monitored (bidirectional)


@dataclass(frozen=True)
class FlowgateBranch:
    """A single branch within a flowgate definition.

    Pairs the branch index with its weight in the linear combination.
    For single-branch flowgates, weight is always 1.0.
    For multi-branch flowgates, weight is normalized so the highest-flow
    branch has weight 1.0 and others reflect relative flow contribution.

    Consistent with Phase 2b PRD-07 FlowgateBranch.
    """

    branch_idx: int  # 1-based index into mpc.branch matrix
    from_bus: int
    to_bus: int
    weight: float  # normalized relative flow contribution


@dataclass(frozen=True)
class FlowgateDefinition:
    """Complete definition of a single flowgate.

    A flowgate monitors the weighted sum of branch flows:
        flowgate_flow = sum(weight_i * flow_i for i in branches)
    and enforces flowgate_flow <= limit_mw.

    For single-branch flowgates, this reduces to flow_1 <= limit_mw.
    For multi-branch flowgates, it monitors a parallel-path corridor.

    Consistent with Phase 2b PRD-07 FlowgateDefinition.
    """

    flowgate_id: str  # e.g., "FG_1", "FG_2" (1-based, ordered by severity)
    flowgate_name: str  # descriptive, e.g., "Bus100-Bus200_Bus100-Bus300 corridor"
    branches: list[FlowgateBranch]  # constituent branches with weights
    limit_mw: float  # MW limit (95% of max observed weighted flow)
    direction: FlowgateDirection
    calibration_load_level: str  # LoadLevel value at which binding flow occurred
    max_observed_flow_mw: float  # binding weighted flow before 95% derating


@dataclass(frozen=True)
class FlowgateWeight:
    """Intermediate result: computed weight for one branch in a multi-branch flowgate.

    Used during the weight computation step before constructing FlowgateBranch.
    """

    branch_idx: int  # 1-based
    from_bus: int
    to_bus: int
    flow_mw: float  # absolute flow at binding load level
    raw_weight: float  # flow_mw / max_flow_in_corridor
    normalized_weight: float  # raw_weight (max branch = 1.0)


@dataclass(frozen=True)
class FlowgateCalibrationResult:
    """Complete result of the flowgate definition pipeline for one network.

    Bundles the flowgate definitions, source corridor data, and output paths.
    """

    network_id: str  # CongestionNetworkId value ("ACTIVSg2000" or "ACTIVSg10k")
    flowgates: list[FlowgateDefinition]  # 3-5 flowgate definitions
    selected_corridor_count: int  # corridors selected (3-5)
    total_corridor_count: int  # total corridors from D5
    excluded_corridor_count: int  # corridors not selected (logged)
    flowgates_csv_path: str  # relative path to flowgates.csv
    narrative_path: str  # relative path to flowgate_narrative.md
    calibration_log_json_path: str  # relative path to flowgate_definition_log.json


@dataclass(frozen=True)
class FlowgateNarrativeEntry:
    """Human-readable description of one flowgate for the calibration narrative.

    Used to generate the markdown narrative document.
    """

    flowgate_id: str
    flowgate_name: str
    branch_count: int
    branch_descriptions: list[str]  # "Branch 42: bus 100 -> bus 200, weight=1.00"
    limit_mw: float
    max_observed_flow_mw: float
    derating_factor: float  # 0.95
    calibration_load_level: str
    direction: str
    physical_interpretation: str  # "Monitors the parallel-path corridor between ..."


# ---------------------------------------------------------------------------
# Corridor loading
# ---------------------------------------------------------------------------


def load_congestion_candidates_csv(
    csv_path: Path,
) -> list[CongestionCandidate]:
    """Parse the congestion_candidates.csv output from D5.

    Reads the CSV produced by Phase 3 D5 and returns CongestionCandidate
    records with corridor_group_id assignments.

    Expected columns: branch_idx, from_bus, to_bus, rate_a_mw,
    utilization_peak, utilization_shoulder, utilization_valley,
    max_utilization, binding_load_level, corridor_group_id.

    Args:
        csv_path: Path to congestion_candidates.csv.

    Returns:
        A list of CongestionCandidate, ordered by max_utilization descending.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If the CSV has unexpected columns or missing corridor IDs.
    """
    if not csv_path.exists():
        msg = f"Congestion candidates CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    candidates: list[CongestionCandidate] = []

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        expected_cols = {
            "branch_idx",
            "from_bus",
            "to_bus",
            "rate_a_mw",
            "utilization_peak",
            "utilization_shoulder",
            "utilization_valley",
            "max_utilization",
            "binding_load_level",
            "corridor_group_id",
        }
        if reader.fieldnames is None:
            msg = "CSV file has no header row"
            raise ValueError(msg)
        actual_cols = set(reader.fieldnames)
        missing = expected_cols - actual_cols
        if missing:
            msg = f"Missing columns in congestion candidates CSV: {missing}"
            raise ValueError(msg)

        for row in reader:
            corridor_id_str = row["corridor_group_id"]
            corridor_id = int(corridor_id_str) if corridor_id_str else None

            binding_level_str = row["binding_load_level"]
            binding_level = LoadLevel(binding_level_str)

            candidates.append(
                CongestionCandidate(
                    branch_idx=int(row["branch_idx"]),
                    from_bus=int(row["from_bus"]),
                    to_bus=int(row["to_bus"]),
                    rate_a_mw=float(row["rate_a_mw"]),
                    utilization_peak=float(row["utilization_peak"]),
                    utilization_shoulder=float(row["utilization_shoulder"]),
                    utilization_valley=float(row["utilization_valley"]),
                    max_utilization=float(row["max_utilization"]),
                    binding_load_level=binding_level,
                    corridor_group_id=corridor_id,
                )
            )

    candidates.sort(key=lambda c: c.max_utilization, reverse=True)
    return candidates


def load_branch_loading_csv(
    csv_path: Path,
) -> list[BranchLoading]:
    """Parse a branch_loading CSV from D5 for flow values at one load level.

    Delegates to the D5 parse_branch_loading_csv function for consistency.

    Args:
        csv_path: Path to branch_loading_<level>.csv.

    Returns:
        A list of BranchLoading, ordered by branch_idx ascending.

    Raises:
        FileNotFoundError: If csv_path does not exist.
    """
    return parse_branch_loading_csv(csv_path)


def reconstruct_corridors(
    candidates: list[CongestionCandidate],
) -> list[CongestedCorridor]:
    """Reconstruct corridor groups from candidate records with corridor_group_id.

    Groups CongestionCandidate records by their corridor_group_id field
    and constructs CongestedCorridor objects. This avoids re-running
    the union-find clustering from D5 -- the corridor assignments are
    read directly from the CSV.

    Corridors are returned sorted by max_utilization descending
    (most congested corridor first).

    Args:
        candidates: CongestionCandidate records with corridor_group_id set.

    Returns:
        A list of CongestedCorridor, sorted by max_utilization descending.

    Raises:
        ValueError: If any candidate has corridor_group_id = None.
    """
    # Validate no None corridor IDs
    for c in candidates:
        if c.corridor_group_id is None:
            msg = (
                f"Candidate branch {c.branch_idx} (bus {c.from_bus}->{c.to_bus}) "
                f"has corridor_group_id=None"
            )
            raise ValueError(msg)

    # Group by corridor_group_id
    groups: dict[int, list[CongestionCandidate]] = {}
    for c in candidates:
        gid = c.corridor_group_id
        assert gid is not None  # already validated above
        if gid not in groups:
            groups[gid] = []
        groups[gid].append(c)

    corridors: list[CongestedCorridor] = []
    for corridor_id, branches in groups.items():
        # Find shared buses (buses that appear in more than one branch)
        bus_counts: dict[int, int] = {}
        for b in branches:
            bus_counts[b.from_bus] = bus_counts.get(b.from_bus, 0) + 1
            bus_counts[b.to_bus] = bus_counts.get(b.to_bus, 0) + 1
        shared = sorted(bus_id for bus_id, count in bus_counts.items() if count > 1)

        max_util = max(b.max_utilization for b in branches)
        # Determine binding load level from the branch with highest utilization
        binding_branch = max(branches, key=lambda b: b.max_utilization)

        corridors.append(
            CongestedCorridor(
                corridor_id=corridor_id,
                branches=branches,
                shared_buses=shared,
                max_utilization=max_util,
                binding_load_level=binding_branch.binding_load_level,
                branch_count=len(branches),
            )
        )

    corridors.sort(key=lambda c: c.max_utilization, reverse=True)
    return corridors


# ---------------------------------------------------------------------------
# Corridor selection
# ---------------------------------------------------------------------------


def select_flowgate_corridors(
    corridors: list[CongestedCorridor],
    min_flowgates: int = MIN_FLOWGATES,
    max_flowgates: int = MAX_FLOWGATES,
) -> tuple[list[CongestedCorridor], list[CongestedCorridor]]:
    """Select the top corridors to become flowgates.

    Takes the sorted corridor list from reconstruct_corridors and
    selects the top max_flowgates corridors by max_utilization. If
    fewer than min_flowgates corridors exist, all are selected and
    a warning is logged.

    Args:
        corridors: Corridors sorted by max_utilization descending.
        min_flowgates: Minimum desired flowgate count (default 3).
        max_flowgates: Maximum flowgate count (default 5).

    Returns:
        A tuple of (selected_corridors, excluded_corridors).
        selected_corridors has length min(len(corridors), max_flowgates).
        excluded_corridors contains the remaining corridors.

    Raises:
        ValueError: If corridors is empty (no congestion found by D5).
    """
    if not corridors:
        msg = "No congestion corridors available for flowgate selection"
        raise ValueError(msg)

    if len(corridors) < min_flowgates:
        logger.warning(
            "Only %d corridors available, fewer than minimum %d",
            len(corridors),
            min_flowgates,
        )

    selected = corridors[:max_flowgates]
    excluded = corridors[max_flowgates:]

    if excluded:
        logger.info(
            "Selected %d corridors, excluded %d (beyond max_flowgates=%d)",
            len(selected),
            len(excluded),
            max_flowgates,
        )

    return selected, excluded


# ---------------------------------------------------------------------------
# Weight computation
# ---------------------------------------------------------------------------


def compute_flowgate_weights(
    corridor: CongestedCorridor,
    branch_loadings: dict[str, list[BranchLoading]],
) -> list[FlowgateWeight]:
    """Compute normalized weights for branches in a multi-branch corridor.

    For the corridor's binding load level, retrieves the absolute flow
    for each constituent branch from the branch_loadings dict. Weights
    are normalized so the branch with the highest absolute flow has
    weight 1.0, and other branches have weight = flow / max_flow.

    For single-branch corridors, the single branch gets weight 1.0.

    Args:
        corridor: A CongestedCorridor from select_flowgate_corridors.
        branch_loadings: Dict mapping LoadLevel string to the list of
            BranchLoading records for that level (from D5 CSV output).

    Returns:
        A list of FlowgateWeight, one per branch in the corridor,
        sorted by branch_idx ascending.

    Raises:
        KeyError: If the binding load level is not found in branch_loadings.
        ValueError: If a corridor branch is not found in the branch loading data.
        ValueError: If all branch flows are zero at the binding level.
    """
    binding_level = corridor.binding_load_level.value

    if binding_level not in branch_loadings:
        msg = f"Binding load level '{binding_level}' not found in branch_loadings"
        raise KeyError(msg)

    # Build lookup: branch_idx -> BranchLoading for the binding level
    level_data = branch_loadings[binding_level]
    loading_map: dict[int, BranchLoading] = {bl.branch_idx: bl for bl in level_data}

    # Get flows for corridor branches
    branch_flows: list[tuple[CongestionCandidate, float]] = []
    for branch in corridor.branches:
        if branch.branch_idx not in loading_map:
            msg = (
                f"Branch {branch.branch_idx} (bus {branch.from_bus}->{branch.to_bus}) "
                f"not found in branch loading data for level '{binding_level}'"
            )
            raise ValueError(msg)
        bl = loading_map[branch.branch_idx]
        branch_flows.append((branch, abs(bl.flow_mw)))

    # Find max flow for normalization
    max_flow = max(flow for _, flow in branch_flows)
    if max_flow == 0.0:
        msg = (
            f"All branch flows are zero at binding level '{binding_level}' "
            f"for corridor {corridor.corridor_id}"
        )
        raise ValueError(msg)

    # Compute normalized weights
    weights: list[FlowgateWeight] = []
    for branch, flow in branch_flows:
        raw_weight = flow / max_flow
        weights.append(
            FlowgateWeight(
                branch_idx=branch.branch_idx,
                from_bus=branch.from_bus,
                to_bus=branch.to_bus,
                flow_mw=flow,
                raw_weight=raw_weight,
                normalized_weight=raw_weight,  # max branch = 1.0
            )
        )

    weights.sort(key=lambda w: w.branch_idx)
    return weights


def compute_weighted_flow_sum(
    weights: list[FlowgateWeight],
    branch_loadings: list[BranchLoading],
) -> float:
    """Compute the weighted flow sum for a flowgate at one load level.

    Calculates sum(weight_i * |flow_i|) for the branches in the flowgate
    using the provided branch loading data.

    Args:
        weights: FlowgateWeight records for the flowgate's branches.
        branch_loadings: Full branch loading list for one load level.

    Returns:
        The weighted flow sum in MW.

    Raises:
        ValueError: If any weight branch is not found in branch_loadings.
    """
    loading_map: dict[int, BranchLoading] = {bl.branch_idx: bl for bl in branch_loadings}

    total = 0.0
    for w in weights:
        if w.branch_idx not in loading_map:
            msg = f"Branch {w.branch_idx} not found in branch loading data"
            raise ValueError(msg)
        bl = loading_map[w.branch_idx]
        total += w.normalized_weight * abs(bl.flow_mw)

    return total


def compute_max_weighted_flow(
    weights: list[FlowgateWeight],
    branch_loadings: dict[str, list[BranchLoading]],
) -> tuple[float, str]:
    """Find the maximum weighted flow sum across all three load levels.

    Calls compute_weighted_flow_sum for each load level and returns
    the maximum value and the load level at which it occurs.

    Args:
        weights: FlowgateWeight records for the flowgate's branches.
        branch_loadings: Dict mapping LoadLevel string to branch loading list.

    Returns:
        A tuple of (max_weighted_flow_mw, binding_load_level_str).
    """
    max_flow = 0.0
    max_level = ""

    for level_str, loadings in branch_loadings.items():
        flow_sum = compute_weighted_flow_sum(weights, loadings)
        if flow_sum > max_flow:
            max_flow = flow_sum
            max_level = level_str

    return max_flow, max_level


# ---------------------------------------------------------------------------
# Flowgate name generation
# ---------------------------------------------------------------------------


def generate_flowgate_name(
    corridor: CongestedCorridor,
) -> str:
    """Generate a descriptive name for a flowgate from its corridor topology.

    For single-branch corridors:
        "Bus<from>-Bus<to>"
    For multi-branch corridors:
        "Corridor_<from1>-<to1>_<from2>-<to2>_..."

    Branch pairs are listed in branch_idx order. Names are truncated
    to 80 characters with ellipsis if necessary.

    Args:
        corridor: The corridor to name.

    Returns:
        A human-readable flowgate name string.
    """
    sorted_branches = sorted(corridor.branches, key=lambda b: b.branch_idx)

    if len(sorted_branches) == 1:
        b = sorted_branches[0]
        return f"Bus{b.from_bus}-Bus{b.to_bus}"

    pairs = [f"{b.from_bus}-{b.to_bus}" for b in sorted_branches]
    name = "Corridor_" + "_".join(pairs)

    if len(name) > 80:
        name = name[:77] + "..."

    return name


# ---------------------------------------------------------------------------
# Flowgate definition
# ---------------------------------------------------------------------------


def define_single_flowgate(
    corridor: CongestedCorridor,
    flowgate_index: int,
    branch_loadings: dict[str, list[BranchLoading]],
    limit_factor: float = FLOWGATE_LIMIT_FACTOR,
) -> FlowgateDefinition:
    """Define a single flowgate from a congested corridor.

    Orchestrates the full definition for one corridor:
    1. Computes weights via compute_flowgate_weights.
    2. Computes max weighted flow across load levels.
    3. Applies the 95% derating factor to get limit_mw.
    4. Constructs FlowgateBranch records from the weights.
    5. Generates a descriptive flowgate_name from the bus pairs.
    6. Returns a complete FlowgateDefinition.

    The flowgate_id is "FG_<flowgate_index>" (1-based).

    Args:
        corridor: The CongestedCorridor to convert to a flowgate.
        flowgate_index: 1-based index for the flowgate_id.
        branch_loadings: Dict mapping LoadLevel string to branch loading list.
        limit_factor: Derating factor (default 0.95).

    Returns:
        A FlowgateDefinition with all fields populated.

    Raises:
        ValueError: If the corridor has no branches.
    """
    if not corridor.branches:
        msg = f"Corridor {corridor.corridor_id} has no branches"
        raise ValueError(msg)

    # 1. Compute weights
    weights = compute_flowgate_weights(corridor, branch_loadings)

    # 2. Compute max weighted flow across all load levels
    max_flow, binding_level = compute_max_weighted_flow(weights, branch_loadings)

    # 3. Apply derating factor
    limit_mw = limit_factor * max_flow

    # 4. Construct FlowgateBranch records
    fg_branches = [
        FlowgateBranch(
            branch_idx=w.branch_idx,
            from_bus=w.from_bus,
            to_bus=w.to_bus,
            weight=w.normalized_weight,
        )
        for w in weights
    ]

    # 5. Generate name
    flowgate_name = generate_flowgate_name(corridor)

    # 6. Return FlowgateDefinition
    return FlowgateDefinition(
        flowgate_id=f"FG_{flowgate_index}",
        flowgate_name=flowgate_name,
        branches=fg_branches,
        limit_mw=limit_mw,
        direction=FlowgateDirection.BOTH,
        calibration_load_level=binding_level,
        max_observed_flow_mw=max_flow,
    )


def define_flowgates(
    selected_corridors: list[CongestedCorridor],
    branch_loadings: dict[str, list[BranchLoading]],
    limit_factor: float = FLOWGATE_LIMIT_FACTOR,
) -> list[FlowgateDefinition]:
    """Define flowgates from the selected corridor list.

    Iterates over selected corridors (already sorted by severity) and
    calls define_single_flowgate for each. Flowgate IDs are assigned
    sequentially: FG_1 for the most congested corridor, FG_2 for the
    next, etc.

    Args:
        selected_corridors: Corridors from select_flowgate_corridors.
        branch_loadings: Dict mapping LoadLevel string to branch loading list.
        limit_factor: Derating factor (default 0.95).

    Returns:
        A list of FlowgateDefinition, one per selected corridor,
        ordered by severity (FG_1 first).

    Raises:
        ValueError: If selected_corridors is empty.
    """
    if not selected_corridors:
        msg = "No corridors provided for flowgate definition"
        raise ValueError(msg)

    flowgates: list[FlowgateDefinition] = []
    for i, corridor in enumerate(selected_corridors, start=1):
        fg = define_single_flowgate(corridor, i, branch_loadings, limit_factor)
        flowgates.append(fg)

    return flowgates


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_flowgates_csv(
    flowgates: list[FlowgateDefinition],
    dest_path: Path,
) -> None:
    """Write flowgate definitions to flowgates.csv in canonical format.

    Produces a CSV with columns: flowgate_id, flowgate_name,
    branch_id_list, weight_list, limit_mw, direction,
    calibration_load_level.

    branch_id_list and weight_list are semicolon-separated strings.
    limit_mw is written with 1 decimal place. Weights use 2 decimal places.

    Args:
        flowgates: The flowgate definitions to write.
        dest_path: File path for the output CSV. Parent directory
            is created if it does not exist.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "flowgate_id",
        "flowgate_name",
        "branch_id_list",
        "weight_list",
        "limit_mw",
        "direction",
        "calibration_load_level",
    ]

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for fg in flowgates:
            branch_ids = ";".join(str(b.branch_idx) for b in fg.branches)
            weights = ";".join(f"{b.weight:.2f}" for b in fg.branches)
            writer.writerow(
                [
                    fg.flowgate_id,
                    fg.flowgate_name,
                    branch_ids,
                    weights,
                    f"{fg.limit_mw:.1f}",
                    fg.direction.value,
                    fg.calibration_load_level,
                ]
            )


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------


def build_narrative_entry(
    flowgate: FlowgateDefinition,
) -> FlowgateNarrativeEntry:
    """Build a narrative entry for one flowgate.

    Generates a human-readable description of the flowgate including
    its physical interpretation (which buses and branches it monitors),
    how the limit was derived (95% of observed weighted flow), the
    branch weights, and the calibrating load level.

    Args:
        flowgate: A FlowgateDefinition.

    Returns:
        A FlowgateNarrativeEntry with all descriptive fields populated.
    """
    branch_descs = [
        f"Branch {b.branch_idx}: bus {b.from_bus} -> bus {b.to_bus}, weight={b.weight:.2f}"
        for b in flowgate.branches
    ]

    if len(flowgate.branches) == 1:
        b = flowgate.branches[0]
        interpretation = (
            f"Monitors the single transmission line from bus {b.from_bus} to bus {b.to_bus}."
        )
    else:
        bus_set: set[int] = set()
        for b in flowgate.branches:
            bus_set.add(b.from_bus)
            bus_set.add(b.to_bus)
        bus_list = sorted(bus_set)
        interpretation = (
            f"Monitors the parallel-path corridor spanning buses "
            f"{', '.join(str(b) for b in bus_list)} "
            f"with {len(flowgate.branches)} constituent branches."
        )

    return FlowgateNarrativeEntry(
        flowgate_id=flowgate.flowgate_id,
        flowgate_name=flowgate.flowgate_name,
        branch_count=len(flowgate.branches),
        branch_descriptions=branch_descs,
        limit_mw=flowgate.limit_mw,
        max_observed_flow_mw=flowgate.max_observed_flow_mw,
        derating_factor=FLOWGATE_LIMIT_FACTOR,
        calibration_load_level=flowgate.calibration_load_level,
        direction=flowgate.direction.value,
        physical_interpretation=interpretation,
    )


def write_flowgate_narrative(
    entries: list[FlowgateNarrativeEntry],
    network_id: str,
    dest_path: Path,
) -> None:
    """Write the human-readable calibration narrative to markdown.

    Produces a markdown document with:
    - Header identifying the network
    - Summary table of all flowgates (ID, name, limit, branch count)
    - Detailed section per flowgate with branch-level weight breakdown,
      limit derivation, and physical interpretation

    Args:
        entries: Narrative entries from build_narrative_entry.
        network_id: The CongestionNetworkId value string.
        dest_path: File path for the output markdown.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Flowgate Calibration Narrative: {network_id}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Flowgate ID | Name | Limit (MW) | Branches | Load Level |")
    lines.append("|-------------|------|------------|----------|------------|")
    for e in entries:
        lines.append(
            f"| {e.flowgate_id} | {e.flowgate_name} | {e.limit_mw:.1f} "
            f"| {e.branch_count} | {e.calibration_load_level} |"
        )
    lines.append("")

    for e in entries:
        lines.append(f"## {e.flowgate_id}: {e.flowgate_name}")
        lines.append("")
        lines.append(f"**Direction:** {e.direction}")
        lines.append("")
        lines.append(f"**Physical interpretation:** {e.physical_interpretation}")
        lines.append("")
        lines.append("**Constituent branches:**")
        lines.append("")
        for desc in e.branch_descriptions:
            lines.append(f"- {desc}")
        lines.append("")
        lines.append(
            f"**Limit derivation:** {e.derating_factor:.0%} of max observed weighted "
            f"flow ({e.max_observed_flow_mw:.1f} MW) = {e.limit_mw:.1f} MW, "
            f"calibrated at {e.calibration_load_level} load level."
        )
        lines.append("")

    dest_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Calibration log
# ---------------------------------------------------------------------------


def write_flowgate_definition_log(
    result: FlowgateCalibrationResult,
    flowgates: list[FlowgateDefinition],
    dest_path: Path,
) -> None:
    """Write the flowgate definition log to JSON for provenance.

    Documents:
    - Network identifier
    - Derating factor used (0.95)
    - Number of corridors from D5 and number selected
    - For each flowgate: ID, name, branch list with weights,
      limit_mw, max_observed_flow_mw, calibration_load_level,
      direction
    - Excluded corridors with reason (beyond max_flowgates count)

    Args:
        result: The FlowgateCalibrationResult.
        flowgates: The flowgate definitions.
        dest_path: File path for the output JSON.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    log_data = {
        "network_id": result.network_id,
        "derating_factor": FLOWGATE_LIMIT_FACTOR,
        "total_corridors_from_d5": result.total_corridor_count,
        "selected_corridor_count": result.selected_corridor_count,
        "excluded_corridor_count": result.excluded_corridor_count,
        "flowgates": [
            {
                "flowgate_id": fg.flowgate_id,
                "flowgate_name": fg.flowgate_name,
                "branches": [
                    {
                        "branch_idx": b.branch_idx,
                        "from_bus": b.from_bus,
                        "to_bus": b.to_bus,
                        "weight": round(b.weight, 4),
                    }
                    for b in fg.branches
                ],
                "limit_mw": round(fg.limit_mw, 1),
                "max_observed_flow_mw": round(fg.max_observed_flow_mw, 1),
                "calibration_load_level": fg.calibration_load_level,
                "direction": fg.direction.value,
            }
            for fg in flowgates
        ],
    }

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(log_data, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def define_network_flowgates(
    network_id: str,
    flowgate_calibration_dir: Path,
    output_dir: Path,
    limit_factor: float = FLOWGATE_LIMIT_FACTOR,
    max_flowgates: int = MAX_FLOWGATES,
) -> FlowgateCalibrationResult:
    """Run the full flowgate definition pipeline for one network.

    This is the primary per-network entry point. It:
    1. Loads congestion_candidates.csv from D5 output.
    2. Reconstructs corridor groups from candidate records.
    3. Loads branch_loading CSVs for all three load levels.
    4. Selects the top 3-5 corridors by max utilization.
    5. Computes weights and limits for each selected corridor.
    6. Defines FlowgateDefinition objects.
    7. Writes flowgates.csv to output_dir.
    8. Generates and writes calibration narrative.
    9. Writes flowgate_definition_log.json.

    Args:
        network_id: CongestionNetworkId value ("ACTIVSg2000" or "ACTIVSg10k").
        flowgate_calibration_dir: Path to the D5 output directory
            (data/timeseries/<network>/flowgate_calibration/).
        output_dir: Base output directory (data/timeseries/<network>/).
        limit_factor: Derating factor (default 0.95).
        max_flowgates: Maximum flowgates per network (default 5).

    Returns:
        A FlowgateCalibrationResult with all outputs.

    Raises:
        FileNotFoundError: If D5 output files are missing.
        ValueError: If no congestion corridors were found by D5.
    """
    # 1. Load congestion candidates
    candidates_csv = flowgate_calibration_dir / "congestion_candidates.csv"
    candidates = load_congestion_candidates_csv(candidates_csv)

    # 2. Reconstruct corridors
    corridors = reconstruct_corridors(candidates)

    # 3. Load branch loading CSVs for all three load levels
    branch_loadings: dict[str, list[BranchLoading]] = {}
    for level in LoadLevel:
        csv_path = flowgate_calibration_dir / f"branch_loading_{level.value}.csv"
        branch_loadings[level.value] = load_branch_loading_csv(csv_path)

    # 4. Select top corridors
    selected, excluded = select_flowgate_corridors(corridors, max_flowgates=max_flowgates)

    # 5-6. Define flowgates
    flowgates = define_flowgates(selected, branch_loadings, limit_factor)

    # 7. Write flowgates.csv
    flowgates_csv_path = output_dir / "flowgates.csv"
    write_flowgates_csv(flowgates, flowgates_csv_path)

    # 8. Generate and write narrative
    entries = [build_narrative_entry(fg) for fg in flowgates]
    narrative_path = flowgate_calibration_dir / "flowgate_narrative.md"
    write_flowgate_narrative(entries, network_id, narrative_path)

    # Build result (before writing log, so we can pass it to the log writer)
    result = FlowgateCalibrationResult(
        network_id=network_id,
        flowgates=flowgates,
        selected_corridor_count=len(selected),
        total_corridor_count=len(corridors),
        excluded_corridor_count=len(excluded),
        flowgates_csv_path=str(flowgates_csv_path),
        narrative_path=str(narrative_path),
        calibration_log_json_path=str(flowgate_calibration_dir / "flowgate_definition_log.json"),
    )

    # 9. Write definition log
    log_path = flowgate_calibration_dir / "flowgate_definition_log.json"
    write_flowgate_definition_log(result, flowgates, log_path)

    logger.info(
        "Defined %d flowgates for %s (from %d corridors, %d excluded)",
        len(flowgates),
        network_id,
        len(corridors),
        len(excluded),
    )

    return result


def main(
    timeseries_base_dir: Path | None = None,
) -> list[FlowgateCalibrationResult]:
    """Entry point: define flowgates for both SMALL and MEDIUM networks.

    Default paths resolve relative to the repository root:
    - D5 output: data/timeseries/<network>/flowgate_calibration/
    - flowgates.csv: data/timeseries/<network>/flowgates.csv
    - narrative: data/timeseries/<network>/flowgate_calibration/flowgate_narrative.md
    - definition log: data/timeseries/<network>/flowgate_calibration/flowgate_definition_log.json

    Processes both networks sequentially. Each network's definition is
    independent; failure in one does not prevent definition for the other
    (though an error is raised after both are attempted).

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.

    Returns:
        A list of 2 FlowgateCalibrationResult, one per network.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_root / "timeseries"

    results: list[FlowgateCalibrationResult] = []
    errors: list[str] = []

    for network_id in CongestionNetworkId:
        network_dir = timeseries_base_dir / network_id.value
        flowgate_cal_dir = network_dir / "flowgate_calibration"

        try:
            result = define_network_flowgates(
                network_id=network_id.value,
                flowgate_calibration_dir=flowgate_cal_dir,
                output_dir=network_dir,
            )
            results.append(result)
        except Exception as e:
            logger.error("Failed to define flowgates for %s: %s", network_id.value, e)
            errors.append(f"{network_id.value}: {e}")

    if errors:
        msg = "Flowgate definition failed for: " + "; ".join(errors)
        raise RuntimeError(msg)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
