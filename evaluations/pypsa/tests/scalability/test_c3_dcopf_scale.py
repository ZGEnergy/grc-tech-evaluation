"""C-3: DC OPF on MEDIUM (10k-bus) with HiGHS and GLPK."""

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
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0
    return n


def run_dcopf(n, solver_name, solver_options, label):
    print(f"\n--- {label} ---")
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        status, condition = n.optimize(solver_name=solver_name, solver_options=solver_options)
        wall_clock = time.perf_counter() - t0
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / 1024 / 1024

        obj = n.objective
        print(f"Status: {status}, Condition: {condition}")
        print(f"Objective: {obj:.2f}")
        print(f"Wall-clock: {wall_clock:.4f}s")
        print(f"Peak memory: {peak_mb:.2f} MB")
        print(f"Total generation: {n.generators_t.p.values.sum():.2f} MW")
        return {"status": status, "obj": obj, "time": wall_clock, "peak_mb": peak_mb}
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
    print("C-3: DC OPF on MEDIUM (10k-bus) -- HiGHS vs GLPK")
    print("=" * 70)

    # HiGHS -- single-threaded baseline
    n1 = load_network_with_costs(MEDIUM)
    print(f"Network: {len(n1.buses)} buses, {len(n1.lines)} lines, {len(n1.generators)} generators")

    result_highs_1t = run_dcopf(
        n1, "highs", {"time_limit": 300, "presolve": "on", "threads": 1}, "HiGHS (1 thread)"
    )

    # HiGHS -- multi-threaded
    n2 = load_network_with_costs(MEDIUM)
    result_highs_16t = run_dcopf(
        n2, "highs", {"time_limit": 300, "presolve": "on", "threads": 16}, "HiGHS (16 threads)"
    )

    # GLPK
    n3 = load_network_with_costs(MEDIUM)
    result_glpk = run_dcopf(n3, "glpk", {"tm_lim": 300000}, "GLPK")

    # Objective consistency
    print("\n--- Objective Consistency ---")
    objs = {}
    for name, r in [
        ("HiGHS-1t", result_highs_1t),
        ("HiGHS-16t", result_highs_16t),
        ("GLPK", result_glpk),
    ]:
        if r["obj"] is not None:
            objs[name] = r["obj"]
            print(f"  {name}: {r['obj']:.6f}")

    if len(objs) >= 2:
        vals = list(objs.values())
        max_diff = max(vals) - min(vals)
        rel_diff = max_diff / abs(vals[0]) * 100 if vals[0] != 0 else 0
        print(f"  Max abs diff: {max_diff:.6f}")
        print(f"  Relative diff: {rel_diff:.6f}%")

    print("\n--- RESULTS ---")
    for name, r in [
        ("highs_1t", result_highs_1t),
        ("highs_16t", result_highs_16t),
        ("glpk", result_glpk),
    ]:
        print(f"{name}_status={r['status']}")
        print(f"{name}_time_s={r['time']:.4f}")
        print(f"{name}_peak_mb={r['peak_mb']:.2f}")
        if r.get("obj") is not None:
            print(f"{name}_objective={r['obj']:.6f}")


if __name__ == "__main__":
    main()
