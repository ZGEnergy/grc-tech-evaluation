"""C-5: N-M contingency sweep (x=5, m=4) on MEDIUM with pruning. 10-min timeout."""

import itertools
import time
import tracemalloc

import numpy as np
import pypsa
from matpowercaseframes import CaseFrames

MEDIUM = "/workspace/data/networks/case_ACTIVSg10k.m"
TIMEOUT = 600  # 10 minutes


def load_network(filepath):
    cf = CaseFrames(filepath)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc)
    n.lines.loc[n.lines.s_nom == 0, "s_nom"] = 9999.0
    n.transformers.loc[n.transformers.s_nom == 0, "s_nom"] = 9999.0
    # Fix zero-impedance transformers (causes singular matrix)
    n.transformers.loc[n.transformers.x == 0, "x"] = 0.0001
    n.lines.loc[n.lines.x == 0, "x"] = 0.0001
    return n


def check_violations(n, threshold=1.0):
    """Check for line flow violations after DCPF."""
    violations = []
    if len(n.lines_t.p0) > 0:
        p0 = n.lines_t.p0.iloc[0]
        s_nom = n.lines.s_nom
        loading = (p0.abs() / s_nom).dropna()
        violated = loading[loading > threshold]
        for line_name in violated.index:
            violations.append((line_name, loading[line_name]))
    return violations


def main():
    print("=" * 70)
    print("C-5: N-M Contingency Sweep (x=5, m=4) on MEDIUM")
    print("=" * 70)

    n_base = load_network(MEDIUM)
    print(f"Network: {len(n_base.buses)} buses, {len(n_base.lines)} lines")

    # Run base case DCPF
    n_base.lpf()

    # Select top-loaded lines for contingency analysis
    p0 = n_base.lines_t.p0.iloc[0]
    s_nom = n_base.lines.s_nom
    loading = (p0.abs() / s_nom).dropna()
    loading = loading.replace([np.inf, -np.inf], np.nan).dropna()
    loading = loading.sort_values(ascending=False)

    x = 5
    top_lines = loading.head(x).index.tolist()
    print(f"\nTop {x} loaded lines (for N-M sweep):")
    for ln in top_lines:
        print(f"  {ln}: {loading[ln]:.4f} loading ratio")

    # N-M sweep with pruning
    m = 4
    total_cases = 0
    for order in range(1, m + 1):
        total_cases += len(list(itertools.combinations(range(x), order)))
    print(f"\nTotal contingency cases (orders 1-{m}): {total_cases}")

    results_by_order = {}
    pruned_branches = set()
    timed_out = False
    cases_run = 0
    violations_found = 0

    tracemalloc.start()
    t_total = time.perf_counter()

    for order in range(1, m + 1):
        if timed_out:
            break

        combos = list(itertools.combinations(top_lines, order))
        order_times = []
        order_violations = 0
        pruned_count = 0

        print(f"\n--- Order {order}: {len(combos)} combinations ---")

        for combo in combos:
            elapsed = time.perf_counter() - t_total
            if elapsed > TIMEOUT:
                timed_out = True
                print(f"  TIMEOUT after {elapsed:.1f}s")
                break

            # Pruning: skip if any subset was already non-violating
            skip = False
            if order > 1:
                for sub in itertools.combinations(combo, order - 1):
                    if frozenset(sub) in pruned_branches:
                        skip = True
                        break

            if skip:
                pruned_count += 1
                continue

            # Apply contingency
            n_cont = load_network(MEDIUM)
            for line_name in combo:
                if line_name in n_cont.lines.index:
                    n_cont.lines.loc[line_name, "s_nom"] = 0.0001

            t0 = time.perf_counter()
            try:
                n_cont.lpf()
                case_time = time.perf_counter() - t0
            except Exception as e:
                case_time = time.perf_counter() - t0
                print(f"  {combo}: FAILED ({e})")
                order_times.append(case_time)
                cases_run += 1
                continue

            order_times.append(case_time)
            cases_run += 1

            # Check violations
            viols = check_violations(n_cont, threshold=1.0)
            if viols:
                order_violations += len(viols)
                violations_found += len(viols)
                print(f"  {combo}: {len(viols)} violations, {case_time:.3f}s")
            else:
                pruned_branches.add(frozenset(combo))

        avg_time = sum(order_times) / len(order_times) if order_times else 0
        results_by_order[order] = {
            "combos": len(combos),
            "run": len(order_times),
            "pruned": pruned_count,
            "violations": order_violations,
            "avg_time": avg_time,
            "total_time": sum(order_times),
        }
        print(
            f"  Run: {len(order_times)}, Pruned: {pruned_count}, "
            f"Violations: {order_violations}, Avg time: {avg_time:.4f}s"
        )

    total_elapsed = time.perf_counter() - t_total
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1024 / 1024

    pruning_ratio = (
        sum(r["pruned"] for r in results_by_order.values()) / total_cases if total_cases > 0 else 0
    )
    per_case_avg = total_elapsed / cases_run if cases_run > 0 else 0

    print("\n--- Summary ---")
    print(f"Total time: {total_elapsed:.2f}s")
    print(f"Cases run: {cases_run}")
    print(f"Cases pruned: {sum(r['pruned'] for r in results_by_order.values())}")
    print(f"Total violations: {violations_found}")
    print(f"Peak memory: {peak_mb:.2f} MB")
    print(f"Timed out: {timed_out}")
    print(f"Pruning ratio: {pruning_ratio:.2%}")
    print(f"Per-case average: {per_case_avg:.4f}s")

    print("\n--- Per-Order Breakdown ---")
    for order, r in sorted(results_by_order.items()):
        print(
            f"  Order {order}: {r['combos']} combos, {r['run']} run, "
            f"{r['pruned']} pruned, {r['violations']} violations, "
            f"{r['avg_time']:.4f}s avg"
        )

    print("\n--- RESULTS ---")
    print(f"total_time_s={total_elapsed:.4f}")
    print(f"per_case_avg_s={per_case_avg:.4f}")
    print(f"cases_run={cases_run}")
    print(f"pruning_ratio={pruning_ratio:.4f}")
    print(f"peak_memory_mb={peak_mb:.2f}")
    print(f"timed_out={timed_out}")
    print(f"violations_found={violations_found}")


if __name__ == "__main__":
    main()
