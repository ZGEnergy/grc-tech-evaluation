"""C-8: SCOPF on MEDIUM (10k-bus) with 500 line contingencies."""

import time
import tracemalloc

import pypsa
from matpowercaseframes import CaseFrames

MEDIUM = "/workspace/data/networks/case_ACTIVSg10k.m"


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
    # Fix zero-rated branches: use max of existing non-zero values (not 9999 which causes inf in PTDF)
    max_line_snom = n.lines.loc[n.lines.s_nom > 0, "s_nom"].max()
    max_tr_snom = n.transformers.loc[n.transformers.s_nom > 0, "s_nom"].max()
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = max_line_snom if max_line_snom > 0 else 1000.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = (
        max_tr_snom if max_tr_snom > 0 else 1000.0
    )
    # Fix zero-impedance branches that cause singular PTDF B matrix
    n.lines.loc[n.lines.x == 0, "x"] = 0.0001
    n.transformers.loc[n.transformers.x == 0, "x"] = 0.0001
    return n


def main():
    print("=" * 70)
    print("C-8: SCOPF on MEDIUM (10k-bus) -- 500 line contingencies")
    print("=" * 70)

    n = load_network_with_costs(MEDIUM)
    print(
        f"Network: {len(n.buses)} buses, {len(n.lines)} lines, "
        f"{len(n.transformers)} transformers, {len(n.generators)} generators"
    )

    # Select 500 lines for contingency analysis (highest-flow lines from base DCPF)
    print("\nRunning base case DCPF to select monitored lines...")
    n.lpf()
    base_flows = n.lines_t.p0.iloc[0].abs()
    top_500_lines = base_flows.nlargest(500).index.tolist()
    print(f"Selected {len(top_500_lines)} lines for contingency monitoring")

    # Reload for clean optimization
    n = load_network_with_costs(MEDIUM)

    print("\nRunning SCOPF with 500 contingencies...")
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        status, condition = n.optimize.optimize_security_constrained(
            branch_outages=top_500_lines,
            solver_name="highs",
            solver_options={"time_limit": 600, "presolve": "on", "threads": 1},
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

        # Check for binding contingencies
        print(f"\nTotal generation: {n.generators_t.p.values.sum():.2f} MW")

        print("\n--- RESULTS ---")
        print(f"status={status}")
        print(f"objective={obj:.2f}")
        print(f"wall_clock_s={wall_clock:.4f}")
        print(f"peak_memory_mb={peak_mb:.2f}")
        print("n_contingencies=500")
        print("solver=highs")

    except Exception as e:
        wall_clock = time.perf_counter() - t0
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / 1024 / 1024

        print(f"FAILED: {e}")
        print(f"Wall-clock: {wall_clock:.4f}s")
        print(f"Peak memory: {peak_mb:.2f} MB")

        print("\n--- RESULTS ---")
        print("status=FAIL")
        print(f"wall_clock_s={wall_clock:.4f}")
        print(f"peak_memory_mb={peak_mb:.2f}")
        print("n_contingencies=500")
        print(f"error={e}")


if __name__ == "__main__":
    main()
