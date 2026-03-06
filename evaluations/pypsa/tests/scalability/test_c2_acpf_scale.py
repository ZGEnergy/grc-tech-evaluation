"""C-2: ACPF on MEDIUM (10k-bus) network -- wall-clock, peak memory, iterations."""

import time
import tracemalloc

import pypsa
from matpowercaseframes import CaseFrames

MEDIUM = "/workspace/data/networks/case_ACTIVSg10k.m"


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
    return n


def main():
    print("=" * 70)
    print("C-2: ACPF on MEDIUM (10k-bus)")
    print("=" * 70)

    n = load_network(MEDIUM)
    print(
        f"Network: {len(n.buses)} buses, {len(n.lines)} lines, "
        f"{len(n.transformers)} transformers, {len(n.generators)} generators"
    )

    # Attempt 1: Flat start (default)
    print("\n--- Attempt 1: Flat start ---")
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        info = n.pf()
        wall_clock_flat = time.perf_counter() - t0
        current, peak_flat = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_flat_mb = peak_flat / 1024 / 1024

        if hasattr(info, "converged"):
            converged_flat = bool(info.converged.all())
        else:
            converged_flat = True
        print(f"Converged: {converged_flat}")
        print(f"Wall-clock: {wall_clock_flat:.4f}s")
        print(f"Peak memory: {peak_flat_mb:.2f} MB")
    except Exception as e:
        wall_clock_flat = time.perf_counter() - t0
        current, peak_flat = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_flat_mb = peak_flat / 1024 / 1024
        converged_flat = False
        print(f"FAILED: {e}")
        print(f"Wall-clock: {wall_clock_flat:.4f}s")
        print(f"Peak memory: {peak_flat_mb:.2f} MB")

    # Attempt 2: DC warm start
    print("\n--- Attempt 2: DC warm start ---")
    n2 = load_network(MEDIUM)
    n2.lpf()

    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        info2 = n2.pf()
        wall_clock_dc = time.perf_counter() - t0
        current2, peak_dc = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_dc_mb = peak_dc / 1024 / 1024

        if hasattr(info2, "converged"):
            converged_dc = bool(info2.converged.all())
        else:
            converged_dc = True
        print(f"Converged: {converged_dc}")
        print(f"Wall-clock: {wall_clock_dc:.4f}s")
        print(f"Peak memory: {peak_dc_mb:.2f} MB")
    except Exception as e:
        wall_clock_dc = time.perf_counter() - t0
        current2, peak_dc = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_dc_mb = peak_dc / 1024 / 1024
        converged_dc = False
        print(f"FAILED: {e}")
        print(f"Wall-clock: {wall_clock_dc:.4f}s")

    # Summary stats from best result
    best_n = n if converged_flat else (n2 if converged_dc else None)
    if best_n is not None:
        p_gen = best_n.generators_t.p
        print(
            f"\nGenerator dispatch range: [{p_gen.values.min():.2f}, {p_gen.values.max():.2f}] MW"
        )
        print(f"Total generation: {p_gen.values.sum():.2f} MW")
        print(f"Total load: {best_n.loads.p_set.sum():.2f} MW")

        v_mag = best_n.buses_t.v_mag_pu
        if len(v_mag) > 0:
            print(f"Voltage range: [{v_mag.values.min():.4f}, {v_mag.values.max():.4f}] p.u.")

    # Attempt 3: Relaxed tolerance if both failed
    if not converged_flat and not converged_dc:
        print("\n--- Attempt 3: Relaxed tolerance (1e-3) ---")
        n3 = load_network(MEDIUM)
        n3.lpf()
        tracemalloc.start()
        t0 = time.perf_counter()
        try:
            info3 = n3.pf(x_tol=1e-3)
            wall_clock_relax = time.perf_counter() - t0
            current3, peak_relax = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"Converged: {info3}")
            print(f"Wall-clock: {wall_clock_relax:.4f}s")
        except Exception as e:
            tracemalloc.stop()
            print(f"FAILED: {e}")

    print("\n--- RESULTS ---")
    print(f"flat_start_converged={converged_flat}")
    print(f"flat_start_wall_clock_s={wall_clock_flat:.4f}")
    print(f"flat_start_peak_mb={peak_flat_mb:.2f}")
    print(f"dc_warmstart_converged={converged_dc}")
    print(f"dc_warmstart_wall_clock_s={wall_clock_dc:.4f}")
    print(f"dc_warmstart_peak_mb={peak_dc_mb:.2f}")
    print(f"n_buses={len(n.buses)}")


if __name__ == "__main__":
    main()
