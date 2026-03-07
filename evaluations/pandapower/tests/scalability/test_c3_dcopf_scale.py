"""
Test C-3: DC OPF at scale with multiple solvers

Dimension: scalability
Network: MEDIUM (ACTIVSg10k, ~10000 buses)
Pass condition: Converges with each solver. Objective values consistent across solvers.
Tool: pandapower v3.4.0

NOTE: Eval-config specifies "HiGHS, GLPK" but pandapower can only use PYPOWER
interior point solver for rundcopp(). No solver swap is possible without the
PowerModels.jl bridge. This limitation is documented.
"""

import json
import os
import time
import traceback

import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc


def run(network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m") -> dict:
    """Execute DC OPF at scale and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        load_start = time.perf_counter()
        net = from_mpc(network_file, f_hz=60)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["load_count"] = len(net.load)
        results["details"]["line_count"] = len(net.line)

        # Check cost curves
        has_costs = len(net.poly_cost) > 0 or len(net.pwl_cost) > 0
        if not has_costs:
            results["details"]["cost_setup"] = "No cost curves from import; adding linear costs"
            for idx in net.gen.index:
                pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=20.0 + idx * 0.1)
            for idx in net.ext_grid.index:
                pp.create_poly_cost(net, idx, "ext_grid", cp1_eur_per_mw=50.0)
        else:
            results["details"]["cost_setup"] = "Cost curves imported from MATPOWER case"
            results["details"]["poly_cost_count"] = len(net.poly_cost)
            results["details"]["pwl_cost_count"] = len(net.pwl_cost)

        # Document solver limitation
        results["details"]["solver_limitation"] = (
            "pandapower rundcopp() uses PYPOWER interior point solver only. "
            "Cannot use HiGHS or GLPK as specified in eval-config. "
            "Solver swap requires PowerModels.jl bridge."
        )
        results["workarounds"].append(
            "Solver deviation: eval-config specifies HiGHS, GLPK but pandapower "
            "native DC OPF uses PYPOWER interior point only. Single solver tested."
        )

        # Memory before solve
        try:
            import resource

            mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # noqa: F841
        except Exception:
            mem_before = None  # noqa: F841

        # 2. Solve DC OPF with PYPOWER interior point
        solve_start = time.perf_counter()
        pp.rundcopp(net)
        solve_elapsed = time.perf_counter() - solve_start
        results["details"]["solve_seconds"] = solve_elapsed

        # Memory after solve
        try:
            mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            results["details"]["peak_memory_mb"] = mem_after
        except Exception:
            pass

        # CPU utilization
        try:
            cpu_times = os.times()
            results["details"]["cpu_user_seconds"] = cpu_times.user
            results["details"]["cpu_system_seconds"] = cpu_times.system
        except Exception:
            pass

        # 3. Check convergence
        if not net.get("OPF_converged", False):
            results["errors"].append("DC OPF did not converge on MEDIUM network")
            # Still collect what we can
            results["details"]["converged"] = False
            return results

        results["details"]["converged"] = True

        # 4. Extract results
        results["details"]["solver_results"] = {
            "pypower_ip": {
                "wall_clock_seconds": solve_elapsed,
                "converged": True,
                "objective": float(net.res_cost) if hasattr(net, "res_cost") else None,
            }
        }

        # Generation dispatch summary
        total_gen = float(net.res_gen["p_mw"].sum())
        total_ext = float(net.res_ext_grid["p_mw"].sum())
        results["details"]["total_generation_mw"] = total_gen + total_ext

        # LMPs
        if "lam_p" in net.res_bus.columns:
            lmps = net.res_bus["lam_p"]
            results["details"]["lmp_max"] = float(lmps.max())
            results["details"]["lmp_min"] = float(lmps.min())
            results["details"]["lmp_mean"] = float(lmps.mean())
            results["details"]["lmps_extractable"] = True
        else:
            results["details"]["lmps_extractable"] = False

        # 5. Assess pass condition
        # Cannot test multiple solvers - PYPOWER IP is the only option
        results["status"] = "qualified_pass"
        results["details"]["qualification"] = (
            "DC OPF converges on MEDIUM network but only with PYPOWER interior point. "
            "Cannot test solver consistency across HiGHS/GLPK as required."
        )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
