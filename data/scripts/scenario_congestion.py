"""Scenario-Driven Congestion Analysis for TINY (case39).

Re-runs DC power flow for each of 50 stochastic scenarios to determine how
renewable generation variability changes branch loading and flowgate
congestion patterns.

For each scenario and each hour:
  1. Apply scenario multiplier to renewable forecast → scenario-specific MW
  2. Inject renewable generation at placed buses
  3. Re-dispatch conventional generators to balance load minus renewables
  4. Solve DC power flow
  5. Compute branch flows and compare against flowgate limits

Output artifacts:
  - data/timeseries/case39/scenario_congestion/branch_loading_summary.csv
  - data/timeseries/case39/scenario_congestion/flowgate_violations.csv
  - data/timeseries/case39/scenario_congestion/congestion_statistics.json
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from scripts.tiny_flowgates import (
    BranchData,
    BranchFlowResult,
    BusData,
    FlowgateDefinition,
    GenData,
    build_b_matrix,
    compute_branch_flows,
    parse_matpower_case_extended,
    solve_dc_power_flow,
)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenewableUnit:
    """A renewable generator placed on the network."""

    gen_uid: str
    bus_id: int
    resource_type: str  # "wind" or "solar"
    pmax_mw: float


@dataclass(frozen=True)
class ScenarioHourResult:
    """Branch loading results for one scenario at one hour."""

    scenario: int
    hour: int  # 1-24 (hour-ending)
    total_load_mw: float
    total_renewable_mw: float
    total_conventional_mw: float
    max_loading_pct: float
    n_congested_80: int  # branches >= 80% loading
    n_congested_100: int  # branches >= 100% loading (overloaded)
    branch_flows: list[BranchFlowResult]


@dataclass(frozen=True)
class FlowgateViolation:
    """A single flowgate limit violation."""

    scenario: int
    hour: int
    flowgate_id: str
    flowgate_name: str
    max_branch_loading_pct: float
    weighted_flow_mw: float
    limit_mw: float
    margin_mw: float  # positive = within limit, negative = violation


@dataclass(frozen=True)
class BranchLoadingStats:
    """Per-branch loading statistics across all scenarios and hours."""

    branch_index: int
    from_bus: int
    to_bus: int
    rate_a_mw: float
    mean_loading_pct: float
    p50_loading_pct: float
    p95_loading_pct: float
    max_loading_pct: float
    prob_congested_80: float  # fraction of (scenario, hour) pairs >= 80%
    prob_congested_100: float  # fraction of (scenario, hour) pairs >= 100%
    worst_scenario: int
    worst_hour: int


@dataclass(frozen=True)
class CongestionAnalysisResult:
    """Top-level result container."""

    branch_stats: list[BranchLoadingStats]
    violations: list[FlowgateViolation]
    n_scenarios: int
    n_hours: int
    n_branches: int
    summary: dict


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_renewable_units(csv_path: Path) -> list[RenewableUnit]:
    """Load renewable unit definitions from renewable_units.csv."""
    units: list[RenewableUnit] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            units.append(
                RenewableUnit(
                    gen_uid=row["gen_uid"],
                    bus_id=int(row["bus_id"]),
                    resource_type=row["type"],
                    pmax_mw=float(row["pmax_mw"]),
                )
            )
    return units


def load_hourly_profiles(csv_path: Path) -> dict[str, list[float]]:
    """Load 24h profiles from a CSV with gen_uid, HR_1..HR_24 columns.

    Returns dict mapping gen_uid to list of 24 MW values.
    """
    profiles: dict[str, list[float]] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            gen_uid = row["gen_uid"]
            hourly = [float(row[f"HR_{h}"]) for h in range(1, 25)]
            profiles[gen_uid] = hourly
    return profiles


def load_load_profile(csv_path: Path) -> dict[int, list[float]]:
    """Load bus-level 24h load profile from load_24h.csv.

    Returns dict mapping bus_id to list of 24 hourly MW values.
    """
    result: dict[int, list[float]] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            bus_id = int(row["bus_id"])
            hourly = [float(row[f"HR_{h}"]) for h in range(1, 25)]
            result[bus_id] = hourly
    return result


def load_scenario_multipliers(
    csv_path: Path,
) -> dict[int, dict[str, list[float]]]:
    """Load scenario multipliers from scenario_multipliers_50x24.csv.

    Returns nested dict: scenario_id -> gen_uid -> list of 24 multipliers.
    """
    scenarios: dict[int, dict[str, list[float]]] = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            scenario = int(row["scenario"])
            gen_uid = row["gen_uid"]
            hourly = [float(row[f"HR_{h}"]) for h in range(1, 25)]
            if scenario not in scenarios:
                scenarios[scenario] = {}
            scenarios[scenario][gen_uid] = hourly
    return scenarios


def load_flowgate_definitions(csv_path: Path) -> list[FlowgateDefinition]:
    """Load flowgate definitions from flowgates.csv."""
    flowgates: list[FlowgateDefinition] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            branch_strs = row["branches"].split(";")
            from_buses = [int(s.split("-")[0]) for s in branch_strs]
            to_buses = [int(s.split("-")[1]) for s in branch_strs]
            weights = [float(w) for w in row["weights"].split(";")]

            # Recover branch indices by matching from/to bus pairs
            # (we'll resolve these against the actual branch list later)
            flowgates.append(
                FlowgateDefinition(
                    flowgate_id=row["flowgate_id"],
                    name=row["name"],
                    branches=[],  # resolved later
                    from_buses=from_buses,
                    to_buses=to_buses,
                    weights=weights,
                    limit_mw=float(row["limit_mw"]),
                    binding_load_level=row["binding_load_level"],
                    max_loading_pct=float(row["max_loading_pct"]),
                )
            )
    return flowgates


def resolve_flowgate_branch_indices(
    flowgates: list[FlowgateDefinition],
    branches: list[BranchData],
) -> list[FlowgateDefinition]:
    """Map flowgate bus pairs back to branch indices."""
    bus_pair_to_idx: dict[tuple[int, int], int] = {}
    for br in branches:
        bus_pair_to_idx[(br.from_bus, br.to_bus)] = br.branch_index
        bus_pair_to_idx[(br.to_bus, br.from_bus)] = br.branch_index

    resolved: list[FlowgateDefinition] = []
    for fg in flowgates:
        branch_indices = []
        for fb, tb in zip(fg.from_buses, fg.to_buses):
            idx = bus_pair_to_idx.get((fb, tb))
            if idx is not None:
                branch_indices.append(idx)
        resolved.append(
            FlowgateDefinition(
                flowgate_id=fg.flowgate_id,
                name=fg.name,
                branches=branch_indices,
                from_buses=fg.from_buses,
                to_buses=fg.to_buses,
                weights=fg.weights,
                limit_mw=fg.limit_mw,
                binding_load_level=fg.binding_load_level,
                max_loading_pct=fg.max_loading_pct,
            )
        )
    return resolved


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def dispatch_with_renewables(
    gens: list[GenData],
    renewable_mw_by_bus: dict[int, float],
    total_load_mw: float,
) -> dict[int, float]:
    """Dispatch conventional generators to balance load minus renewables.

    Reduces conventional dispatch proportionally to accommodate renewable
    injection, respecting Pmin/Pmax bounds.

    Args:
        gens: Conventional generator data.
        renewable_mw_by_bus: Renewable MW injection at each bus.
        total_load_mw: Total system load (MW).

    Returns:
        Dict mapping bus_id to total net injection (conventional + renewable).
    """
    total_renewable = sum(renewable_mw_by_bus.values())
    conventional_needed = max(0.0, total_load_mw - total_renewable)

    total_pmax = sum(g.pmax_mw for g in gens)
    if total_pmax <= 0.0:
        msg = "Total Pmax is zero or negative"
        raise ValueError(msg)

    # Proportional dispatch of conventional
    bus_gen: dict[int, float] = {}
    for g in gens:
        fraction = g.pmax_mw / total_pmax
        pg = fraction * conventional_needed
        pg = max(g.pmin_mw, min(g.pmax_mw, pg))
        bus_gen[g.bus_id] = bus_gen.get(g.bus_id, 0.0) + pg

    # Add renewable injection
    for bus_id, re_mw in renewable_mw_by_bus.items():
        bus_gen[bus_id] = bus_gen.get(bus_id, 0.0) + re_mw

    return bus_gen


def run_dcpf_scenario_hour(
    buses: list[BusData],
    gens: list[GenData],
    branches: list[BranchData],
    base_mva: float,
    ref_bus_id: int,
    b_matrix: np.ndarray,
    non_ref_bus_ids: list[int],
    bus_id_to_reduced_idx: dict[int, int],
    bus_loads: dict[int, float],
    renewable_mw_by_bus: dict[int, float],
    total_load_mw: float,
) -> list[BranchFlowResult]:
    """Run DC power flow for one scenario at one hour.

    Args:
        buses: Bus data.
        gens: Conventional generator data.
        branches: Branch data.
        base_mva: System base MVA.
        ref_bus_id: Reference bus ID.
        b_matrix: Pre-computed reduced B matrix.
        non_ref_bus_ids: Non-reference bus IDs.
        bus_id_to_reduced_idx: Mapping from bus ID to B-matrix index.
        bus_loads: Per-bus load (MW) for this hour.
        renewable_mw_by_bus: Renewable injection (MW) per bus.
        total_load_mw: Total system load (MW).

    Returns:
        List of BranchFlowResult for all branches.
    """
    gen_dispatch = dispatch_with_renewables(gens, renewable_mw_by_bus, total_load_mw)

    n_reduced = len(non_ref_bus_ids)
    p_inject = np.zeros(n_reduced)
    for bus_id in non_ref_bus_ids:
        idx = bus_id_to_reduced_idx[bus_id]
        gen_at_bus = gen_dispatch.get(bus_id, 0.0)
        load_at_bus = bus_loads.get(bus_id, 0.0)
        p_inject[idx] = (gen_at_bus - load_at_bus) / base_mva

    theta = solve_dc_power_flow(b_matrix, p_inject)
    return compute_branch_flows(theta, branches, non_ref_bus_ids, ref_bus_id, base_mva)


def check_flowgate_violations(
    flows: list[BranchFlowResult],
    flowgates: list[FlowgateDefinition],
    scenario: int,
    hour: int,
) -> list[FlowgateViolation]:
    """Check if any flowgate limits are violated.

    Computes weighted flow for each flowgate and compares to limit.
    """
    flow_map = {f.branch_index: f for f in flows}
    violations: list[FlowgateViolation] = []

    for fg in flowgates:
        weighted_flow = 0.0
        max_loading = 0.0
        for br_idx, weight in zip(fg.branches, fg.weights):
            if br_idx in flow_map:
                weighted_flow += abs(flow_map[br_idx].flow_mw) * weight
                max_loading = max(max_loading, flow_map[br_idx].loading_pct)

        margin = fg.limit_mw - weighted_flow
        violations.append(
            FlowgateViolation(
                scenario=scenario,
                hour=hour,
                flowgate_id=fg.flowgate_id,
                flowgate_name=fg.name,
                max_branch_loading_pct=max_loading,
                weighted_flow_mw=weighted_flow,
                limit_mw=fg.limit_mw,
                margin_mw=margin,
            )
        )

    return violations


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_branch_loading_csv(
    stats: list[BranchLoadingStats],
    dest_path: Path,
) -> None:
    """Write per-branch loading statistics to CSV."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "branch_index",
        "from_bus",
        "to_bus",
        "rate_a_mw",
        "mean_loading_pct",
        "p50_loading_pct",
        "p95_loading_pct",
        "max_loading_pct",
        "prob_congested_80",
        "prob_congested_100",
        "worst_scenario",
        "worst_hour",
    ]
    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for s in stats:
            writer.writerow(
                [
                    s.branch_index,
                    s.from_bus,
                    s.to_bus,
                    f"{s.rate_a_mw:.2f}",
                    f"{s.mean_loading_pct:.2f}",
                    f"{s.p50_loading_pct:.2f}",
                    f"{s.p95_loading_pct:.2f}",
                    f"{s.max_loading_pct:.2f}",
                    f"{s.prob_congested_80:.4f}",
                    f"{s.prob_congested_100:.4f}",
                    s.worst_scenario,
                    s.worst_hour,
                ]
            )


def write_violations_csv(
    violations: list[FlowgateViolation],
    dest_path: Path,
) -> None:
    """Write flowgate violations to CSV."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "scenario",
        "hour",
        "flowgate_id",
        "flowgate_name",
        "max_branch_loading_pct",
        "weighted_flow_mw",
        "limit_mw",
        "margin_mw",
    ]
    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for v in violations:
            writer.writerow(
                [
                    v.scenario,
                    v.hour,
                    v.flowgate_id,
                    v.flowgate_name,
                    f"{v.max_branch_loading_pct:.2f}",
                    f"{v.weighted_flow_mw:.2f}",
                    f"{v.limit_mw:.2f}",
                    f"{v.margin_mw:.2f}",
                ]
            )


def write_statistics_json(result: CongestionAnalysisResult, dest_path: Path) -> None:
    """Write analysis statistics to JSON."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "script_version": __version__,
        "n_scenarios": result.n_scenarios,
        "n_hours": result.n_hours,
        "n_branches": result.n_branches,
        "summary": result.summary,
        "top_congested_branches": [
            asdict(s)
            for s in sorted(result.branch_stats, key=lambda x: x.max_loading_pct, reverse=True)[:10]
        ],
    }

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main(
    data_dir: Path | None = None,
) -> CongestionAnalysisResult:
    """Entry point: run scenario congestion analysis.

    Runs DC power flow for all 50 scenarios across all 24 hours, computing
    branch loading and flowgate violation statistics.

    Args:
        data_dir: Path to data/timeseries/case39/. Defaults to
            <repo_root>/data/timeseries/case39/.

    Returns:
        CongestionAnalysisResult with full statistics.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if data_dir is None:
        data_dir = repo_root / "timeseries" / "case39"

    # Load case data
    m_file = data_dir / "case39.m"
    buses, gens, branches, base_mva = parse_matpower_case_extended(m_file)
    ref_bus_id = next(b.bus_id for b in buses if b.bus_type == 3)

    # Pre-compute B matrix (same for all scenarios)
    b_matrix, non_ref_bus_ids = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    bus_id_to_reduced_idx = {bid: i for i, bid in enumerate(non_ref_bus_ids)}

    # Load profiles
    load_profile = load_load_profile(data_dir / "load_24h.csv")
    renewable_units = load_renewable_units(data_dir / "renewable_units.csv")
    forecast_wind = load_hourly_profiles(data_dir / "wind_forecast_24h.csv")
    forecast_solar = load_hourly_profiles(data_dir / "solar_forecast_24h.csv")
    forecasts = {**forecast_wind, **forecast_solar}

    # Load scenarios and flowgates
    scenarios = load_scenario_multipliers(data_dir / "scenarios" / "scenario_multipliers_50x24.csv")
    flowgates = load_flowgate_definitions(data_dir / "flowgates.csv")
    flowgates = resolve_flowgate_branch_indices(flowgates, branches)

    n_scenarios = len(scenarios)
    n_hours = 24
    n_branches = len(branches)

    # Collect all branch loadings: branch_index -> list of (loading_pct, scenario, hour)
    all_loadings: dict[int, list[tuple[float, int, int]]] = {br.branch_index: [] for br in branches}
    all_violations: list[FlowgateViolation] = []

    scenario_ids = sorted(scenarios.keys())

    for scenario_id in scenario_ids:
        multipliers = scenarios[scenario_id]

        for hour_idx in range(n_hours):
            hour = hour_idx + 1  # 1-based hour-ending

            # Bus loads at this hour
            bus_loads: dict[int, float] = {
                bus_id: hourly[hour_idx] for bus_id, hourly in load_profile.items()
            }
            total_load = sum(bus_loads.values())

            # Renewable MW at each bus for this scenario + hour
            renewable_mw_by_bus: dict[int, float] = {}
            total_renewable = 0.0
            for unit in renewable_units:
                forecast = forecasts.get(unit.gen_uid)
                mult = multipliers.get(unit.gen_uid)
                if forecast is None or mult is None:
                    continue
                mw = min(forecast[hour_idx] * mult[hour_idx], unit.pmax_mw)
                mw = max(mw, 0.0)
                renewable_mw_by_bus[unit.bus_id] = renewable_mw_by_bus.get(unit.bus_id, 0.0) + mw
                total_renewable += mw

            # Run DCPF
            flows = run_dcpf_scenario_hour(
                buses,
                gens,
                branches,
                base_mva,
                ref_bus_id,
                b_matrix,
                non_ref_bus_ids,
                bus_id_to_reduced_idx,
                bus_loads,
                renewable_mw_by_bus,
                total_load,
            )

            # Record branch loadings
            for f in flows:
                all_loadings[f.branch_index].append((f.loading_pct, scenario_id, hour))

            # Check flowgate violations
            violations = check_flowgate_violations(flows, flowgates, scenario_id, hour)
            # Only record actual violations (margin < 0)
            all_violations.extend(v for v in violations if v.margin_mw < 0)

    # Compute per-branch statistics
    branch_stats: list[BranchLoadingStats] = []
    total_points = n_scenarios * n_hours

    for br in branches:
        loadings = all_loadings[br.branch_index]
        pcts = [x[0] for x in loadings]
        pcts_arr = np.array(pcts)

        worst_idx = int(np.argmax(pcts_arr))
        _, worst_scenario, worst_hour = loadings[worst_idx]

        branch_stats.append(
            BranchLoadingStats(
                branch_index=br.branch_index,
                from_bus=br.from_bus,
                to_bus=br.to_bus,
                rate_a_mw=br.rate_a_mw,
                mean_loading_pct=float(np.mean(pcts_arr)),
                p50_loading_pct=float(np.median(pcts_arr)),
                p95_loading_pct=float(np.percentile(pcts_arr, 95)),
                max_loading_pct=float(np.max(pcts_arr)),
                prob_congested_80=float(np.sum(pcts_arr >= 80.0)) / total_points,
                prob_congested_100=float(np.sum(pcts_arr >= 100.0)) / total_points,
                worst_scenario=worst_scenario,
                worst_hour=worst_hour,
            )
        )

    # Build summary
    n_branches_ever_congested_80 = sum(1 for s in branch_stats if s.max_loading_pct >= 80.0)
    n_branches_ever_congested_100 = sum(1 for s in branch_stats if s.max_loading_pct >= 100.0)
    n_violation_events = len(all_violations)
    unique_violation_scenarios = len({v.scenario for v in all_violations})

    # Congestion variability: how much does max loading vary across scenarios?
    # For each branch, compute std dev of loading across (scenario, hour) pairs
    high_variability_branches = []
    for s in branch_stats:
        loadings = all_loadings[s.branch_index]
        pcts = [x[0] for x in loadings]
        std = float(np.std(pcts))
        if std > 5.0:  # >5 percentage points of variability
            high_variability_branches.append(
                {
                    "branch": f"{s.from_bus}-{s.to_bus}",
                    "branch_index": s.branch_index,
                    "loading_std_pct": round(std, 2),
                    "mean_loading_pct": round(s.mean_loading_pct, 2),
                    "p95_loading_pct": round(s.p95_loading_pct, 2),
                    "max_loading_pct": round(s.max_loading_pct, 2),
                }
            )

    # Per-scenario peak loading to show scenario-to-scenario variation
    scenario_peaks: dict[int, float] = {}
    for sid in scenario_ids:
        peak = 0.0
        for br in branches:
            for pct, s, h in all_loadings[br.branch_index]:
                if s == sid and pct > peak:
                    peak = pct
        scenario_peaks[sid] = peak

    peak_values = list(scenario_peaks.values())

    summary = {
        "total_scenario_hour_pairs": total_points,
        "n_branches_ever_congested_80pct": n_branches_ever_congested_80,
        "n_branches_ever_congested_100pct": n_branches_ever_congested_100,
        "n_flowgate_violation_events": n_violation_events,
        "n_scenarios_with_violations": unique_violation_scenarios,
        "scenario_peak_loading_min": round(min(peak_values), 2),
        "scenario_peak_loading_max": round(max(peak_values), 2),
        "scenario_peak_loading_mean": round(float(np.mean(peak_values)), 2),
        "scenario_peak_loading_std": round(float(np.std(peak_values)), 2),
        "high_variability_branches": sorted(
            high_variability_branches, key=lambda x: x["loading_std_pct"], reverse=True
        ),
    }

    result = CongestionAnalysisResult(
        branch_stats=branch_stats,
        violations=all_violations,
        n_scenarios=n_scenarios,
        n_hours=n_hours,
        n_branches=n_branches,
        summary=summary,
    )

    # Write outputs
    out_dir = data_dir / "scenario_congestion"
    write_branch_loading_csv(branch_stats, out_dir / "branch_loading_summary.csv")
    write_violations_csv(all_violations, out_dir / "flowgate_violations.csv")
    write_statistics_json(result, out_dir / "congestion_statistics.json")

    # Print summary
    _print_summary(result)

    return result


def _print_summary(result: CongestionAnalysisResult) -> None:
    """Print a human-readable summary to stdout."""
    s = result.summary
    print("=" * 72)
    print("  Scenario Congestion Analysis — TINY (case39)")
    print("=" * 72)
    print(
        f"  Scenarios: {result.n_scenarios}  |  Hours: {result.n_hours}"
        f"  |  Branches: {result.n_branches}"
    )
    print(f"  Total (scenario × hour) pairs analyzed: {s['total_scenario_hour_pairs']}")
    print()
    print(f"  Branches ever >= 80% loading:  {s['n_branches_ever_congested_80pct']}")
    print(f"  Branches ever >= 100% loading: {s['n_branches_ever_congested_100pct']}")
    print(f"  Flowgate violation events:     {s['n_flowgate_violation_events']}")
    print(
        f"  Scenarios with violations:     {s['n_scenarios_with_violations']}"
        f" / {result.n_scenarios}"
    )
    print()
    print("  Peak loading across scenarios:")
    print(f"    Min:  {s['scenario_peak_loading_min']:.1f}%")
    print(f"    Mean: {s['scenario_peak_loading_mean']:.1f}%")
    print(f"    Max:  {s['scenario_peak_loading_max']:.1f}%")
    print(f"    Std:  {s['scenario_peak_loading_std']:.1f}%")
    print()

    if s["high_variability_branches"]:
        print("  Branches with high loading variability (σ > 5%):")
        fmt = "    {branch:>8s}  mean={mean_loading_pct:5.1f}%  p95={p95_loading_pct:5.1f}%"
        fmt += "  max={max_loading_pct:5.1f}%  σ={loading_std_pct:5.1f}%"
        for br in s["high_variability_branches"][:10]:
            print(fmt.format(**br))
    else:
        print("  No branches with high loading variability (σ > 5%)")

    print()


if __name__ == "__main__":
    main()
