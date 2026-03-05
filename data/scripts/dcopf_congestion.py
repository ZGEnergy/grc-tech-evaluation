"""DC OPF Congestion Analysis for SMALL (ACTIVSg2000) and MEDIUM (ACTIVSg10k) networks.

Runs MATPOWER DC OPF at three load levels (peak, shoulder, valley), produces branch
loading reports, identifies branches exceeding 80% thermal utilization, and clusters
adjacent congested branches into corridor groups that become flowgate candidates for
the downstream Deliverable 6 (Flowgate Definition & Calibration).

Output artifacts per network:
  - data/timeseries/<network>/flowgate_calibration/branch_loading_<level>.csv
  - data/timeseries/<network>/flowgate_calibration/congestion_candidates.csv
  - data/timeseries/<network>/flowgate_calibration/calibration_log.json
  - data/timeseries/<network>/flowgate_calibration/run_dcopf_<level>.m
"""

from __future__ import annotations

import csv
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class CongestionNetworkId(StrEnum):
    """Networks in scope for Phase 3 DC OPF congestion analysis.

    TINY is excluded -- Phase 2b PRD-07 handles it.
    """

    SMALL = "ACTIVSg2000"
    MEDIUM = "ACTIVSg10k"


class LoadLevel(StrEnum):
    """The three load levels at which DC OPF is run for congestion analysis.

    Consistent with Phase 2b PRD-07 LoadLevel enum.
    """

    PEAK = "peak"
    SHOULDER = "shoulder"
    VALLEY = "valley"


@dataclass(frozen=True)
class OPFSolverSettings:
    """Documented MATPOWER DC OPF solver configuration.

    Frozen across all runs and logged in calibration output for
    reproducibility. Matches Phase 2b PRD-07 settings exactly.
    """

    model: str = "DC"
    solver: str = "MIPS"
    tolerance: float = 1e-8
    enforce_branch_limits: bool = True
    verbose: int = 0


@dataclass(frozen=True)
class BranchLoading:
    """Branch flow result from a single DC OPF run.

    Represents one row in the branch_loading CSV.
    flow_mw is the absolute value of real power flow (|Pf|).
    utilization is flow_mw / rate_a_mw.
    """

    branch_idx: int  # 1-based index into mpc.branch matrix
    from_bus: int
    to_bus: int
    flow_mw: float  # |Pf| in MW
    rate_a_mw: float  # thermal limit (rateA) in MW
    utilization: float  # flow_mw / rate_a_mw


@dataclass(frozen=True)
class OPFRunResult:
    """Result of a single DC OPF run at one load level for one network.

    Captures solver convergence, objective, and full branch loading report.
    """

    network_id: CongestionNetworkId
    load_level: LoadLevel
    load_multiplier: float  # fraction of peak system load
    system_load_mw: float  # total Pd after scaling
    converged: bool
    objective_value: float  # minimized total generation cost ($)
    branch_count: int  # total branches in network
    branch_loadings: list[BranchLoading]


@dataclass(frozen=True)
class CongestionCandidate:
    """A branch identified as congested (>= threshold utilization) at any load level.

    Records the branch identity, thermal rating, and utilization at
    each of the three load levels. max_utilization is the maximum
    across all three levels.
    """

    branch_idx: int  # 1-based
    from_bus: int
    to_bus: int
    rate_a_mw: float
    utilization_peak: float
    utilization_shoulder: float
    utilization_valley: float
    max_utilization: float
    binding_load_level: LoadLevel  # level at which max_utilization occurs
    corridor_group_id: int | None = None  # assigned during clustering


@dataclass(frozen=True)
class CongestedCorridor:
    """A group of electrically adjacent congested branches forming a corridor.

    Corridors become flowgate candidates for D6.
    """

    corridor_id: int  # 1-based
    branches: list[CongestionCandidate]
    shared_buses: list[int]  # buses shared between branches in this corridor
    max_utilization: float  # max across all branches and load levels
    binding_load_level: LoadLevel  # level at which corridor max occurs
    branch_count: int


@dataclass(frozen=True)
class LoadLevelSelection:
    """Selected hour and multiplier for a single load level."""

    load_level: LoadLevel
    hour_ending: int  # 1-based (1..24)
    system_load_mw: float  # system total MW at this hour
    load_multiplier: float  # ratio to peak hour (1.0 for peak)


@dataclass(frozen=True)
class CongestionAnalysisResult:
    """Complete result of the congestion analysis pipeline for one network.

    Bundles all intermediate and final outputs for one network.
    """

    network_id: CongestionNetworkId
    opf_results: list[OPFRunResult]  # 3 entries (peak, shoulder, valley)
    load_level_selections: list[LoadLevelSelection]  # 3 entries
    congestion_threshold: float  # 0.80, or relaxed value if needed
    candidates: list[CongestionCandidate]
    corridors: list[CongestedCorridor]
    branch_loading_csv_paths: dict[LoadLevel, str]  # level -> relative path
    congestion_candidates_csv_path: str  # relative path
    calibration_log_json_path: str  # relative path
    octave_script_paths: dict[LoadLevel, str]  # level -> relative path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONGESTION_THRESHOLD: float = 0.80
"""Minimum branch utilization to qualify as a congestion candidate.

Branches with utilization >= 0.80 at any load level are candidates
for corridor grouping. If fewer than 5 candidates are found at
0.80, the threshold is relaxed to 0.70. Consistent with the TLR
standard and Phase 2b PRD-07.
"""

RELAXED_CONGESTION_THRESHOLD: float = 0.70
"""Fallback threshold if CONGESTION_THRESHOLD yields fewer than 5 candidates."""

MIN_CANDIDATES: int = 5
"""Minimum number of congestion candidates before threshold relaxation.

For SMALL/MEDIUM networks (hundreds to thousands of branches),
5 candidates is the minimum to produce 3-5 meaningful flowgates.
"""

LOAD_LEVEL_TARGETS: dict[str, float] = {
    "peak": 1.00,
    "shoulder": 0.75,
    "valley": 0.55,
}
"""Target load multipliers for the three OPF runs.

Actual multipliers are derived from load_24h.csv system totals
by selecting the hour closest to each target fraction of peak.
"""

MATPOWER_PATH: str = "evaluations/matpower/matpower8.1"
"""Relative path from repo root to the MATPOWER installation."""

SOLVER_SETTINGS: OPFSolverSettings = OPFSolverSettings()
"""Frozen solver settings for all DC OPF runs."""

OPF_TIMEOUT_SECONDS: int = 600
"""Maximum time (seconds) for a single DC OPF subprocess.

SMALL (2000 buses) and MEDIUM (10000 buses) DC OPF can take
significantly longer than TINY (39 buses). 10 minutes is generous
for DC OPF even on large networks.
"""

NETWORK_M_FILE_NAMES: dict[CongestionNetworkId, str] = {
    CongestionNetworkId.SMALL: "case_ACTIVSg2000.m",
    CongestionNetworkId.MEDIUM: "case_ACTIVSg10k.m",
}
"""Mapping from network ID to the cleaned .m file name."""


# ---------------------------------------------------------------------------
# Load level selection
# ---------------------------------------------------------------------------


def select_load_level_hours(
    system_hourly_mw: list[float],
) -> list[LoadLevelSelection]:
    """Select the representative hour for each load level from the 24h profile.

    For each target load level (peak, shoulder, valley), finds the hour
    whose system total is closest to the target fraction of the peak
    hour's system total. Returns a LoadLevelSelection per level.

    The peak hour is always the hour with the maximum system total
    (multiplier = 1.0). The shoulder hour is the hour closest to 75%
    of peak. The valley hour is the hour closest to 55% of peak.

    Consistent with Phase 2b PRD-07 select_load_level_hours.

    Args:
        system_hourly_mw: 24-element list of system total load per hour
            (MW), index 0 = HR_1, index 23 = HR_24.

    Returns:
        A list of 3 LoadLevelSelection objects (peak, shoulder, valley).

    Raises:
        ValueError: If system_hourly_mw does not contain exactly 24 values.
        ValueError: If the peak system load is zero or negative.
    """
    if len(system_hourly_mw) != 24:
        msg = f"Expected 24 hourly values, got {len(system_hourly_mw)}"
        raise ValueError(msg)

    peak_mw = max(system_hourly_mw)
    if peak_mw <= 0:
        msg = f"Peak system load must be positive, got {peak_mw}"
        raise ValueError(msg)

    peak_hour_idx = system_hourly_mw.index(peak_mw)

    selections: list[LoadLevelSelection] = []

    for level_name, target_fraction in LOAD_LEVEL_TARGETS.items():
        load_level = LoadLevel(level_name)
        target_mw = peak_mw * target_fraction

        # Find the hour closest to the target
        best_idx = 0
        best_diff = abs(system_hourly_mw[0] - target_mw)
        for i in range(1, 24):
            diff = abs(system_hourly_mw[i] - target_mw)
            if diff < best_diff:
                best_diff = diff
                best_idx = i

        # For peak, always use the actual peak hour
        if load_level == LoadLevel.PEAK:
            best_idx = peak_hour_idx

        actual_mw = system_hourly_mw[best_idx]
        multiplier = actual_mw / peak_mw

        selections.append(
            LoadLevelSelection(
                load_level=load_level,
                hour_ending=best_idx + 1,  # 1-based
                system_load_mw=actual_mw,
                load_multiplier=multiplier,
            )
        )

    return selections


# ---------------------------------------------------------------------------
# System hourly totals
# ---------------------------------------------------------------------------


def load_system_hourly_totals(load_csv_path: Path) -> list[float]:
    """Load 24-hour system-level load totals from load_24h.csv.

    Reads load_24h.csv (Phase 1 D5 output), sums MW across all buses
    at each hour, and returns a 24-element list of system totals.
    Index 0 = HR_1, index 23 = HR_24.

    Consistent with Phase 2b PRD-07 load_system_hourly_totals.

    Args:
        load_csv_path: Path to load_24h.csv.

    Returns:
        A 24-element list of system total MW per hour.

    Raises:
        FileNotFoundError: If load_csv_path does not exist.
    """
    if not load_csv_path.exists():
        msg = f"Load CSV not found: {load_csv_path}"
        raise FileNotFoundError(msg)

    hourly_totals = [0.0] * 24

    with open(load_csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            for h in range(1, 25):
                col = f"HR_{h}"
                if col in row:
                    hourly_totals[h - 1] += float(row[col])

    return hourly_totals


# ---------------------------------------------------------------------------
# Octave script generation
# ---------------------------------------------------------------------------


def generate_octave_script(
    cleaned_m_path: Path,
    matpower_path: Path,
    output_csv_path: Path,
    load_multiplier: float,
    solver_settings: OPFSolverSettings,
) -> str:
    """Generate the Octave .m script content for a single DC OPF run.

    Produces a complete Octave script that:
    1. Adds the MATPOWER path to the Octave search path.
    2. Loads the cleaned .m case file.
    3. Scales all bus Pd values by load_multiplier.
    4. Scales all bus Qd values by load_multiplier (maintain power factor).
    5. Configures MATPOWER options (DC model, MIPS solver, tolerance).
    6. Runs rundcopf (DC OPF).
    7. Extracts branch flow results (Pf column from result.branch).
    8. Writes branch_idx, from_bus, to_bus, flow_mw, rate_a_mw, utilization
       to the output CSV file.
    9. Prints convergence status and objective value to stdout for capture.

    Args:
        cleaned_m_path: Absolute path to the cleaned .m case file.
        matpower_path: Absolute path to the MATPOWER installation directory.
        output_csv_path: Absolute path where branch loading CSV will be written.
        load_multiplier: Fraction of peak load (e.g., 1.0, 0.75, 0.55).
        solver_settings: DC OPF solver configuration.

    Returns:
        A string containing the complete Octave .m script content.
    """
    verbose_flag = solver_settings.verbose

    script = f"""%% Auto-generated DC OPF script
%% Load multiplier: {load_multiplier}

%% Add MATPOWER to path
addpath(genpath('{matpower_path}'));

%% Load the case
mpc = loadcase('{cleaned_m_path}');

%% Scale bus Pd and Qd by load multiplier
mpc.bus(:, 3) = mpc.bus(:, 3) * {load_multiplier};  % Pd
mpc.bus(:, 4) = mpc.bus(:, 4) * {load_multiplier};  % Qd

%% Configure MATPOWER options
mpopt = mpoption();
mpopt = mpoption(mpopt, 'model', '{solver_settings.model}');
mpopt = mpoption(mpopt, 'opf.dc.solver', '{solver_settings.solver}');
mpopt = mpoption(mpopt, 'opf.violation', {solver_settings.tolerance});
mpopt = mpoption(mpopt, 'verbose', {verbose_flag});
mpopt = mpoption(mpopt, 'out.all', 0);

%% Enforce branch flow limits
mpopt = mpoption(mpopt, 'opf.flow_lim', 'P');

%% Run DC OPF
result = rundcopf(mpc, mpopt);

%% Print convergence status
if result.success
    fprintf('CONVERGED=1\\n');
else
    fprintf('CONVERGED=0\\n');
end
fprintf('OBJECTIVE=%.6f\\n', result.f);

%% Write branch loading CSV
fid = fopen('{output_csv_path}', 'w');
fprintf(fid, 'branch_idx,from_bus,to_bus,flow_mw,rate_a_mw,utilization\\n');
n_branch = size(result.branch, 1);
for k = 1:n_branch
    from_bus = result.branch(k, 1);
    to_bus = result.branch(k, 2);
    rate_a = result.branch(k, 6);
    flow_mw = abs(result.branch(k, 14));  % PF column (real power flow)
    if rate_a > 0
        util = flow_mw / rate_a;
    else
        util = 0.0;
    end
    fprintf(fid, '%d,%d,%d,%.4f,%d,%.4f\\n', k, from_bus, to_bus, flow_mw, rate_a, util);
end
fclose(fid);

fprintf('DCOPF_COMPLETE\\n');
exit(0);
"""
    return script


def run_octave_dcopf(
    script_content: str,
    script_path: Path,
    timeout_seconds: int = OPF_TIMEOUT_SECONDS,
) -> tuple[bool, float, str]:
    """Write and execute an Octave DC OPF script via subprocess.

    Writes the script content to script_path, then invokes Octave
    via subprocess.run. Parses stdout for convergence status and
    objective value. The script is expected to print lines:
        CONVERGED=1
        OBJECTIVE=<float>

    Args:
        script_content: The Octave .m script content.
        script_path: File path to write the .m script.
        timeout_seconds: Maximum wait time. Default 600s for large networks.

    Returns:
        A tuple of (converged, objective_value, raw_stdout).

    Raises:
        RuntimeError: If Octave returns a nonzero exit code.
        TimeoutError: If Octave does not complete within timeout_seconds.
        FileNotFoundError: If the octave binary is not found in PATH.
    """
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_content)

    try:
        result = subprocess.run(
            ["octave", "--no-gui", "--no-window-system", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        msg = "Octave binary not found in PATH"
        raise FileNotFoundError(msg)
    except subprocess.TimeoutExpired as e:
        msg = f"Octave DC OPF timed out after {timeout_seconds}s"
        raise TimeoutError(msg) from e

    stdout = result.stdout
    stderr = result.stderr

    if result.returncode != 0:
        msg = f"Octave exited with code {result.returncode}. stderr: {stderr}"
        raise RuntimeError(msg)

    # Parse convergence and objective from stdout
    converged = False
    objective_value = 0.0

    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("CONVERGED="):
            converged = line.split("=", 1)[1].strip() == "1"
        elif line.startswith("OBJECTIVE="):
            try:
                objective_value = float(line.split("=", 1)[1].strip())
            except ValueError:
                objective_value = 0.0

    return converged, objective_value, stdout


# ---------------------------------------------------------------------------
# Branch loading parsing
# ---------------------------------------------------------------------------


def parse_branch_loading_csv(csv_path: Path) -> list[BranchLoading]:
    """Parse a branch loading CSV file written by the Octave DC OPF script.

    Reads the CSV and returns a list of BranchLoading records, one per
    branch, ordered by branch_idx ascending.

    Expected CSV columns: branch_idx, from_bus, to_bus, flow_mw,
    rate_a_mw, utilization.

    Consistent with Phase 2b PRD-07 parse_branch_loading_csv.

    Args:
        csv_path: Path to the branch loading CSV file.

    Returns:
        A list of BranchLoading, ordered by branch_idx ascending.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: If the CSV has unexpected columns or non-numeric data.
    """
    if not csv_path.exists():
        msg = f"Branch loading CSV not found: {csv_path}"
        raise FileNotFoundError(msg)

    loadings: list[BranchLoading] = []

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        expected_cols = {"branch_idx", "from_bus", "to_bus", "flow_mw", "rate_a_mw", "utilization"}
        if reader.fieldnames is None:
            msg = "CSV file has no header row"
            raise ValueError(msg)
        actual_cols = set(reader.fieldnames)
        missing = expected_cols - actual_cols
        if missing:
            msg = f"Missing columns in branch loading CSV: {missing}"
            raise ValueError(msg)

        for row in reader:
            try:
                loadings.append(
                    BranchLoading(
                        branch_idx=int(row["branch_idx"]),
                        from_bus=int(row["from_bus"]),
                        to_bus=int(row["to_bus"]),
                        flow_mw=float(row["flow_mw"]),
                        rate_a_mw=float(row["rate_a_mw"]),
                        utilization=float(row["utilization"]),
                    )
                )
            except (ValueError, KeyError) as e:
                msg = f"Error parsing branch loading CSV row: {e}"
                raise ValueError(msg) from e

    loadings.sort(key=lambda b: b.branch_idx)
    return loadings


# ---------------------------------------------------------------------------
# Congestion analysis
# ---------------------------------------------------------------------------


def identify_congestion_candidates(
    opf_results: list[OPFRunResult],
    threshold: float = CONGESTION_THRESHOLD,
) -> list[CongestionCandidate]:
    """Identify branches exceeding the utilization threshold at any load level.

    Scans branch loadings across all three OPF runs. A branch is a
    candidate if its utilization >= threshold at any load level. For
    each candidate, records utilization at all three levels, maximum
    utilization, and binding load level.

    Results are sorted by max_utilization descending (most congested first).

    Args:
        opf_results: List of OPFRunResult, one per load level (3 entries).
            All must be for the same network.
        threshold: Minimum utilization to qualify as a candidate.

    Returns:
        A list of CongestionCandidate, sorted by max_utilization descending.

    Raises:
        ValueError: If opf_results does not contain exactly 3 entries.
        ValueError: If any OPF run did not converge.
        ValueError: If opf_results contain mixed network IDs.
    """
    if len(opf_results) != 3:
        msg = f"Expected exactly 3 OPF results, got {len(opf_results)}"
        raise ValueError(msg)

    network_ids = {r.network_id for r in opf_results}
    if len(network_ids) > 1:
        msg = f"Mixed network IDs in OPF results: {network_ids}"
        raise ValueError(msg)

    for r in opf_results:
        if not r.converged:
            msg = f"OPF run for {r.load_level} did not converge"
            raise ValueError(msg)

    # Build per-level lookup: branch_idx -> utilization
    level_utils: dict[LoadLevel, dict[int, BranchLoading]] = {}
    for r in opf_results:
        level_map: dict[int, BranchLoading] = {}
        for bl in r.branch_loadings:
            level_map[bl.branch_idx] = bl
        level_utils[r.load_level] = level_map

    # Get all branch indices from any result
    all_branch_idxs: set[int] = set()
    for r in opf_results:
        for bl in r.branch_loadings:
            all_branch_idxs.add(bl.branch_idx)

    candidates: list[CongestionCandidate] = []

    for branch_idx in sorted(all_branch_idxs):
        # Get utilization at each level
        util_peak = 0.0
        util_shoulder = 0.0
        util_valley = 0.0
        from_bus = 0
        to_bus = 0
        rate_a = 0.0

        if LoadLevel.PEAK in level_utils and branch_idx in level_utils[LoadLevel.PEAK]:
            bl = level_utils[LoadLevel.PEAK][branch_idx]
            util_peak = bl.utilization
            from_bus = bl.from_bus
            to_bus = bl.to_bus
            rate_a = bl.rate_a_mw

        if LoadLevel.SHOULDER in level_utils and branch_idx in level_utils[LoadLevel.SHOULDER]:
            bl = level_utils[LoadLevel.SHOULDER][branch_idx]
            util_shoulder = bl.utilization
            if from_bus == 0:
                from_bus = bl.from_bus
                to_bus = bl.to_bus
                rate_a = bl.rate_a_mw

        if LoadLevel.VALLEY in level_utils and branch_idx in level_utils[LoadLevel.VALLEY]:
            bl = level_utils[LoadLevel.VALLEY][branch_idx]
            util_valley = bl.utilization
            if from_bus == 0:
                from_bus = bl.from_bus
                to_bus = bl.to_bus
                rate_a = bl.rate_a_mw

        # Check if any level exceeds threshold
        max_util = max(util_peak, util_shoulder, util_valley)
        if max_util >= threshold:
            # Determine binding level
            if max_util == util_peak:
                binding = LoadLevel.PEAK
            elif max_util == util_shoulder:
                binding = LoadLevel.SHOULDER
            else:
                binding = LoadLevel.VALLEY

            candidates.append(
                CongestionCandidate(
                    branch_idx=branch_idx,
                    from_bus=from_bus,
                    to_bus=to_bus,
                    rate_a_mw=rate_a,
                    utilization_peak=util_peak,
                    utilization_shoulder=util_shoulder,
                    utilization_valley=util_valley,
                    max_utilization=max_util,
                    binding_load_level=binding,
                )
            )

    # Sort by max_utilization descending
    candidates.sort(key=lambda c: c.max_utilization, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Corridor clustering
# ---------------------------------------------------------------------------


def cluster_congested_corridors(
    candidates: list[CongestionCandidate],
) -> list[CongestedCorridor]:
    """Group congested branches into corridor clusters by electrical adjacency.

    Two candidate branches are in the same corridor if they share a
    common bus (either from_bus or to_bus). Corridors are formed
    transitively using union-find: if branch A shares a bus with B,
    and B shares a bus with C, all three are in the same corridor.

    The corridor_id is assigned in order of descending max_utilization
    (corridor 1 is the most congested).

    Each corridor records the set of shared buses (junction points)
    and the maximum utilization across all constituent branches and
    load levels.

    Args:
        candidates: Congestion candidates from identify_congestion_candidates.

    Returns:
        A list of CongestedCorridor, sorted by max_utilization descending.
        Each corridor's branches are sorted by branch_idx ascending.
    """
    if not candidates:
        return []

    n = len(candidates)
    parent = list(range(n))
    rank = [0] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if rank[ra] < rank[rb]:
                ra, rb = rb, ra
            parent[rb] = ra
            if rank[ra] == rank[rb]:
                rank[ra] += 1

    # Build bus-to-candidate-index mapping
    bus_to_indices: dict[int, list[int]] = {}
    for i, c in enumerate(candidates):
        for bus_id in (c.from_bus, c.to_bus):
            if bus_id not in bus_to_indices:
                bus_to_indices[bus_id] = []
            bus_to_indices[bus_id].append(i)

    # Union candidates sharing a bus
    for indices in bus_to_indices.values():
        for j in range(1, len(indices)):
            union(indices[0], indices[j])

    # Collect groups by root
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # Build corridor objects
    corridors: list[CongestedCorridor] = []
    for group_indices in groups.values():
        group_candidates = [candidates[i] for i in group_indices]
        group_candidates.sort(key=lambda c: c.branch_idx)

        # Find shared buses: buses that appear in more than one branch
        bus_count: dict[int, int] = {}
        for c in group_candidates:
            for bus_id in (c.from_bus, c.to_bus):
                bus_count[bus_id] = bus_count.get(bus_id, 0) + 1
        shared = sorted(b for b, cnt in bus_count.items() if cnt > 1)

        # Corridor-level max utilization and binding level
        corridor_max = max(c.max_utilization for c in group_candidates)
        binding_candidate = max(group_candidates, key=lambda c: c.max_utilization)
        binding_level = binding_candidate.binding_load_level

        corridors.append(
            CongestedCorridor(
                corridor_id=0,  # assigned below after sorting
                branches=group_candidates,
                shared_buses=shared,
                max_utilization=corridor_max,
                binding_load_level=binding_level,
                branch_count=len(group_candidates),
            )
        )

    # Sort by max_utilization descending and assign corridor IDs
    corridors.sort(key=lambda c: c.max_utilization, reverse=True)

    result: list[CongestedCorridor] = []
    for idx, corridor in enumerate(corridors):
        result.append(
            CongestedCorridor(
                corridor_id=idx + 1,
                branches=corridor.branches,
                shared_buses=corridor.shared_buses,
                max_utilization=corridor.max_utilization,
                binding_load_level=corridor.binding_load_level,
                branch_count=corridor.branch_count,
            )
        )

    return result


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def write_branch_loading_csv(
    branch_loadings: list[BranchLoading],
    dest_path: Path,
) -> None:
    """Write branch loading results to CSV.

    Produces a CSV with columns: branch_idx, from_bus, to_bus,
    flow_mw, rate_a_mw, utilization. One row per branch.
    flow_mw and utilization are written with 4 decimal places.
    rate_a_mw is written as an integer.

    Args:
        branch_loadings: Branch loading records from an OPF run.
        dest_path: File path for the output CSV. Parent directory
            is created if it does not exist.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["branch_idx", "from_bus", "to_bus", "flow_mw", "rate_a_mw", "utilization"])
        for bl in branch_loadings:
            writer.writerow(
                [
                    bl.branch_idx,
                    bl.from_bus,
                    bl.to_bus,
                    f"{bl.flow_mw:.4f}",
                    int(bl.rate_a_mw),
                    f"{bl.utilization:.4f}",
                ]
            )


def write_congestion_candidates_csv(
    candidates: list[CongestionCandidate],
    corridors: list[CongestedCorridor],
    dest_path: Path,
) -> None:
    """Write congestion candidates to CSV with corridor assignments.

    Produces a CSV with columns: branch_idx, from_bus, to_bus,
    rate_a_mw, utilization_peak, utilization_shoulder, utilization_valley,
    max_utilization, binding_load_level, corridor_group_id.

    corridor_group_id is the 1-based corridor identifier from
    cluster_congested_corridors. Candidates are written in order
    of descending max_utilization.

    Args:
        candidates: All congestion candidates.
        corridors: Corridor assignments from cluster_congested_corridors.
        dest_path: File path for the output CSV.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Build branch_idx -> corridor_id mapping
    branch_to_corridor: dict[int, int] = {}
    for corridor in corridors:
        for branch in corridor.branches:
            branch_to_corridor[branch.branch_idx] = corridor.corridor_id

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
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
            ]
        )
        for c in candidates:
            corridor_id = branch_to_corridor.get(c.branch_idx, 0)
            writer.writerow(
                [
                    c.branch_idx,
                    c.from_bus,
                    c.to_bus,
                    int(c.rate_a_mw),
                    f"{c.utilization_peak:.4f}",
                    f"{c.utilization_shoulder:.4f}",
                    f"{c.utilization_valley:.4f}",
                    f"{c.max_utilization:.4f}",
                    c.binding_load_level.value,
                    corridor_id,
                ]
            )


# ---------------------------------------------------------------------------
# Calibration log
# ---------------------------------------------------------------------------


def write_calibration_log(
    result: CongestionAnalysisResult,
    solver_settings: OPFSolverSettings,
    dest_path: Path,
) -> None:
    """Write the calibration log to JSON for provenance and reproducibility.

    Documents:
    - Network identifier and branch count
    - Solver settings (model, solver, tolerance)
    - Load level selections (hour-ending, multiplier, system MW)
    - OPF convergence status and objective value per run
    - Congestion threshold used (0.80 or relaxed 0.70)
    - Number of candidate branches per load level
    - Full candidate list with per-level utilization
    - Corridor assignments with shared bus sets
    - Total congested corridor count

    Args:
        result: The complete CongestionAnalysisResult.
        solver_settings: The solver settings used.
        dest_path: File path for the output JSON.

    Raises:
        PermissionError: If dest_path is not writable.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    log_data: dict = {
        "network_id": result.network_id.value,
        "solver_settings": {
            "model": solver_settings.model,
            "solver": solver_settings.solver,
            "tolerance": solver_settings.tolerance,
            "enforce_branch_limits": solver_settings.enforce_branch_limits,
            "verbose": solver_settings.verbose,
        },
        "load_levels": [
            {
                "load_level": sel.load_level.value,
                "hour_ending": sel.hour_ending,
                "system_load_mw": round(sel.system_load_mw, 2),
                "load_multiplier": round(sel.load_multiplier, 4),
            }
            for sel in result.load_level_selections
        ],
        "opf_runs": [
            {
                "load_level": r.load_level.value,
                "load_multiplier": round(r.load_multiplier, 4),
                "system_load_mw": round(r.system_load_mw, 2),
                "converged": r.converged,
                "objective_value": round(r.objective_value, 2),
                "branch_count": r.branch_count,
            }
            for r in result.opf_results
        ],
        "congestion_threshold": result.congestion_threshold,
        "candidate_count": len(result.candidates),
        "candidates": [
            {
                "branch_idx": c.branch_idx,
                "from_bus": c.from_bus,
                "to_bus": c.to_bus,
                "rate_a_mw": c.rate_a_mw,
                "utilization_peak": round(c.utilization_peak, 4),
                "utilization_shoulder": round(c.utilization_shoulder, 4),
                "utilization_valley": round(c.utilization_valley, 4),
                "max_utilization": round(c.max_utilization, 4),
                "binding_load_level": c.binding_load_level.value,
                "corridor_group_id": c.corridor_group_id,
            }
            for c in result.candidates
        ],
        "corridors": [
            {
                "corridor_id": cor.corridor_id,
                "branch_count": cor.branch_count,
                "shared_buses": cor.shared_buses,
                "max_utilization": round(cor.max_utilization, 4),
                "binding_load_level": cor.binding_load_level.value,
                "branch_indices": [b.branch_idx for b in cor.branches],
            }
            for cor in result.corridors
        ],
        "total_corridor_count": len(result.corridors),
    }

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(log_data, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_all_dcopf(
    network_id: CongestionNetworkId,
    cleaned_m_path: Path,
    matpower_path: Path,
    load_level_selections: list[LoadLevelSelection],
    output_dir: Path,
) -> list[OPFRunResult]:
    """Run DC OPF at all three load levels for one network and collect results.

    For each load level:
    1. Generates the Octave script via generate_octave_script.
    2. Writes the script to output_dir/run_dcopf_<level>.m.
    3. Executes the script via run_octave_dcopf.
    4. Parses the branch loading CSV via parse_branch_loading_csv.
    5. Constructs an OPFRunResult.

    Args:
        network_id: Which network to process.
        cleaned_m_path: Path to the cleaned .m file.
        matpower_path: Path to the MATPOWER installation directory.
        load_level_selections: The 3 LoadLevelSelection objects.
        output_dir: Directory for intermediate files (Octave scripts,
            branch loading CSVs). Created if it does not exist.

    Returns:
        A list of 3 OPFRunResult, one per load level.

    Raises:
        RuntimeError: If any OPF run fails to converge.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[OPFRunResult] = []

    for sel in load_level_selections:
        level = sel.load_level
        csv_path = output_dir / f"branch_loading_{level.value}.csv"
        script_path = output_dir / f"run_dcopf_{level.value}.m"

        script_content = generate_octave_script(
            cleaned_m_path=cleaned_m_path,
            matpower_path=matpower_path,
            output_csv_path=csv_path,
            load_multiplier=sel.load_multiplier,
            solver_settings=SOLVER_SETTINGS,
        )

        logger.info(
            "Running DC OPF for %s at %s (multiplier=%.4f)",
            network_id.value,
            level.value,
            sel.load_multiplier,
        )

        converged, objective, stdout = run_octave_dcopf(script_content, script_path)

        if not converged:
            msg = (
                f"DC OPF did not converge for {network_id.value} at {level.value} "
                f"(multiplier={sel.load_multiplier})"
            )
            raise RuntimeError(msg)

        branch_loadings = parse_branch_loading_csv(csv_path)

        results.append(
            OPFRunResult(
                network_id=network_id,
                load_level=level,
                load_multiplier=sel.load_multiplier,
                system_load_mw=sel.system_load_mw,
                converged=converged,
                objective_value=objective,
                branch_count=len(branch_loadings),
                branch_loadings=branch_loadings,
            )
        )

    return results


def analyze_network_congestion(
    network_id: CongestionNetworkId,
    cleaned_m_path: Path,
    load_csv_path: Path,
    matpower_path: Path,
    output_dir: Path,
) -> CongestionAnalysisResult:
    """Run the full congestion analysis pipeline for one network.

    This is the primary per-network entry point. It:
    1. Loads system hourly totals from load_24h.csv.
    2. Selects representative hours for peak/shoulder/valley.
    3. Runs DC OPF at all three load levels.
    4. Identifies congestion candidates (>= 80% utilization).
    5. If fewer than MIN_CANDIDATES, relaxes threshold to 70%.
    6. Clusters candidates into congested corridors.
    7. Writes branch loading CSVs per load level.
    8. Writes congestion_candidates.csv.
    9. Writes calibration_log.json.

    Args:
        network_id: Which network (SMALL or MEDIUM).
        cleaned_m_path: Path to the cleaned .m file
            (data/timeseries/<network>/<case_file>.m).
        load_csv_path: Path to load_24h.csv
            (data/timeseries/<network>/load_24h.csv).
        matpower_path: Path to the MATPOWER installation directory.
        output_dir: Base output directory (data/timeseries/<network>/).

    Returns:
        A CongestionAnalysisResult with all outputs and in-memory data.

    Raises:
        FileNotFoundError: If cleaned .m file or load CSV not found.
        RuntimeError: If DC OPF fails to converge at any load level.
    """
    if not cleaned_m_path.exists():
        msg = f"Cleaned .m file not found: {cleaned_m_path}"
        raise FileNotFoundError(msg)
    if not load_csv_path.exists():
        msg = f"Load CSV not found: {load_csv_path}"
        raise FileNotFoundError(msg)

    # 1. Load system hourly totals
    system_hourly = load_system_hourly_totals(load_csv_path)

    # 2. Select representative hours
    load_level_selections = select_load_level_hours(system_hourly)

    # 3. Run DC OPF at all three load levels
    cal_dir = output_dir / "flowgate_calibration"
    opf_results = run_all_dcopf(
        network_id=network_id,
        cleaned_m_path=cleaned_m_path,
        matpower_path=matpower_path,
        load_level_selections=load_level_selections,
        output_dir=cal_dir,
    )

    # 4. Identify congestion candidates
    threshold = CONGESTION_THRESHOLD
    candidates = identify_congestion_candidates(opf_results, threshold)

    # 5. Relax threshold if too few candidates
    if len(candidates) < MIN_CANDIDATES:
        logger.warning(
            "Only %d candidates at threshold %.2f for %s; relaxing to %.2f",
            len(candidates),
            threshold,
            network_id.value,
            RELAXED_CONGESTION_THRESHOLD,
        )
        threshold = RELAXED_CONGESTION_THRESHOLD
        candidates = identify_congestion_candidates(opf_results, threshold)

    # 6. Cluster into corridors
    corridors = cluster_congested_corridors(candidates)

    # 7-9. Write outputs
    branch_loading_paths: dict[LoadLevel, str] = {}
    octave_script_paths: dict[LoadLevel, str] = {}
    for level in LoadLevel:
        bl_path = cal_dir / f"branch_loading_{level.value}.csv"
        branch_loading_paths[level] = str(bl_path)
        octave_script_paths[level] = str(cal_dir / f"run_dcopf_{level.value}.m")

    candidates_csv_path = cal_dir / "congestion_candidates.csv"
    write_congestion_candidates_csv(candidates, corridors, candidates_csv_path)

    cal_log_path = cal_dir / "calibration_log.json"

    result = CongestionAnalysisResult(
        network_id=network_id,
        opf_results=opf_results,
        load_level_selections=load_level_selections,
        congestion_threshold=threshold,
        candidates=candidates,
        corridors=corridors,
        branch_loading_csv_paths=branch_loading_paths,
        congestion_candidates_csv_path=str(candidates_csv_path),
        calibration_log_json_path=str(cal_log_path),
        octave_script_paths=octave_script_paths,
    )

    write_calibration_log(result, SOLVER_SETTINGS, cal_log_path)

    return result


def main(
    timeseries_base_dir: Path | None = None,
    matpower_path: Path | None = None,
) -> list[CongestionAnalysisResult]:
    """Entry point: run congestion analysis for both SMALL and MEDIUM networks.

    Default paths resolve relative to the repository root:
    - cleaned .m files: data/timeseries/<network>/<case_file>.m
    - load profiles: data/timeseries/<network>/load_24h.csv
    - matpower: evaluations/matpower/matpower8.1/
    - output: data/timeseries/<network>/flowgate_calibration/

    Processes both networks sequentially. Each network's analysis is
    independent; failure in one does not prevent analysis of the other
    (though an error is raised after both are attempted).

    Args:
        timeseries_base_dir: Base directory for input/output. Defaults
            to <repo_root>/data/timeseries/.
        matpower_path: Path to MATPOWER installation. Defaults to
            <repo_root>/evaluations/matpower/matpower8.1/.

    Returns:
        A list of 2 CongestionAnalysisResult, one per network.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if timeseries_base_dir is None:
        timeseries_base_dir = repo_root / "timeseries"
    if matpower_path is None:
        matpower_path = repo_root.parent / MATPOWER_PATH

    results: list[CongestionAnalysisResult] = []
    errors: list[str] = []

    for network_id in CongestionNetworkId:
        m_file_name = NETWORK_M_FILE_NAMES[network_id]
        cleaned_m_path = timeseries_base_dir / network_id.value / m_file_name
        load_csv_path = timeseries_base_dir / network_id.value / "load_24h.csv"
        output_dir = timeseries_base_dir / network_id.value

        try:
            result = analyze_network_congestion(
                network_id=network_id,
                cleaned_m_path=cleaned_m_path,
                load_csv_path=load_csv_path,
                matpower_path=matpower_path,
                output_dir=output_dir,
            )
            results.append(result)
            logger.info(
                "Completed congestion analysis for %s: %d candidates, %d corridors",
                network_id.value,
                len(result.candidates),
                len(result.corridors),
            )
        except Exception as e:
            errors.append(f"{network_id.value}: {e}")
            logger.error("Failed for %s: %s", network_id.value, e)

    if errors:
        msg = "Congestion analysis failed for: " + "; ".join(errors)
        raise RuntimeError(msg)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
