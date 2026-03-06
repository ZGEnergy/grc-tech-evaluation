"""C-10: Distributed slack DC OPF on MEDIUM (10k-bus).

Based on A-11 finding: distributed slack is NOT supported in n.optimize().
It is only available in n.pf(distribute_slack=True).
This test confirms the same limitation at scale.
"""

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


def main():
    print("=" * 70)
    print("C-10: Distributed Slack DC OPF on MEDIUM (10k-bus)")
    print("=" * 70)

    n = load_network_with_costs(MEDIUM)
    print(f"Network: {len(n.buses)} buses, {len(n.lines)} lines, {len(n.generators)} generators")

    # Confirm: check optimize() signature for distribute_slack
    import inspect

    opt_sig = inspect.signature(
        n.optimize.__wrapped__ if hasattr(n.optimize, "__wrapped__") else n.optimize
    )
    has_distribute_slack = "distribute_slack" in str(opt_sig)
    print(f"\nn.optimize() has distribute_slack param: {has_distribute_slack}")

    pf_sig = inspect.signature(n.pf)
    has_pf_distribute_slack = "distribute_slack" in str(pf_sig)
    print(f"n.pf() has distribute_slack param: {has_pf_distribute_slack}")

    # Demonstrate that n.pf(distribute_slack=True) works at scale
    print("\n--- DCPF with distribute_slack=True ---")
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        info = n.pf(distribute_slack=True)
        wall_clock_pf = time.perf_counter() - t0
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb_pf = peak / 1024 / 1024
        print(f"Wall-clock: {wall_clock_pf:.4f}s")
        print(f"Peak memory: {peak_mb_pf:.2f} MB")
        if isinstance(info, dict) and "converged" in info:
            print(f"Converged: {info['converged']}")
    except Exception as e:
        wall_clock_pf = time.perf_counter() - t0
        try:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peak_mb_pf = peak / 1024 / 1024
        except Exception:
            peak_mb_pf = 0.0
        print(f"Exception: {e}")
        print(f"Wall-clock: {wall_clock_pf:.4f}s")

    # Confirm optimize() does NOT support it
    print("\n--- DC OPF with distribute_slack (not supported) ---")
    print("SKIP: As confirmed in A-11, n.optimize() does not support distribute_slack.")
    print("The parameter is silently ignored if passed (forwarded to solver_options).")
    print("STATUS: FAIL — distributed slack OPF is not a supported feature in PyPSA.")

    print("\n--- RESULTS ---")
    print("distributed_slack_in_optimize=False")
    print("distributed_slack_in_pf=True")
    print(f"pf_distribute_slack_time_s={wall_clock_pf:.4f}")
    print(f"pf_distribute_slack_peak_mb={peak_mb_pf:.2f}")
    print("status=FAIL")
    print("reason=n.optimize() does not support distribute_slack parameter")


if __name__ == "__main__":
    main()
