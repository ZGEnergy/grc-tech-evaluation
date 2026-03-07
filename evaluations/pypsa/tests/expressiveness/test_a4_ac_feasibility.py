"""
Test A-4: AC Feasibility Check — take DC OPF dispatch, run full ACPF

Dimension: expressiveness
Network: TINY (case39)
Pass condition: Achievable within the same model context (no export to file
    and reimport). Voltage violations and thermal limit violations identifiable
    from results.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import numpy as np

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

# Convergence protocol thresholds
V_MAG_MIN = 0.95  # pu
V_MAG_MAX = 1.05  # pu


def _load_network_with_costs(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network and manually set marginal costs.

    Reuses the pattern from test_a3_dcopf.py.
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

    # Parse gencost and set marginal_cost
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

    if costs_set > 0:
        workarounds.append(
            f"Manually set marginal_cost on {costs_set}/{num_gens} generators "
            "from gencost data (PPC importer does not import gencost)"
        )

    return net, workarounds


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute AC feasibility check on DC OPF dispatch.

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

        # 2. Solve DC OPF to get dispatch
        opt_status = n.optimize(solver_name=SOLVER_NAME, solver_options=SOLVER_OPTIONS)
        solver_status = str(opt_status)
        converged_dcopf = "ok" in solver_status.lower() or "optimal" in solver_status.lower()

        if not converged_dcopf:
            results["errors"].append(f"DC OPF did not converge: {solver_status}")
            return results

        # Record DC OPF dispatch
        dcopf_dispatch = n.generators_t.p.iloc[0].copy()
        dcopf_objective = float(n.objective)
        results["details"]["dcopf_objective"] = dcopf_objective
        results["details"]["dcopf_dispatch"] = {
            gen: float(dcopf_dispatch[gen]) for gen in dcopf_dispatch.index
        }

        # 3. Set generator p_set from DC OPF dispatch for AC PF
        # This is done in the same model context (no export/reimport)
        for gen in n.generators.index:
            n.generators.loc[gen, "p_set"] = float(dcopf_dispatch[gen])

        results["workarounds"].append(
            "Set generator p_set from DC OPF dispatch results to run AC PF "
            "in the same model context"
        )

        # 4. Run AC Power Flow (flat start per convergence-protocol.md)
        start = time.perf_counter()
        pf_result = n.pf()
        elapsed_flat = time.perf_counter() - start

        # Check convergence
        # n.pf() returns a dict with 'converged' key per sub-network
        pf_converged = False
        convergence_info = {}
        if hasattr(pf_result, "keys"):
            # pf_result is a dict-like with sub_network convergence info
            for key in pf_result:
                convergence_info[str(key)] = str(pf_result[key])
        # Check sub_networks convergence
        if hasattr(n, "sub_networks") and len(n.sub_networks) > 0:
            converged_flags = (
                n.sub_networks["pf_converged"] if "pf_converged" in n.sub_networks.columns else None
            )
            if converged_flags is not None:
                pf_converged = bool(converged_flags.all())
            else:
                # Fallback: check if results were populated
                pf_converged = len(n.buses_t.v_mag_pu) > 0

        # If flat start fails, try DC warm start
        dc_warm_start_used = False
        if not pf_converged:
            results["details"]["flat_start_converged"] = False
            results["details"]["flat_start_time_s"] = elapsed_flat

            # DC warm start: solve DCPF first, use angles as initialization
            n.lpf()
            # Set voltage angles from DCPF solution
            if len(n.buses_t.v_ang) > 0:
                for bus in n.buses.index:
                    n.buses.loc[bus, "v_ang"] = float(n.buses_t.v_ang.iloc[0][bus])

            start = time.perf_counter()
            pf_result = n.pf()
            elapsed_warm = time.perf_counter() - start
            dc_warm_start_used = True

            if hasattr(n, "sub_networks") and len(n.sub_networks) > 0:
                converged_flags = n.sub_networks.get("pf_converged")
                if converged_flags is not None:
                    pf_converged = bool(converged_flags.all())
                else:
                    pf_converged = len(n.buses_t.v_mag_pu) > 0

            results["details"]["dc_warm_start_used"] = True
            results["details"]["dc_warm_start_time_s"] = elapsed_warm
        else:
            results["details"]["flat_start_converged"] = True

        results["wall_clock_seconds"] = (
            elapsed_flat if not dc_warm_start_used else elapsed_flat + elapsed_warm
        )

        results["details"]["acpf_converged"] = pf_converged

        if not pf_converged:
            results["errors"].append("AC PF did not converge (flat start and DC warm start)")
            return results

        # 5. Extract results and check violations
        v_mag = n.buses_t.v_mag_pu.iloc[0]
        v_ang = n.buses_t.v_ang.iloc[0]

        # Voltage violations
        v_violations_low = v_mag[v_mag < V_MAG_MIN]
        v_violations_high = v_mag[v_mag > V_MAG_MAX]
        voltage_violations = {}
        if len(v_violations_low) > 0:
            voltage_violations["below_0.95"] = {
                bus: float(v_mag[bus]) for bus in v_violations_low.index
            }
        if len(v_violations_high) > 0:
            voltage_violations["above_1.05"] = {
                bus: float(v_mag[bus]) for bus in v_violations_high.index
            }

        results["details"]["voltage_magnitudes"] = {
            "min_pu": float(v_mag.min()),
            "max_pu": float(v_mag.max()),
            "mean_pu": float(v_mag.mean()),
            "num_violations": len(v_violations_low) + len(v_violations_high),
            "violations": voltage_violations,
        }

        # Thermal limit violations
        line_flows_p0 = n.lines_t.p0.iloc[0]
        line_flows_p1 = n.lines_t.p1.iloc[0]
        # Compute apparent power (use max of |p0|, |p1| as proxy for loading)
        # For a proper check, compute S = sqrt(P^2 + Q^2)
        line_q0 = n.lines_t.q0.iloc[0] if len(n.lines_t.q0) > 0 else line_flows_p0 * 0
        line_q1 = n.lines_t.q1.iloc[0] if len(n.lines_t.q1) > 0 else line_flows_p1 * 0

        s0 = np.sqrt(line_flows_p0**2 + line_q0**2)
        s1 = np.sqrt(line_flows_p1**2 + line_q1**2)
        s_max = np.maximum(s0, s1)

        s_rating = n.lines["s_nom"]  # MVA rating
        loading_pct = (s_max / s_rating * 100).replace([np.inf, -np.inf], np.nan).dropna()

        thermal_violations = loading_pct[loading_pct > 100.0]
        results["details"]["thermal_loading"] = {
            "max_loading_pct": float(loading_pct.max()) if len(loading_pct) > 0 else None,
            "mean_loading_pct": float(loading_pct.mean()) if len(loading_pct) > 0 else None,
            "num_violations": int(len(thermal_violations)),
            "violations": {line: float(loading_pct[line]) for line in thermal_violations.index}
            if len(thermal_violations) > 0
            else {},
        }

        # Reactive power summary
        gen_q = n.generators_t.q.iloc[0] if len(n.generators_t.q) > 0 else None
        if gen_q is not None:
            results["details"]["reactive_power"] = {
                "total_gen_q_mvar": float(gen_q.sum()),
                "min_q_mvar": float(gen_q.min()),
                "max_q_mvar": float(gen_q.max()),
            }

        # Voltage angle summary
        results["details"]["voltage_angles"] = {
            "min_deg": float(np.degrees(v_ang.min())),
            "max_deg": float(np.degrees(v_ang.max())),
            "spread_deg": float(np.degrees(v_ang.max() - v_ang.min())),
        }

        # 6. Pass condition: achievable in same model context, violations identifiable
        # The test passes if we could run ACPF on DCOPF dispatch and identify violations
        results["status"] = "pass"
        results["details"]["same_model_context"] = True
        results["details"]["violations_identifiable"] = True

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
