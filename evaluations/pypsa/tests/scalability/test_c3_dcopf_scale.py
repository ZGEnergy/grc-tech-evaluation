"""
Test C-3: DC OPF Scale Test

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k)
Pass condition: Converges. Wall-clock, objective, and peak memory recorded.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import json
import math
import time
import traceback
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600.0,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
}

TIMEOUT_SECONDS = 600


def _load_network_with_costs(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network and manually set marginal costs."""
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

    gencost = cf.gencost.values
    workarounds = []
    num_gens = len(net.generators)
    costs_set = 0
    for i, gen_idx in enumerate(net.generators.index):
        if i < len(gencost):
            cost_row = gencost[i]
            cost_type = int(cost_row[0])
            n_coeffs = int(cost_row[3])
            if cost_type == 2:
                coeffs = cost_row[4 : 4 + n_coeffs]
                if n_coeffs >= 2:
                    c1 = float(coeffs[-2])
                    net.generators.loc[gen_idx, "marginal_cost"] = c1
                    costs_set += 1
                elif n_coeffs == 1:
                    net.generators.loc[gen_idx, "marginal_cost"] = 0.0
                    costs_set += 1
            elif cost_type == 1:
                n_pairs = int(cost_row[3])
                pairs = cost_row[4 : 4 + 2 * n_pairs].reshape(-1, 2)
                if len(pairs) >= 2:
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

    # Fix zero s_nom branches (causes infeasibility in OPF)
    zero_s_nom_lines = net.lines["s_nom"] == 0
    if zero_s_nom_lines.any():
        net.lines.loc[zero_s_nom_lines, "s_nom"] = 9999.0
        workarounds.append(
            f"Set s_nom=9999 on {zero_s_nom_lines.sum()} lines with zero thermal rating"
        )

    zero_s_nom_xfmr = net.transformers["s_nom"] == 0
    if zero_s_nom_xfmr.any():
        net.transformers.loc[zero_s_nom_xfmr, "s_nom"] = 9999.0
        workarounds.append(
            f"Set s_nom=9999 on {zero_s_nom_xfmr.sum()} transformers with zero rating"
        )

    # Fix zero impedance branches (causes singular matrix in LPF)
    zero_x_lines = net.lines["x"] == 0
    if zero_x_lines.any():
        net.lines.loc[zero_x_lines, "x"] = 0.0001
        workarounds.append(f"Set x=0.0001 on {zero_x_lines.sum()} lines with zero reactance")

    zero_x_xfmr = net.transformers["x"] == 0
    if zero_x_xfmr.any():
        net.transformers.loc[zero_x_xfmr, "x"] = 0.0001
        workarounds.append(f"Set x=0.0001 on {zero_x_xfmr.sum()} transformers with zero reactance")

    return net, workarounds


def _get_peak_memory_mb():
    """Get peak memory usage in MB using resource module."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024.0
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute DCOPF on 10k-bus network and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pypsa

        mem_before = _get_peak_memory_mb()

        # 1. Load network with costs
        n, load_workarounds = _load_network_with_costs(network_file)
        results["workarounds"].extend(load_workarounds)

        network_stats = {
            "n_buses": len(n.buses),
            "n_generators": len(n.generators),
            "n_lines": len(n.lines),
            "n_transformers": len(n.transformers),
            "n_loads": len(n.loads),
        }

        # 2. Solve DCOPF
        solve_start = time.perf_counter()
        status = n.optimize(solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS)
        solve_elapsed = time.perf_counter() - solve_start

        mem_after = _get_peak_memory_mb()

        # 3. Check convergence
        solver_status = str(status)
        converged = False
        if isinstance(status, tuple):
            solver_status = str(status[0])
            converged = "ok" in solver_status.lower() or "optimal" in solver_status.lower()
        elif isinstance(status, str):
            converged = "ok" in status.lower() or "optimal" in status.lower()
        else:
            converged = "ok" in str(status).lower() or "optimal" in str(status).lower()

        # 4. Extract results
        objective_raw = getattr(n, "objective", None)
        objective = float(objective_raw) if objective_raw is not None else None

        dispatch_stats = {}
        gen_dispatch = n.generators_t.p
        if gen_dispatch is not None and len(gen_dispatch) > 0:
            dispatch = gen_dispatch.iloc[0]
            dispatch_stats = {
                "total_dispatch_MW": float(dispatch.sum()),
                "min_MW": float(dispatch.min()),
                "max_MW": float(dispatch.max()),
                "num_generators": int(len(dispatch)),
            }

        lmp_stats = {}
        bus_mp = n.buses_t.marginal_price
        if bus_mp is not None and len(bus_mp) > 0:
            lmps = bus_mp.iloc[0]
            lmp_stats = {
                "min_$/MWh": float(lmps.min()),
                "max_$/MWh": float(lmps.max()),
                "mean_$/MWh": float(lmps.mean()),
                "num_buses_with_lmp": int((~lmps.isna()).sum()),
            }

        total_elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = total_elapsed

        results["details"] = {
            "converged": converged,
            "solver_status": solver_status,
            "solver": SOLVER_NAME,
            "solver_options": SOLVER_OPTIONS,
            "objective": objective,
            "solve_time_seconds": solve_elapsed,
            "network": network_stats,
            "dispatch": dispatch_stats,
            "lmps": lmp_stats,
            "peak_memory_mb": mem_after,
            "mem_before_mb": mem_before,
            "pypsa_version": pypsa.__version__,
        }

        if converged and objective is not None and np.isfinite(objective):
            results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":

    def _json_safe(obj):
        if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
            return str(obj)
        return str(obj)

    result = run()
    print(json.dumps(result, indent=2, default=_json_safe))
