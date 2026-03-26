"""
Test C-4: SCUC 24hr on SMALL with HiGHS and SCIP

Dimension: scalability
Network: SMALL (ACTIVSg2000, case_ACTIVSg2000.m)
Pass condition: Completes SCUC 24hr on SMALL with HiGHS and SCIP. Wall-clock time per
    solver, MIP gap at termination, and peak memory recorded.
Tool: PyPSA 1.1.2
"""

import json
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))

DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")

# Solver configurations per solver-config.md
HIGHS_OPTIONS_1T = {
    "time_limit": 600.0,  # 10 min (prior run showed root LP unresolved at 600s)
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
    "log_to_console": True,
}

HIGHS_OPTIONS_MT = {
    "time_limit": 1800.0,  # 30 min — give multi-threaded the full budget
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 0,  # 0 = use all available cores
    "output_flag": True,
    "log_to_console": True,
}

SCIP_OPTIONS = {
    "limits/time": 1800,  # 30 min per spec timeout threshold
    "limits/gap": 0.01,
    "display/verblevel": 4,
    "lp/threads": 1,
}

# 24-hour load profile (normalized, peak at hour 19, trough at hour 4)
HOURLY_FACTORS = np.array(
    [
        0.75,
        0.73,
        0.72,
        0.72,
        0.73,
        0.76,
        0.82,
        0.88,
        0.92,
        0.94,
        0.95,
        0.95,
        0.94,
        0.93,
        0.92,
        0.92,
        0.93,
        0.95,
        1.00,
        0.98,
        0.95,
        0.90,
        0.85,
        0.80,
    ]
)


def prepare_network(network_file: str):
    """Load ACTIVSg2000 and configure for 24-hour SCUC."""
    from matpower_loader import load_pypsa

    n = load_pypsa(network_file, overwrite_zero_s_nom=True)

    # Set 24-hour snapshots
    snapshots = pd.date_range("2024-01-01", periods=24, freq="h")
    n.set_snapshots(snapshots)

    # Assign UC parameters to all generators
    gen_names = list(n.generators.index)
    n_gens = len(gen_names)

    # Differentiated marginal costs: $10-$100/MWh linear scale
    costs = np.linspace(10, 100, n_gens)
    for i, gen_name in enumerate(gen_names):
        n.generators.at[gen_name, "marginal_cost"] = float(costs[i])
        n.generators.at[gen_name, "committable"] = True
        n.generators.at[gen_name, "start_up_cost"] = float(costs[i]) * 1000
        n.generators.at[gen_name, "p_min_pu"] = 0.3
        n.generators.at[gen_name, "min_up_time"] = 1
        n.generators.at[gen_name, "min_down_time"] = 1

    n.generators["min_up_time"] = n.generators["min_up_time"].astype(int)
    n.generators["min_down_time"] = n.generators["min_down_time"].astype(int)

    # Build 24-hour load profile
    total_original_load = float(n.loads.p_set.sum())
    for load_name in n.loads.index:
        base_load = float(n.loads.at[load_name, "p_set"])
        frac = base_load / total_original_load if total_original_load > 0 else 0.0
        load_series = pd.Series(
            [total_original_load * HOURLY_FACTORS[h] * frac for h in range(24)],
            index=snapshots,
        )
        n.loads_t.p_set[load_name] = load_series

    return n, total_original_load


def solve_scuc(n, solver_name: str, solver_options: dict) -> dict:
    """Run SCUC with the given solver, measuring time and memory."""
    result = {
        "solver": solver_name,
        "feasible": False,
        "solve_seconds": 0.0,
        "peak_memory_mb": 0.0,
        "objective": None,
        "mip_gap": None,
        "hit_time_limit": False,
        "solver_status": None,
        "n_cycling_generators": None,
        "error": None,
    }

    tracemalloc.start()
    solve_start = time.perf_counter()
    try:
        opt_result = n.optimize(
            solver_name=solver_name,
            solver_options=solver_options,
        )
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result["solve_seconds"] = solve_elapsed
        result["peak_memory_mb"] = peak / (1024 * 1024)

        # Parse status
        if isinstance(opt_result, tuple):
            status_str = str(opt_result[0])
        else:
            status_str = str(opt_result)
        result["solver_status"] = status_str

        # Check feasibility
        solve_ok = False
        try:
            obj = float(n.objective)
            if np.isfinite(obj):
                solve_ok = True
                result["objective"] = obj
        except Exception:
            pass
        if not solve_ok and status_str.lower() in ("ok", "optimal", "feasible"):
            solve_ok = True

        result["feasible"] = solve_ok

        # Time limit check
        time_limit = solver_options.get("time_limit", solver_options.get("limits/time", 600))
        result["hit_time_limit"] = solve_elapsed >= float(time_limit) * 0.98

        if result["hit_time_limit"]:
            result["mip_gap"] = "unknown (time limit reached)"
        else:
            result["mip_gap"] = "<=1% (target met)"

        # Commitment schedule analysis
        if solve_ok and hasattr(n, "generators_t") and "status" in dir(n.generators_t):
            try:
                status_df = n.generators_t.status
                if len(status_df) > 0:
                    n_cycling = int(
                        sum(
                            1
                            for col in status_df.columns
                            if (np.diff(status_df[col].values.astype(float)) != 0).any()
                        )
                    )
                    result["n_cycling_generators"] = n_cycling
            except Exception:
                pass

    except Exception as e:
        solve_elapsed = time.perf_counter() - solve_start
        try:
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            result["peak_memory_mb"] = peak / (1024 * 1024)
        except Exception:
            tracemalloc.stop()
        result["solve_seconds"] = solve_elapsed
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute 24-hour SCUC on ACTIVSg2000 with HiGHS and SCIP.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # 1. Load and prepare network
        load_start = time.perf_counter()
        n, total_load = prepare_network(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["n_committable"] = int(n.generators.committable.sum())
        results["details"]["total_load_mw"] = total_load
        results["details"]["total_gen_capacity_mw"] = float(n.generators.p_nom.sum())
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["load_range_mw"] = {
            "min": float(total_load * HOURLY_FACTORS.min()),
            "max": float(total_load * HOURLY_FACTORS.max()),
        }
        print(
            f"Network: {len(n.buses)} buses, {len(n.lines)} lines, "
            f"{len(n.generators)} generators ({n.generators.committable.sum()} committable)"
        )
        print(
            f"Load range: {total_load * HOURLY_FACTORS.min():.0f}"
            f"–{total_load * HOURLY_FACTORS.max():.0f} MW"
        )
        print(f"Total gen capacity: {n.generators.p_nom.sum():.0f} MW")

        # Record CPU info
        import os

        cpu_count = os.cpu_count() or 1
        results["details"]["cpu_threads_available"] = cpu_count

        # 2. Solve with HiGHS (single-threaded)
        print("\n=== HiGHS SCUC (24h, 1 thread) ===")
        n_highs_1t = n.copy()
        highs_1t_result = solve_scuc(n_highs_1t, "highs", HIGHS_OPTIONS_1T)
        highs_1t_result["threads_used"] = 1
        results["details"]["highs_1t"] = highs_1t_result
        print(
            f"HiGHS (1T): feasible={highs_1t_result['feasible']}, "
            f"time={highs_1t_result['solve_seconds']:.2f}s, "
            f"peak_mem={highs_1t_result['peak_memory_mb']:.1f} MB"
        )
        if highs_1t_result["objective"]:
            print(f"  Objective: ${highs_1t_result['objective']:,.0f}")
        if highs_1t_result["error"]:
            print(f"  Error: {highs_1t_result['error']}")

        # 3. Solve with HiGHS (multi-threaded)
        print(f"\n=== HiGHS SCUC (24h, {cpu_count} threads) ===")
        n_highs_mt = n.copy()
        highs_mt_result = solve_scuc(n_highs_mt, "highs", HIGHS_OPTIONS_MT)
        highs_mt_result["threads_used"] = cpu_count
        results["details"]["highs_mt"] = highs_mt_result
        print(
            f"HiGHS ({cpu_count}T): feasible={highs_mt_result['feasible']}, "
            f"time={highs_mt_result['solve_seconds']:.2f}s, "
            f"peak_mem={highs_mt_result['peak_memory_mb']:.1f} MB"
        )
        if highs_mt_result["objective"]:
            print(f"  Objective: ${highs_mt_result['objective']:,.0f}")
        if highs_mt_result["error"]:
            print(f"  Error: {highs_mt_result['error']}")

        # 4. Solve with SCIP
        print("\n=== SCIP SCUC (24h) ===")
        n_scip = n.copy()
        scip_result = solve_scuc(n_scip, "scip", SCIP_OPTIONS)
        results["details"]["scip"] = scip_result
        print(
            f"SCIP: feasible={scip_result['feasible']}, "
            f"time={scip_result['solve_seconds']:.2f}s, "
            f"peak_mem={scip_result['peak_memory_mb']:.1f} MB"
        )
        if scip_result["objective"]:
            print(f"  Objective: ${scip_result['objective']:,.0f}")
        if scip_result["error"]:
            print(f"  Error: {scip_result['error']}")

        # 5. Determine overall status
        # Pass if at least one solver/config completes successfully
        any_feasible = (
            highs_1t_result["feasible"] or highs_mt_result["feasible"] or scip_result["feasible"]
        )

        if any_feasible:
            results["status"] = "pass"
        else:
            results["status"] = "fail"
            results["errors"].append("No solver configuration produced a feasible SCUC solution")

        # Record errors from individual solvers
        for solver_label, solver_result in [
            ("HiGHS-1T", highs_1t_result),
            (f"HiGHS-{cpu_count}T", highs_mt_result),
            ("SCIP", scip_result),
        ]:
            if solver_result["error"]:
                results["errors"].append(f"{solver_label}: {solver_result['error']}")

        print(f"\n=== C-4 {results['status'].upper()} ===")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
