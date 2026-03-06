"""C-4: SCUC 24hr on SMALL (ACTIVSg2000) with HiGHS and SCIP."""

import time
import tracemalloc

import numpy as np
import pandas as pd
import pypsa
from matpowercaseframes import CaseFrames

SMALL = "/workspace/data/networks/case_ACTIVSg2000.m"


def load_network_with_costs(filepath):
    cf = CaseFrames(filepath)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None:
        ppc["gencost"] = cf.gencost.values
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    if hasattr(cf, "gencost") and cf.gencost is not None:
        gc = cf.gencost.values
        for i, gen_name in enumerate(n.generators.index):
            if i < len(gc):
                cost_type = int(gc[i, 0])
                if cost_type == 2:
                    n_coeffs = int(gc[i, 3])
                    if n_coeffs == 2:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 4]
                    elif n_coeffs >= 3:
                        n.generators.loc[gen_name, "marginal_cost"] = gc[i, 5]
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0
    return n


def setup_24h(n):
    """Set up 24-hour snapshots with load profile."""
    snapshots = pd.date_range("2024-01-01", periods=24, freq="h")
    n.set_snapshots(snapshots)

    # Create a realistic daily load profile (normalized)
    hours = np.arange(24)
    load_profile = 0.7 + 0.3 * np.sin((hours - 6) * np.pi / 12)
    load_profile = np.clip(load_profile, 0.6, 1.0)

    # Set time-varying loads
    for load_name in n.loads.index:
        base_load = n.loads.loc[load_name, "p_set"]
        n.loads_t.p_set[load_name] = base_load * load_profile

    # Add committable status to generators (makes it a UC problem)
    n.generators["committable"] = True
    # Set minimum up/down times
    n.generators["min_up_time"] = 2
    n.generators["min_down_time"] = 2
    # Set startup/shutdown costs
    n.generators["start_up_cost"] = n.generators["p_nom"] * 5.0  # $/MW startup
    n.generators["shut_down_cost"] = n.generators["p_nom"] * 2.0
    # Set p_min_pu for committed generators
    n.generators["p_min_pu"] = 0.3

    return n


def run_scuc(n, solver_name, solver_options, label):
    print(f"\n--- {label} ---")
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        status, condition = n.optimize(
            solver_name=solver_name,
            solver_options=solver_options,
        )
        wall_clock = time.perf_counter() - t0
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / 1024 / 1024

        obj = n.objective
        print(f"Status: {status}, Condition: {condition}")
        print(f"Objective: ${obj:,.2f}")
        print(f"Wall-clock: {wall_clock:.4f}s")
        print(f"Peak memory: {peak_mb:.2f} MB")

        # Commitment stats
        if hasattr(n, "generators_t") and "status" in n.generators_t:
            status_df = n.generators_t.status
            n_committed = (status_df > 0.5).sum(axis=1)
            print(
                f"Committed generators: min={n_committed.min()}, "
                f"max={n_committed.max()}, mean={n_committed.mean():.1f}"
            )

        return {
            "status": status,
            "obj": obj,
            "time": wall_clock,
            "peak_mb": peak_mb,
        }
    except Exception as e:
        wall_clock = time.perf_counter() - t0
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / 1024 / 1024
        print(f"FAILED: {e}")
        print(f"Wall-clock: {wall_clock:.4f}s")
        print(f"Peak memory: {peak_mb:.2f} MB")
        return {
            "status": "FAIL",
            "obj": None,
            "time": wall_clock,
            "peak_mb": peak_mb,
            "error": str(e),
        }


def main():
    print("=" * 70)
    print("C-4: SCUC 24hr on SMALL (ACTIVSg2000) -- HiGHS vs SCIP")
    print("=" * 70)

    # HiGHS (1 thread)
    n1 = load_network_with_costs(SMALL)
    n1 = setup_24h(n1)
    print(
        f"Network: {len(n1.buses)} buses, {len(n1.lines)} lines, "
        f"{len(n1.generators)} generators, {len(n1.snapshots)} snapshots"
    )

    result_highs = run_scuc(
        n1,
        "highs",
        {"time_limit": 300, "presolve": "on", "threads": 1, "mip_rel_gap": 0.01},
        "HiGHS (1 thread)",
    )

    # SCIP (1 thread)
    n2 = load_network_with_costs(SMALL)
    n2 = setup_24h(n2)
    result_scip = run_scuc(
        n2,
        "scip",
        {"limits/time": 300, "limits/gap": 0.01, "lp/threads": 1},
        "SCIP (1 thread)",
    )

    print("\n--- RESULTS ---")
    for name, r in [("highs", result_highs), ("scip", result_scip)]:
        print(f"{name}_status={r['status']}")
        print(f"{name}_time_s={r['time']:.4f}")
        print(f"{name}_peak_mb={r['peak_mb']:.2f}")
        if r.get("obj") is not None:
            print(f"{name}_objective={r['obj']:.2f}")


if __name__ == "__main__":
    main()
