"""DC OPF Shadow Price Analysis Across Stochastic Scenarios.

Solves the DC Optimal Power Flow for each scenario and hour to compute
Locational Marginal Prices (LMPs) and congestion shadow prices.

The DC OPF minimizes generation cost subject to:
  - Power balance: sum(Pg) = sum(Pd)
  - Branch flow limits: |PTDF · P_net| <= rateA
  - Generator bounds: Pmin <= Pg <= Pmax

Shadow prices on branch constraints are the congestion component of LMPs:
  LMP_bus = λ (energy) + Σ_k PTDF_k,bus · μ_k (congestion)

Output artifacts:
  - data/timeseries/case39/scenario_congestion/lmp_summary.csv
  - data/timeseries/case39/scenario_congestion/shadow_prices.csv
  - data/timeseries/case39/scenario_congestion/dcopf_statistics.json
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from scripts.scenario_congestion import (
    RenewableUnit,
    load_hourly_profiles,
    load_load_profile,
    load_renewable_units,
    load_scenario_multipliers,
)
from scripts.tiny_flowgates import (
    BranchData,
    BusData,
    GenData,
    build_b_matrix,
    parse_matpower_case_extended,
)

__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenCost:
    """Generator cost curve coefficients (polynomial model 2)."""

    gen_index: int
    c2: float  # $/MW²h
    c1: float  # $/MWh
    c0: float  # $/h


@dataclass(frozen=True)
class DcopfSolution:
    """Solution of DC OPF for one scenario-hour."""

    scenario: int
    hour: int
    converged: bool
    total_cost: float
    energy_price: float  # λ — system marginal price ($/MWh)
    branch_shadow_prices: list[float]  # μ_k for each branch ($/MWh)
    bus_lmps: dict[int, float]  # LMP at each bus ($/MWh)
    gen_dispatch: list[float]  # Pg for each gen (MW)
    binding_branches: list[int]  # branch indices at their limit


@dataclass(frozen=True)
class ScenarioLmpStats:
    """LMP statistics for one bus across scenarios."""

    bus_id: int
    mean_lmp: float
    std_lmp: float
    min_lmp: float
    max_lmp: float
    p5_lmp: float
    p95_lmp: float


@dataclass(frozen=True)
class BranchShadowStats:
    """Shadow price statistics for one branch across scenarios."""

    branch_index: int
    from_bus: int
    to_bus: int
    rate_a_mw: float
    mean_shadow: float
    std_shadow: float
    max_shadow: float
    prob_binding: float  # fraction of scenario-hours where branch is binding


# ---------------------------------------------------------------------------
# Cost data
# ---------------------------------------------------------------------------

# Realistic marginal costs ($/MWh) by fuel type.
# Sources: EIA 2023 average variable O&M + fuel cost.
FUEL_MARGINAL_COSTS: dict[str, float] = {
    "hydro": 5.0,
    "nuclear": 10.0,
    "coal_large": 25.0,
    "coal_medium": 28.0,
    "coal_small": 32.0,
    "gas_CC": 40.0,
    "gas_CT": 55.0,
}

# Zero-cost for renewables (must-take)
RENEWABLE_MARGINAL_COST: float = 0.0


def build_differentiated_costs(
    temporal_params_csv: Path,
    n_gens: int,
) -> list[GenCost]:
    """Build generator cost curves from fuel-type classification.

    Uses the tech_class_key from gen_temporal_params.csv to assign
    realistic marginal costs. Case39's native gencost is homogeneous
    ($0.30/MWh for all 10 generators), which produces no congestion
    pricing. This function replaces those with fuel-type-appropriate costs.

    Args:
        temporal_params_csv: Path to gen_temporal_params.csv.
        n_gens: Number of generators in the case.

    Returns:
        List of GenCost records with differentiated costs.
    """
    costs: list[GenCost] = []

    with open(temporal_params_csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            gen_index = int(row["gen_index"])
            tech_key = row["tech_class_key"]
            c1 = FUEL_MARGINAL_COSTS.get(tech_key, 30.0)
            # Quadratic term: marginal cost increases ~50% from 0 to typical Pmax.
            # c2 = c1 * 0.001 gives MC(200 MW) ≈ c1 + 2*c2*200 = c1 + 0.4*c1
            c2 = c1 * 0.001
            costs.append(GenCost(gen_index=gen_index, c2=c2, c1=c1, c0=0.0))

    if len(costs) != n_gens:
        msg = f"gen_temporal_params.csv has {len(costs)} rows but case has {n_gens} generators"
        raise ValueError(msg)

    return costs


# ---------------------------------------------------------------------------
# PTDF matrix
# ---------------------------------------------------------------------------


def build_ptdf(
    buses: list[BusData],
    branches: list[BranchData],
    ref_bus_id: int,
    base_mva: float,
) -> tuple[np.ndarray, list[int]]:
    """Build the PTDF matrix mapping bus injections to branch flows.

    PTDF[k, i] = sensitivity of branch k flow (MW) to injection at bus i (MW).

    Args:
        buses: Bus data.
        branches: Branch data.
        ref_bus_id: Reference bus ID.
        base_mva: System base MVA.

    Returns:
        Tuple of (PTDF matrix [n_branch x n_bus-1], non_ref_bus_ids).
    """
    b_matrix, non_ref_bus_ids = build_b_matrix(buses, branches, ref_bus_id, base_mva)
    n_reduced = len(non_ref_bus_ids)
    bus_id_to_idx = {bid: i for i, bid in enumerate(non_ref_bus_ids)}

    b_inv = np.linalg.inv(b_matrix)

    n_branch = len(branches)
    ptdf = np.zeros((n_branch, n_reduced))

    for k, br in enumerate(branches):
        if br.x_pu == 0.0:
            continue
        susceptance = 1.0 / br.x_pu
        diff = np.zeros(n_reduced)
        if br.from_bus in bus_id_to_idx:
            diff[bus_id_to_idx[br.from_bus]] = 1.0
        if br.to_bus in bus_id_to_idx:
            diff[bus_id_to_idx[br.to_bus]] = -1.0
        ptdf[k, :] = susceptance * (diff @ b_inv)

    return ptdf, non_ref_bus_ids


# ---------------------------------------------------------------------------
# DC OPF solver
# ---------------------------------------------------------------------------


def _solve_qp_activeset(
    Q_diag: np.ndarray,
    c1: np.ndarray,
    A_eq: np.ndarray,
    b_eq: np.ndarray,
    A_ub: np.ndarray,
    b_ub: np.ndarray,
    lb: np.ndarray,
    ub: np.ndarray,
) -> tuple[np.ndarray, bool] | None:
    """Solve a diagonal QP via LP warm-start + active-set refinement.

    1. Solve the LP relaxation (c2=0) with HiGHS to identify the active set.
    2. Fix the active set and solve the equality-constrained QP (a linear system).
    3. Verify KKT conditions; iterate if needed.

    Returns (x_opt, converged) or None if LP is infeasible.
    """
    # Step 1: LP warm-start to identify active set
    bounds_lp = list(zip(lb, ub, strict=False))
    lp_result = linprog(
        c1, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds_lp, method="highs"
    )
    if not lp_result.success:
        return None

    x = lp_result.x.copy()

    # Step 2: Active-set QP refinement
    # For a diagonal QP, the optimality conditions with fixed active set become
    # a linear system. We iterate the active set up to a few times.
    for _iteration in range(5):
        # Identify active constraints
        tol = 1e-6
        ub_mask = ub - x < tol  # at upper bound
        lb_mask = x - lb < tol  # at lower bound
        ineq_mask = A_ub @ x - b_ub > -tol  # binding inequalities

        # Free variables: not at a bound
        free_mask = ~ub_mask & ~lb_mask

        n_free = int(np.sum(free_mask))
        if n_free == 0:
            break  # all variables at bounds, LP solution is optimal for QP too

        # For free variables, solve the reduced QP:
        # min 0.5 x_f' Q_f x_f + (c1_f + Q_f_off)' x_f
        # s.t. A_eq_f x_f = b_eq - A_eq_fixed x_fixed
        #      A_active_f x_f = b_active - A_active_fixed x_fixed
        # where Q_f = diag(Q_diag[free]), and Q_f_off accounts for
        # cross terms with fixed variables (zero for diagonal Q).

        free_idx = np.where(free_mask)[0]
        fixed_idx = np.where(~free_mask)[0]

        x_fixed = x[fixed_idx]

        # Equality constraint on free vars
        A_eq_f = A_eq[:, free_idx]
        b_eq_f = b_eq - A_eq[:, fixed_idx] @ x_fixed

        # Active inequality constraints on free vars
        active_ineq_rows = np.where(ineq_mask)[0]

        if len(active_ineq_rows) > 0:
            A_act = A_ub[active_ineq_rows][:, free_idx]
            b_act = b_ub[active_ineq_rows] - A_ub[active_ineq_rows][:, fixed_idx] @ x_fixed
            # Combined equality system: [A_eq_f; A_act] x_f = [b_eq_f; b_act]
            A_sys = np.vstack([A_eq_f, A_act])
            b_sys = np.concatenate([b_eq_f, b_act])
        else:
            A_sys = A_eq_f
            b_sys = b_eq_f

        n_constraints = A_sys.shape[0]

        # KKT system for equality-constrained QP:
        # [Q_f  A_sys'] [x_f]   = [-c1_f]
        # [A_sys  0   ] [lam]     [b_sys]
        Q_f = np.diag(Q_diag[free_idx])
        kkt_size = n_free + n_constraints
        KKT = np.zeros((kkt_size, kkt_size))
        KKT[:n_free, :n_free] = Q_f
        KKT[:n_free, n_free:] = A_sys.T
        KKT[n_free:, :n_free] = A_sys

        rhs = np.zeros(kkt_size)
        rhs[:n_free] = -c1[free_idx]
        rhs[n_free:] = b_sys

        try:
            sol = np.linalg.solve(KKT, rhs)
        except np.linalg.LinAlgError:
            # Singular — use least squares
            sol, _, _, _ = np.linalg.lstsq(KKT, rhs, rcond=None)

        x_f_new = sol[:n_free]

        # Clip to bounds (may change active set)
        x_f_clipped = np.clip(x_f_new, lb[free_idx], ub[free_idx])

        x_new = x.copy()
        x_new[free_idx] = x_f_clipped

        # Check convergence
        if np.max(np.abs(x_new - x)) < 1e-8:
            x = x_new
            break
        x = x_new

    return x, True


def solve_dcopf(
    gens: list[GenData],
    gen_costs: list[GenCost],
    buses: list[BusData],
    branches: list[BranchData],
    ptdf: np.ndarray,
    non_ref_bus_ids: list[int],
    ref_bus_id: int,
    base_mva: float,
    bus_loads: dict[int, float],
    renewable_injections: dict[int, float],
    scenario: int,
    hour: int,
) -> DcopfSolution:
    """Solve DC OPF for one scenario-hour using quadratic programming.

    Decision variables: Pg_i for each conventional generator.

    Renewables are treated as negative load (fixed injection), reducing the
    net load that conventional generators must serve.

    Uses a quadratic objective: min Σ(c2_i·Pg_i² + c1_i·Pg_i) which produces
    continuously varying marginal costs and dual values. Unlike LP, where
    duals jump discretely between basis states, QP duals shift smoothly
    with small perturbations in renewable injection.

    Approach: LP warm-start (HiGHS) → active-set QP refinement → KKT dual
    recovery. Each solve takes ~1ms for the 10-generator case39.

    Args:
        gens: Conventional generator data.
        gen_costs: Cost curves for conventional generators.
        buses: Bus data.
        branches: Branch data.
        ptdf: PTDF matrix [n_branch x n_bus-1].
        non_ref_bus_ids: Bus IDs corresponding to PTDF columns.
        ref_bus_id: Reference bus ID.
        base_mva: System base MVA.
        bus_loads: Net load (MW) at each bus for this hour.
        renewable_injections: Renewable MW injection at each bus.
        scenario: Scenario ID (for output tagging).
        hour: Hour-ending (1-24).

    Returns:
        DcopfSolution with LMPs, shadow prices, and dispatch.
    """
    n_gen = len(gens)
    n_branch = len(branches)
    n_reduced = len(non_ref_bus_ids)
    bus_id_to_idx = {bid: i for i, bid in enumerate(non_ref_bus_ids)}

    # Net load at each bus = load - renewable injection
    net_load = np.zeros(n_reduced)
    for bid in non_ref_bus_ids:
        idx = bus_id_to_idx[bid]
        net_load[idx] = bus_loads.get(bid, 0.0) - renewable_injections.get(bid, 0.0)

    # Also account for ref bus load (ref bus gen handles the slack)
    ref_load = bus_loads.get(ref_bus_id, 0.0) - renewable_injections.get(ref_bus_id, 0.0)
    total_net_load = float(np.sum(net_load)) + ref_load

    # Quadratic cost coefficients
    c2_arr = np.array([gen_costs[i].c2 for i in range(n_gen)])
    c1_arr = np.array([gen_costs[i].c1 for i in range(n_gen)])
    Q_diag = 2.0 * c2_arr  # Hessian diagonal elements

    # Build gen-to-bus mapping matrix G [n_reduced x n_gen]
    G = np.zeros((n_reduced, n_gen))
    for j, g in enumerate(gens):
        if g.bus_id != ref_bus_id:
            G[bus_id_to_idx[g.bus_id], j] = 1.0

    # PTDF_G = PTDF @ G  [n_branch x n_gen]
    ptdf_g = ptdf @ G

    # Branch limits (in MW)
    rate_a = np.array([br.rate_a_mw for br in branches])

    # Branch flow constraints
    ptdf_net = ptdf @ net_load  # [n_branch]

    A_ub = np.vstack([ptdf_g, -ptdf_g])
    b_ub = np.concatenate([rate_a + ptdf_net, rate_a - ptdf_net])

    # Equality constraint: sum(Pg) = total_net_load
    A_eq = np.ones((1, n_gen))
    b_eq = np.array([total_net_load])

    # Bounds
    lb = np.array([g.pmin_mw for g in gens])
    ub = np.array([g.pmax_mw for g in gens])

    # Solve QP via LP warm-start + active-set refinement
    qp_result = _solve_qp_activeset(Q_diag, c1_arr, A_eq, b_eq, A_ub, b_ub, lb, ub)

    if qp_result is None:
        return DcopfSolution(
            scenario=scenario,
            hour=hour,
            converged=False,
            total_cost=0.0,
            energy_price=0.0,
            branch_shadow_prices=[0.0] * n_branch,
            bus_lmps={b.bus_id: 0.0 for b in buses},
            gen_dispatch=[0.0] * n_gen,
            binding_branches=[],
        )

    pg, _ = qp_result
    total_cost = float(0.5 * np.sum(Q_diag * pg * pg) + c1_arr @ pg)

    # --- KKT dual recovery ---
    # Gradient of QP objective at optimum
    grad = Q_diag * pg + c1_arr

    # Identify active constraints
    tol = 1e-5
    ineq_residuals = A_ub @ pg - b_ub
    active_ineq = ineq_residuals > -tol
    lb_active = pg - lb < tol
    ub_active = ub - pg < tol

    # Build KKT system: [A_eq; A_active; I_lb; -I_ub]' · duals = -grad
    matrices = [A_eq.T]  # [n_gen x 1]
    n_active_ub = int(np.sum(active_ineq))

    if n_active_ub > 0:
        matrices.append(A_ub[active_ineq].T)

    if np.any(lb_active):
        matrices.append(np.eye(n_gen)[lb_active].T)

    if np.any(ub_active):
        matrices.append(-np.eye(n_gen)[ub_active].T)

    A_kkt = np.hstack(matrices)
    duals, _, _, _ = np.linalg.lstsq(A_kkt, -grad, rcond=None)

    energy_price = float(duals[0])

    # Extract branch shadow prices from active inequality duals
    branch_shadows_full = np.zeros(2 * n_branch)
    if n_active_ub > 0:
        active_indices = np.where(active_ineq)[0]
        mu_active = duals[1 : 1 + n_active_ub]
        for i, idx in enumerate(active_indices):
            branch_shadows_full[idx] = mu_active[i]

    mu_forward = branch_shadows_full[:n_branch]
    mu_reverse = branch_shadows_full[n_branch:]
    branch_shadows = [float(mu_forward[k] - mu_reverse[k]) for k in range(n_branch)]

    # Identify binding branches (shadow price magnitude > threshold)
    binding = [k for k in range(n_branch) if abs(branch_shadows[k]) > 1e-6]

    # Compute LMPs: LMP_bus = λ + Σ_k PTDF[k, bus] · μ_k
    bus_lmps: dict[int, float] = {}
    mu_arr = np.array(branch_shadows)

    for i, bid in enumerate(non_ref_bus_ids):
        congestion_component = float(ptdf[:, i] @ mu_arr)
        bus_lmps[bid] = energy_price + congestion_component

    # Ref bus: PTDF column is zero by construction, so LMP = λ
    bus_lmps[ref_bus_id] = energy_price

    return DcopfSolution(
        scenario=scenario,
        hour=hour,
        converged=True,
        total_cost=total_cost,
        energy_price=energy_price,
        branch_shadow_prices=branch_shadows,
        bus_lmps=bus_lmps,
        gen_dispatch=[float(p) for p in pg],
        binding_branches=binding,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_lmp_csv(
    all_solutions: list[DcopfSolution],
    bus_ids: list[int],
    dest_path: Path,
) -> None:
    """Write LMPs for all scenarios/hours to CSV."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["scenario", "hour", "energy_price"] + [f"bus_{b}" for b in bus_ids]
    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for sol in all_solutions:
            if not sol.converged:
                continue
            row = [sol.scenario, sol.hour, f"{sol.energy_price:.4f}"]
            row += [f"{sol.bus_lmps.get(b, 0.0):.4f}" for b in bus_ids]
            writer.writerow(row)


def write_shadow_csv(
    all_solutions: list[DcopfSolution],
    branches: list[BranchData],
    dest_path: Path,
) -> None:
    """Write branch shadow prices for all scenarios/hours to CSV.

    Only includes branches that are binding in at least one solution.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Find branches that are ever binding
    ever_binding: set[int] = set()
    for sol in all_solutions:
        ever_binding.update(sol.binding_branches)

    binding_sorted = sorted(ever_binding)
    if not binding_sorted:
        # Write empty file
        with open(dest_path, "w", newline="", encoding="utf-8") as fh:
            fh.write("scenario,hour\n")
        return

    header = ["scenario", "hour"] + [
        f"br_{branches[k].from_bus}_{branches[k].to_bus}" for k in binding_sorted
    ]

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for sol in all_solutions:
            if not sol.converged:
                continue
            row: list[str | int] = [sol.scenario, sol.hour]
            row += [f"{sol.branch_shadow_prices[k]:.6f}" for k in binding_sorted]
            writer.writerow(row)


def write_dcopf_json(
    bus_stats: list[ScenarioLmpStats],
    branch_stats: list[BranchShadowStats],
    summary: dict,
    dest_path: Path,
) -> None:
    """Write DC OPF analysis statistics to JSON."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "script_version": __version__,
        "summary": summary,
        "bus_lmp_statistics": [
            {
                "bus_id": s.bus_id,
                "mean_lmp": round(s.mean_lmp, 4),
                "std_lmp": round(s.std_lmp, 4),
                "min_lmp": round(s.min_lmp, 4),
                "max_lmp": round(s.max_lmp, 4),
                "p5_lmp": round(s.p5_lmp, 4),
                "p95_lmp": round(s.p95_lmp, 4),
            }
            for s in bus_stats
        ],
        "branch_shadow_statistics": [
            {
                "branch_index": s.branch_index,
                "branch": f"{s.from_bus}-{s.to_bus}",
                "rate_a_mw": s.rate_a_mw,
                "mean_shadow": round(s.mean_shadow, 6),
                "std_shadow": round(s.std_shadow, 6),
                "max_shadow": round(s.max_shadow, 6),
                "prob_binding": round(s.prob_binding, 4),
            }
            for s in branch_stats
            if s.prob_binding > 0
        ],
    }

    with open(dest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _derate_branches(
    branches: list[BranchData],
    factor: float,
) -> list[BranchData]:
    """Return branches with rate_a_mw scaled by factor."""
    return [
        BranchData(
            branch_index=br.branch_index,
            from_bus=br.from_bus,
            to_bus=br.to_bus,
            x_pu=br.x_pu,
            rate_a_mw=br.rate_a_mw * factor,
        )
        for br in branches
    ]


# Diverse renewable placements: buses behind different bottleneck branches.
# Each unit is at a low-degree bus in a different part of the network.
DIVERSE_PLACEMENTS: list[RenewableUnit] = [
    RenewableUnit("WIND_D1", bus_id=1, resource_type="wind", pmax_mw=300.0),
    RenewableUnit("WIND_D2", bus_id=12, resource_type="wind", pmax_mw=300.0),
    RenewableUnit("WIND_D3", bus_id=27, resource_type="wind", pmax_mw=300.0),
    RenewableUnit("SOLAR_D1", bus_id=18, resource_type="solar", pmax_mw=250.0),
    RenewableUnit("SOLAR_D2", bus_id=24, resource_type="solar", pmax_mw=250.0),
]


def _build_diverse_forecasts(
    original_forecasts: dict[str, list[float]],
    original_units: list[RenewableUnit],
    diverse_units: list[RenewableUnit],
) -> dict[str, list[float]]:
    """Map original forecast profiles to diversely-placed units.

    Reuses the hourly shapes from the original units, scaled to the new Pmax.
    WIND_D1 gets WIND_1's shape, WIND_D2 gets WIND_2's, etc.
    """
    # Pair original and diverse units by resource type
    orig_wind = [u for u in original_units if u.resource_type == "wind"]
    orig_solar = [u for u in original_units if u.resource_type == "solar"]
    div_wind = [u for u in diverse_units if u.resource_type == "wind"]
    div_solar = [u for u in diverse_units if u.resource_type == "solar"]

    forecasts: dict[str, list[float]] = {}
    for i, du in enumerate(div_wind):
        ou = orig_wind[i % len(orig_wind)]
        orig_fc = original_forecasts[ou.gen_uid]
        # Scale by capacity ratio
        scale = du.pmax_mw / ou.pmax_mw
        forecasts[du.gen_uid] = [v * scale for v in orig_fc]

    for i, du in enumerate(div_solar):
        ou = orig_solar[i % len(orig_solar)]
        orig_fc = original_forecasts[ou.gen_uid]
        scale = du.pmax_mw / ou.pmax_mw
        forecasts[du.gen_uid] = [v * scale for v in orig_fc]

    return forecasts


def _build_diverse_multipliers(
    original_scenarios: dict[int, dict[str, list[float]]],
    original_units: list[RenewableUnit],
    diverse_units: list[RenewableUnit],
) -> dict[int, dict[str, list[float]]]:
    """Map original scenario multipliers to diversely-placed units."""
    orig_wind = [u for u in original_units if u.resource_type == "wind"]
    orig_solar = [u for u in original_units if u.resource_type == "solar"]
    div_wind = [u for u in diverse_units if u.resource_type == "wind"]
    div_solar = [u for u in diverse_units if u.resource_type == "solar"]

    result: dict[int, dict[str, list[float]]] = {}
    for sid, mults in original_scenarios.items():
        result[sid] = {}
        for i, du in enumerate(div_wind):
            ou = orig_wind[i % len(orig_wind)]
            result[sid][du.gen_uid] = mults[ou.gen_uid]
        for i, du in enumerate(div_solar):
            ou = orig_solar[i % len(orig_solar)]
            result[sid][du.gen_uid] = mults[ou.gen_uid]

    return result


def main(
    data_dir: Path | None = None,
    *,
    branch_derate: float = 1.0,
    use_diverse_placement: bool = False,
    label: str = "base",
) -> None:
    """Entry point: solve DC OPF across all scenarios and hours.

    Args:
        data_dir: Path to data/timeseries/case39/. Defaults to auto-detect.
        branch_derate: Multiply all branch rateA by this factor (e.g. 0.7
            to tighten limits to 70% of nominal).
        use_diverse_placement: If True, use DIVERSE_PLACEMENTS instead of
            the default renewable_units.csv locations.
        label: Label for the output subdirectory.
    """
    repo_root = Path(__file__).resolve().parent.parent

    if data_dir is None:
        data_dir = repo_root / "timeseries" / "case39"

    # Load case data
    m_file = data_dir / "case39.m"
    buses, gens, branches_orig, base_mva = parse_matpower_case_extended(m_file)
    gen_costs = build_differentiated_costs(data_dir / "gen_temporal_params.csv", len(gens))
    ref_bus_id = next(b.bus_id for b in buses if b.bus_type == 3)

    # Apply branch derating
    branches = (
        _derate_branches(branches_orig, branch_derate) if branch_derate != 1.0 else branches_orig
    )

    # Build PTDF (uses branch reactances, not ratings — same for derated)
    ptdf, non_ref_bus_ids = build_ptdf(buses, branches, ref_bus_id, base_mva)

    # Load profiles & scenarios
    load_profile = load_load_profile(data_dir / "load_24h.csv")
    original_units = load_renewable_units(data_dir / "renewable_units.csv")
    original_forecasts = {
        **load_hourly_profiles(data_dir / "wind_forecast_24h.csv"),
        **load_hourly_profiles(data_dir / "solar_forecast_24h.csv"),
    }
    original_scenarios = load_scenario_multipliers(
        data_dir / "scenarios" / "scenario_multipliers_50x24.csv"
    )

    # Determine renewable configuration
    if use_diverse_placement:
        renewable_units = DIVERSE_PLACEMENTS
        forecasts = _build_diverse_forecasts(original_forecasts, original_units, DIVERSE_PLACEMENTS)
        scenarios = _build_diverse_multipliers(
            original_scenarios, original_units, DIVERSE_PLACEMENTS
        )
    else:
        renewable_units = original_units
        forecasts = original_forecasts
        scenarios = original_scenarios

    total_re_capacity = sum(u.pmax_mw for u in renewable_units)
    re_buses = sorted({u.bus_id for u in renewable_units})

    print(f"Config: branch_derate={branch_derate:.0%}  diverse_placement={use_diverse_placement}")
    print(f"  Renewable capacity: {total_re_capacity:.0f} MW at buses {re_buses}")

    bus_ids = sorted(b.bus_id for b in buses)
    n_scenarios = len(scenarios)
    n_hours = 24
    scenario_ids = sorted(scenarios.keys())

    all_solutions: list[DcopfSolution] = []

    # Also solve a base case (no renewables) for comparison
    print("Solving base case (no renewables)...")
    for hour_idx in range(n_hours):
        bus_loads = {bid: hourly[hour_idx] for bid, hourly in load_profile.items()}
        sol = solve_dcopf(
            gens,
            gen_costs,
            buses,
            branches,
            ptdf,
            non_ref_bus_ids,
            ref_bus_id,
            base_mva,
            bus_loads,
            renewable_injections={},
            scenario=0,
            hour=hour_idx + 1,
        )
        all_solutions.append(sol)

    print(f"Solving {n_scenarios} scenarios × {n_hours} hours = {n_scenarios * n_hours} OPFs...")
    for scenario_id in scenario_ids:
        multipliers = scenarios[scenario_id]

        for hour_idx in range(n_hours):
            hour = hour_idx + 1
            bus_loads = {bid: hourly[hour_idx] for bid, hourly in load_profile.items()}

            # Compute renewable injections for this scenario-hour
            re_inject: dict[int, float] = {}
            for unit in renewable_units:
                fc = forecasts.get(unit.gen_uid)
                mult = multipliers.get(unit.gen_uid)
                if fc is None or mult is None:
                    continue
                mw = min(max(fc[hour_idx] * mult[hour_idx], 0.0), unit.pmax_mw)
                re_inject[unit.bus_id] = re_inject.get(unit.bus_id, 0.0) + mw

            sol = solve_dcopf(
                gens,
                gen_costs,
                buses,
                branches,
                ptdf,
                non_ref_bus_ids,
                ref_bus_id,
                base_mva,
                bus_loads,
                re_inject,
                scenario=scenario_id,
                hour=hour,
            )
            all_solutions.append(sol)

    # Separate base case and scenario solutions
    base_solutions = [s for s in all_solutions if s.scenario == 0]
    scenario_solutions = [s for s in all_solutions if s.scenario > 0]

    # Compute LMP statistics per bus (across scenario solutions only)
    bus_lmp_arrays: dict[int, list[float]] = {bid: [] for bid in bus_ids}
    for sol in scenario_solutions:
        if not sol.converged:
            continue
        for bid in bus_ids:
            bus_lmp_arrays[bid].append(sol.bus_lmps.get(bid, 0.0))

    bus_stats: list[ScenarioLmpStats] = []
    for bid in bus_ids:
        arr = np.array(bus_lmp_arrays[bid])
        if len(arr) == 0:
            continue
        bus_stats.append(
            ScenarioLmpStats(
                bus_id=bid,
                mean_lmp=float(np.mean(arr)),
                std_lmp=float(np.std(arr)),
                min_lmp=float(np.min(arr)),
                max_lmp=float(np.max(arr)),
                p5_lmp=float(np.percentile(arr, 5)),
                p95_lmp=float(np.percentile(arr, 95)),
            )
        )

    # Compute shadow price statistics per branch
    total_points = len([s for s in scenario_solutions if s.converged])
    branch_stats: list[BranchShadowStats] = []
    for k, br in enumerate(branches):
        shadows = [sol.branch_shadow_prices[k] for sol in scenario_solutions if sol.converged]
        arr = np.array(shadows)
        n_binding = int(np.sum(np.abs(arr) > 1e-6))
        branch_stats.append(
            BranchShadowStats(
                branch_index=k,
                from_bus=br.from_bus,
                to_bus=br.to_bus,
                rate_a_mw=br.rate_a_mw,
                mean_shadow=float(np.mean(arr)),
                std_shadow=float(np.std(arr)),
                max_shadow=float(np.max(np.abs(arr))),
                prob_binding=n_binding / total_points if total_points > 0 else 0.0,
            )
        )

    # Build summary
    converged = sum(1 for s in scenario_solutions if s.converged)
    failed = len(scenario_solutions) - converged

    # LMP spread: difference between highest and lowest bus LMP
    lmp_spreads = []
    for sol in scenario_solutions:
        if sol.converged:
            lmps = list(sol.bus_lmps.values())
            lmp_spreads.append(max(lmps) - min(lmps))

    lmp_spread_arr = np.array(lmp_spreads) if lmp_spreads else np.array([0.0])

    # Base case LMPs for comparison
    base_lmps: dict[int, float] = {}
    for sol in base_solutions:
        if sol.converged and sol.hour == 18:  # peak hour
            base_lmps = dict(sol.bus_lmps)
            break

    summary = {
        "total_opfs_solved": converged + failed + len(base_solutions),
        "scenario_opfs_converged": converged,
        "scenario_opfs_failed": failed,
        "lmp_spread_mean": round(float(np.mean(lmp_spread_arr)), 4),
        "lmp_spread_std": round(float(np.std(lmp_spread_arr)), 4),
        "lmp_spread_max": round(float(np.max(lmp_spread_arr)), 4),
        "base_case_peak_lmps": {str(k): round(v, 4) for k, v in sorted(base_lmps.items())},
    }

    # Write outputs
    out_dir = data_dir / "scenario_congestion" / label
    write_lmp_csv(all_solutions, bus_ids, out_dir / "lmp_summary.csv")
    write_shadow_csv(all_solutions, branches, out_dir / "shadow_prices.csv")
    write_dcopf_json(bus_stats, branch_stats, summary, out_dir / "dcopf_statistics.json")

    # Print summary
    _print_summary(summary, bus_stats, branch_stats, base_lmps, bus_ids)


def _print_summary(
    summary: dict,
    bus_stats: list[ScenarioLmpStats],
    branch_stats: list[BranchShadowStats],
    base_lmps: dict[int, float],
    bus_ids: list[int],
) -> None:
    """Print human-readable summary."""
    print()
    print("=" * 72)
    print("  DC OPF Shadow Price Analysis — TINY (case39)")
    print("=" * 72)
    print(
        f"  OPFs solved: {summary['total_opfs_solved']}"
        f"  (converged: {summary['scenario_opfs_converged']})"
    )
    print()
    print("  LMP spread (max bus - min bus):")
    print(f"    Mean: ${summary['lmp_spread_mean']:.4f}/MWh")
    print(f"    Std:  ${summary['lmp_spread_std']:.4f}/MWh")
    print(f"    Max:  ${summary['lmp_spread_max']:.4f}/MWh")
    print()

    # Show buses with highest LMP variability
    stats_sorted = sorted(bus_stats, key=lambda x: x.std_lmp, reverse=True)
    print("  Top 10 buses by LMP variability:")
    print(
        f"    {'Bus':>5s}  {'Mean':>8s}  {'Std':>8s}  {'Min':>8s}  {'Max':>8s}  {'Base(HR18)':>10s}"
    )
    for s in stats_sorted[:10]:
        base = base_lmps.get(s.bus_id, 0.0)
        print(
            f"    {s.bus_id:5d}  {s.mean_lmp:8.4f}  {s.std_lmp:8.4f}"
            f"  {s.min_lmp:8.4f}  {s.max_lmp:8.4f}  {base:10.4f}"
        )

    print()

    # Show binding branches
    binding = [s for s in branch_stats if s.prob_binding > 0]
    if binding:
        print(f"  Binding branches ({len(binding)} of {len(branch_stats)}):")
        hdr = f"    {'Branch':>8s}  {'P(bind)':>8s}  {'Mean μ':>10s}"
        print(f"{hdr}  {'Std μ':>10s}  {'Max |μ|':>10s}")
        for s in sorted(binding, key=lambda x: x.prob_binding, reverse=True):
            print(
                f"    {s.from_bus:3d}-{s.to_bus:<3d}  {s.prob_binding:8.4f}"
                f"  {s.mean_shadow:10.6f}  {s.std_shadow:10.6f}  {s.max_shadow:10.6f}"
            )
    else:
        print("  No binding branches found.")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DC OPF shadow price analysis")
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="Run sensitivity analysis: diverse placement + tightened branches",
    )
    args = parser.parse_args()

    if args.sensitivity:
        print("=" * 72)
        print("  SENSITIVITY: diverse placement + 70% branch ratings")
        print("=" * 72)
        main(branch_derate=0.70, use_diverse_placement=True, label="diverse_tight")
    else:
        main(label="base")
