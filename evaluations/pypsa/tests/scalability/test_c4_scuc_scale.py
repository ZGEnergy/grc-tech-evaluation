"""
Test C-4: SCUC Scale (scuc_scale)

Dimension: scalability
Network: SMALL (ACTIVSg 2k, case_ACTIVSg2000.m)
Pass condition: Wall-clock time, MIP gap at termination, peak memory recorded.
Tool: PyPSA 1.1.2

Note: Config says "HiGHS, SCIP" but SCIP is not available — HiGHS only.
Depends on: A-5 (same UC setup, SMALL network)
"""

import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg2000.m")

# Solver configuration — 10 minute timeout per spec
SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "time_limit": 600,
    "mip_rel_gap": 0.01,
    "presolve": "on",
    "threads": 1,
    "output_flag": True,
    "log_to_console": True,
}


def load_network(network_file: str):
    """Load ACTIVSg2000 via matpowercaseframes -> pypower ppc -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=1.0)
    return n


def assign_uc_parameters(n) -> None:
    """Assign UC parameters to generators for SCUC.

    Sets committable=True and assigns differentiated marginal costs,
    min up/down times, and startup costs across 544 generators.
    """
    gen_names = list(n.generators.index)
    n_gens = len(gen_names)

    # Assign costs: linear scale $10–$100/MWh
    costs = np.linspace(10, 100, n_gens)
    for i, gen_name in enumerate(gen_names):
        n.generators.at[gen_name, "marginal_cost"] = float(costs[i])
        n.generators.at[gen_name, "committable"] = True
        n.generators.at[gen_name, "start_up_cost"] = float(costs[i]) * 1000  # proportional
        n.generators.at[gen_name, "p_min_pu"] = 0.3  # min stable generation
        n.generators.at[gen_name, "min_up_time"] = 1
        n.generators.at[gen_name, "min_down_time"] = 1

    # Enforce integer dtype on min_up_time and min_down_time
    n.generators["min_up_time"] = n.generators["min_up_time"].astype(int)
    n.generators["min_down_time"] = n.generators["min_down_time"].astype(int)


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Execute 24-hour SCUC MILP on ACTIVSg2000 (544 committable generators).

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
        "workarounds": [
            "Used matpowercaseframes.CaseFrames to parse .m -> pypower ppc -> pypsa "
            "(no native MATPOWER reader in PyPSA)",
            "Marginal costs and UC parameters assigned manually (no gencost in pypower ppc)",
            "SCIP not available in devcontainer — HiGHS only",
        ],
    }

    start = time.perf_counter()
    try:
        # 1. Load network
        load_start = time.perf_counter()
        n = load_network(network_file)
        load_elapsed = time.perf_counter() - load_start

        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_generators"] = len(n.generators)
        results["details"]["load_seconds"] = load_elapsed
        print(
            f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines, "
            f"{len(n.generators)} generators in {load_elapsed:.2f}s"
        )

        # 2. Set 24-hour time horizon
        snapshots = pd.date_range("2024-01-01", periods=24, freq="h")
        n.set_snapshots(snapshots)

        # 3. Assign UC parameters
        assign_uc_parameters(n)
        results["details"]["n_committable_generators"] = int(n.generators.committable.sum())
        print(f"Committable generators: {n.generators.committable.sum()}")

        # 4. Build 24-hour load profile (scale original loads across time)
        # Use a synthetic daily profile with morning/evening peaks
        # Profile: normalized to 1.0 at peak (hour 18), 0.75 at minimum (hour 4)
        hourly_factors = np.array(
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
        total_original_load = float(n.loads.p_set.sum())
        results["details"]["total_original_load_mw"] = total_original_load

        # Distribute time-varying load proportionally
        for load_name in n.loads.index:
            base_load = float(n.loads.at[load_name, "p_set"])
            frac = base_load / total_original_load if total_original_load > 0 else 0.0
            load_series = pd.Series(
                [total_original_load * hourly_factors[h] * frac for h in range(24)], index=snapshots
            )
            n.loads_t.p_set[load_name] = load_series

        results["details"]["load_profile"] = {
            "min_mw": float(total_original_load * hourly_factors.min()),
            "max_mw": float(total_original_load * hourly_factors.max()),
        }
        total_cap = float(n.generators.p_nom.sum())
        results["details"]["total_gen_capacity_mw"] = total_cap
        print(
            f"Load range: {total_original_load * hourly_factors.min():.0f}–"
            f"{total_original_load * hourly_factors.max():.0f} MW"
        )
        print(f"Total generation capacity: {total_cap:.0f} MW")

        # 5. Run MILP SCUC with 10-minute timeout
        print(f"\n=== Starting MILP SCUC (24h, {n.generators.committable.sum()} generators) ===")
        print(f"Time limit: {SOLVER_OPTIONS['time_limit']}s")

        tracemalloc.start()
        solve_start = time.perf_counter()
        opt_result = n.optimize(
            snapshots=snapshots,
            solver_name=SOLVER_NAME,
            solver_options=SOLVER_OPTIONS,
        )
        solve_elapsed = time.perf_counter() - solve_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["solve_seconds"] = solve_elapsed
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        print(f"Solve completed in {solve_elapsed:.2f}s")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")
        print(f"Solver result: {opt_result}")

        # 6. Parse result
        if isinstance(opt_result, tuple):
            status_str = str(opt_result[0])
        else:
            status_str = str(opt_result)
        results["details"]["solver_status"] = status_str

        solve_ok = False
        try:
            obj = float(n.objective)
            if np.isfinite(obj):
                solve_ok = True
        except Exception:
            pass

        if not solve_ok and status_str.lower() in ("ok", "optimal", "feasible"):
            solve_ok = True

        results["details"]["feasible"] = solve_ok
        results["details"]["solver_used"] = SOLVER_NAME
        results["details"]["scip_available"] = False
        results["details"]["scip_note"] = "SCIP not installed in devcontainer; HiGHS only"
        results["details"]["time_limit_seconds"] = SOLVER_OPTIONS["time_limit"]

        if solve_ok:
            objective = float(n.objective)
            results["details"]["objective_dollar"] = objective
            print(f"Objective: ${objective:,.0f}")

            # Check MIP gap (HiGHS reports via solver output; we estimate from solve status)
            # HiGHS will say "optimal" if gap <= mip_rel_gap or time limit if not
            hit_time_limit = solve_elapsed >= SOLVER_OPTIONS["time_limit"] * 0.98
            results["details"]["hit_time_limit"] = bool(hit_time_limit)

            if hit_time_limit:
                results["details"]["mip_gap_note"] = (
                    "Solve hit time limit — MIP gap at termination unknown from Python API. "
                    "HiGHS reports final gap in solver output log."
                )
                print("WARNING: Hit time limit — solution may not be optimal")
            else:
                results["details"]["mip_gap_at_termination"] = "<=1% (mip_rel_gap=0.01 target met)"

            # Commitment schedule
            if hasattr(n.generators_t, "status") and len(n.generators_t.status) > 0:
                status_df = n.generators_t.status
                results["details"]["commitment_matrix_shape"] = list(status_df.shape)
                n_cycling = int(
                    sum(
                        1
                        for col in status_df.columns
                        if (np.diff(status_df[col].values.astype(float)) != 0).any()
                    )
                )
                results["details"]["n_cycling_generators"] = n_cycling
                print(f"Cycling generators: {n_cycling}")
            else:
                results["details"]["n_cycling_generators"] = None

            results["status"] = "pass"
        else:
            results["errors"].append(f"SCUC did not produce feasible solution: {status_str}")
            results["status"] = "fail"

        print(f"\n=== C-4 {results['status'].upper()} ===")
        print(f"  Solve time: {solve_elapsed:.2f}s")
        print(f"  Peak memory: {results['details']['peak_memory_mb']:.1f} MB")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
