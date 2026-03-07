"""
Test A-3: Solve DC OPF with generation costs and line flow limits

Dimension: expressiveness
Network: TINY (case39)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable
    from solution.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case39.m")

# HiGHS solver settings per solver-config.md
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 300,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}


def _load_network_with_costs(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network and manually set marginal costs.

    The PPC importer does NOT import gencost, so we parse it from the .m file
    and set marginal_cost on generators manually.
    """
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)

    # Parse gencost from CaseFrames and set marginal_cost on generators
    # MATPOWER gencost format (polynomial type 2):
    #   type, startup, shutdown, n, c(n-1), ..., c0
    # For type 2, n=3: columns are [type, startup, shutdown, n, c2, c1, c0]
    #   cost = c2*P^2 + c1*P + c0
    #   marginal_cost ~ c1 (linear coefficient, used for DC OPF LP)
    gencost = cf.gencost.values
    workarounds = []

    num_gens = len(net.generators)
    costs_set = 0
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])

            if cost_type == 2:  # Polynomial
                # Coefficients are in columns 4 onward: c(n-1), ..., c1, c0
                coeffs = cost_row[4 : 4 + n_coeffs]
                if n_coeffs >= 2:
                    # c1 is the second-to-last coefficient (linear term)
                    c1 = float(coeffs[-2])
                    net.generators.loc[gen_idx, "marginal_cost"] = c1
                    costs_set += 1
                elif n_coeffs == 1:
                    # Only constant term
                    net.generators.loc[gen_idx, "marginal_cost"] = 0.0
                    costs_set += 1
            elif cost_type == 1:  # Piecewise linear
                # Use average cost from piecewise data
                # Pairs are (P, cost) starting at column 4
                n_pairs = int(cost_row[3])
                pairs = cost_row[4 : 4 + 2 * n_pairs].reshape(-1, 2)
                if len(pairs) >= 2:
                    # Linear approximation: (cost_last - cost_first) / (p_last - p_first)
                    dp = pairs[-1, 0] - pairs[0, 0]
                    dc = pairs[-1, 1] - pairs[0, 1]
                    mc = dc / dp if dp > 0 else 0.0
                    net.generators.loc[gen_idx, "marginal_cost"] = mc
                    costs_set += 1

    if costs_set > 0:
        workarounds.append(
            f"Manually set marginal_cost on {costs_set}/{num_gens} generators "
            "from gencost data (PPC importer does not import gencost)"
        )

    return net, workarounds


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute DC OPF and return structured results.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    try:
        # 1. Load network with costs (not timed)
        n, load_workarounds = _load_network_with_costs(network_file)
        results["workarounds"].extend(load_workarounds)

        # Record marginal costs for verification
        gen_costs = {
            gen: float(n.generators.loc[gen, "marginal_cost"]) for gen in n.generators.index
        }

        # 2. Solve DC OPF (timed)
        start = time.perf_counter()
        status = n.optimize(solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS)
        elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = elapsed

        # 3. Check convergence
        # n.optimize() returns (status, condition) tuple or just status string
        solver_status = str(status)
        converged = False
        if isinstance(status, tuple):
            solver_status = str(status[0])
            converged = "ok" in solver_status.lower() or "optimal" in solver_status.lower()
        elif isinstance(status, str):
            converged = "ok" in status.lower() or "optimal" in status.lower()
        else:
            converged = "ok" in str(status).lower() or "optimal" in str(status).lower()

        # 4. Extract structured outputs
        # Optimal dispatch
        gen_dispatch = n.generators_t.p
        dispatch_stats = {}
        if gen_dispatch is not None and len(gen_dispatch) > 0:
            dispatch = gen_dispatch.iloc[0]
            dispatch_stats = {
                "total_dispatch_MW": float(dispatch.sum()),
                "min_MW": float(dispatch.min()),
                "max_MW": float(dispatch.max()),
                "num_generators": int(len(dispatch)),
                "per_generator": {gen: float(dispatch[gen]) for gen in dispatch.index},
            }

        # LMPs (shadow prices on bus power balance)
        lmp_stats = {}
        bus_mp = n.buses_t.marginal_price
        if bus_mp is not None and len(bus_mp) > 0:
            lmps = bus_mp.iloc[0]
            lmp_stats = {
                "min_$/MWh": float(lmps.min()),
                "max_$/MWh": float(lmps.max()),
                "mean_$/MWh": float(lmps.mean()),
                "num_buses_with_lmp": int((~lmps.isna()).sum()),
                "sample_lmps": {bus: float(lmps[bus]) for bus in list(lmps.index[:5])},
            }

        # Line flows
        line_flow_stats = {}
        line_p0 = n.lines_t.p0
        if line_p0 is not None and len(line_p0) > 0:
            flows = line_p0.iloc[0]
            line_flow_stats = {
                "min_MW": float(flows.min()),
                "max_MW": float(flows.max()),
                "num_lines": int(len(flows)),
            }

        # Line shadow prices (congestion)
        # Note: PyPSA's n.optimize() assigns Bus marginal prices (LMPs) but does NOT
        # assign line flow constraint duals (mu_upper/mu_lower) to the network by default.
        # The solver log warns: "shadow-prices of ... Line-fix-s-lower, Line-fix-s-upper
        # ... were not assigned to the network."
        # Line congestion duals would need to be extracted from n.model directly.
        line_mu_stats = {}
        mu_upper_df = n.lines_t.mu_upper
        mu_lower_df = n.lines_t.mu_lower
        if mu_upper_df is not None and len(mu_upper_df.columns) > 0:
            mu_upper = mu_upper_df.iloc[0]
            mu_lower = mu_lower_df.iloc[0]
            congested_upper = (mu_upper.abs() > 1e-6).sum()
            congested_lower = (mu_lower.abs() > 1e-6).sum()
            line_mu_stats = {
                "congested_lines_upper": int(congested_upper),
                "congested_lines_lower": int(congested_lower),
                "mu_upper_max": float(mu_upper.max()),
                "mu_lower_max": float(mu_lower.max()),
            }
        else:
            line_mu_stats = {
                "note": "Line shadow prices not assigned to network by n.optimize(). "
                "Bus LMPs are available via n.buses_t.marginal_price.",
            }

        # Objective value
        objective = float(n.objective) if hasattr(n, "objective") else None

        output_format = "pandas DataFrame"

        # 5. Pass condition check
        has_dispatch = len(dispatch_stats) > 0 and dispatch_stats["num_generators"] > 0
        has_lmps = len(lmp_stats) > 0 and lmp_stats["num_buses_with_lmp"] > 0

        pass_condition_met = converged and has_dispatch and has_lmps

        if pass_condition_met:
            results["status"] = "pass"

        results["details"] = {
            "converged": converged,
            "solver_status": solver_status,
            "solver": SOLVER_NAME,
            "solver_options": SOLVER_OPTIONS,
            "objective": objective,
            "output_format": output_format,
            "generator_costs_set": gen_costs,
            "dispatch": dispatch_stats,
            "lmps": lmp_stats,
            "line_flows": line_flow_stats,
            "line_shadow_prices": line_mu_stats,
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
