"""
Test C-9: PTDF Matrix Computation on MEDIUM

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k — 10,000 buses)
Pass condition: Completes PTDF on MEDIUM. Wall-clock, peak memory, matrix density.
  Phase-shifter correction per B-9.
Tool: PyPSA 1.1.2
"""

import multiprocessing
import os
import sys
import time
import traceback
import tracemalloc

import numpy as np

# Shared loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))
from matpower_loader import load_pypsa

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DEFAULT_NETWORK = os.path.join(REPO_ROOT, "data", "networks", "case_ACTIVSg10k.m")


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Compute PTDF matrix on ACTIVSg10k (10,000 buses).

    Returns:
        dict with standard test result keys.
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
        cpu_threads_available = multiprocessing.cpu_count()
        results["details"]["cpu_threads_available"] = cpu_threads_available
        results["details"]["cpu_threads_used"] = 1

        # 1. Load network
        load_start = time.perf_counter()
        n = load_pypsa(network_file, overwrite_zero_s_nom=True)
        load_elapsed = time.perf_counter() - load_start
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["n_buses"] = len(n.buses)
        results["details"]["n_lines"] = len(n.lines)
        results["details"]["n_transformers"] = len(n.transformers)
        print(
            f"Network loaded: {len(n.buses)} buses, {len(n.lines)} lines, "
            f"{len(n.transformers)} transformers in {load_elapsed:.2f}s"
        )

        # 2. Run DCPF for base-case flow verification
        print("Running base DCPF...")
        n.lpf()
        base_p0_lines = n.lines_t.p0.iloc[0].copy()
        base_p_bus = n.buses_t.p.iloc[0].copy() if len(n.buses_t.p) > 0 else None
        print(f"DCPF complete. Non-zero line flows: {int((base_p0_lines.abs() > 1e-6).sum())}")

        # 3. Determine network topology
        topo_start = time.perf_counter()
        n.determine_network_topology()
        n_sub = len(n.sub_networks)
        topo_elapsed = time.perf_counter() - topo_start
        results["details"]["n_sub_networks"] = n_sub
        results["details"]["topology_seconds"] = topo_elapsed
        print(f"Topology: {n_sub} sub-networks in {topo_elapsed:.2f}s")

        # 4. Find largest sub-network
        largest_sn = None
        max_buses = 0
        for sn in n.sub_networks.obj:
            if len(sn.buses_o) > max_buses:
                max_buses = len(sn.buses_o)
                largest_sn = sn

        if largest_sn is None:
            results["errors"].append("No sub-network found")
            return results

        sn_branches = largest_sn.branches()
        print(f"Largest sub-network: {len(largest_sn.buses_o)} buses, {len(sn_branches)} branches")

        # 5. Compute PTDF
        tracemalloc.start()
        ptdf_start = time.perf_counter()
        largest_sn.calculate_PTDF()
        ptdf_elapsed = time.perf_counter() - ptdf_start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        PTDF = largest_sn.PTDF
        results["details"]["ptdf_compute_seconds"] = round(ptdf_elapsed, 3)
        results["details"]["peak_memory_mb"] = round(peak / (1024 * 1024), 1)
        results["details"]["ptdf_shape"] = list(PTDF.shape)
        results["details"]["ptdf_dtype"] = str(PTDF.dtype)
        print(f"PTDF computed: shape={PTDF.shape} in {ptdf_elapsed:.3f}s")
        print(f"Peak memory: {peak / (1024 * 1024):.1f} MB")

        # 6. Matrix density
        n_total = PTDF.size
        n_nonzero = int(np.count_nonzero(np.abs(PTDF) > 1e-10))
        density = n_nonzero / n_total if n_total > 0 else 0.0
        results["details"]["ptdf_density"] = float(density)
        results["details"]["ptdf_n_nonzero"] = n_nonzero
        results["details"]["ptdf_n_total"] = n_total
        results["details"]["ptdf_max_abs"] = float(np.abs(PTDF).max())
        print(f"Density: {density:.4%} ({n_nonzero}/{n_total} non-zero entries)")

        # 7. Flow verification against DCPF
        if base_p_bus is not None:
            buses_o = list(largest_sn.buses_o)
            base_mva = 100.0
            p_inj_pu = np.array([float(base_p_bus.get(b, 0.0)) / base_mva for b in buses_o])

            predicted_pu = PTDF @ p_inj_pu

            # Build actual flows in sn_branches order
            actual_pu = []
            for comp, bname in sn_branches.index:
                if comp == "Line" and bname in base_p0_lines.index:
                    actual_pu.append(float(base_p0_lines[bname]) / base_mva)
                elif (
                    comp == "Transformer"
                    and len(n.transformers_t.p0) > 0
                    and bname in n.transformers_t.p0.columns
                ):
                    actual_pu.append(float(n.transformers_t.p0.iloc[0][bname]) / base_mva)
                else:
                    actual_pu.append(0.0)
            actual_pu_arr = np.array(actual_pu)

            # Error on branches with meaningful flow
            abs_diff = np.abs(predicted_pu - actual_pu_arr)
            nonzero_mask = np.abs(actual_pu_arr) > 0.001
            n_nonzero_branches = int(nonzero_mask.sum())

            if n_nonzero_branches > 0:
                max_err = float(abs_diff[nonzero_mask].max())
                mean_err = float(abs_diff[nonzero_mask].mean())
                n_within_tol = int((abs_diff[nonzero_mask] < 0.01).sum())
                pct_within = n_within_tol / n_nonzero_branches * 100

                results["details"]["flow_verification"] = {
                    "n_branches_with_flow": n_nonzero_branches,
                    "max_abs_error_pu": f"{max_err:.6e}",
                    "mean_abs_error_pu": f"{mean_err:.6e}",
                    "n_within_0.01pu": n_within_tol,
                    "pct_within_tolerance": round(pct_within, 1),
                }
                print(f"Flow verification ({n_nonzero_branches} branches):")
                print(f"  Max error: {max_err:.6e} pu, Mean: {mean_err:.6e} pu")
                print(f"  Within 0.01 pu: {n_within_tol}/{n_nonzero_branches} ({pct_within:.1f}%)")

        # 8. Phase-shifter check
        # ACTIVSg10k has some phase-shifting transformers (SHIFT != 0)
        from matpowercaseframes import CaseFrames

        cf = CaseFrames(network_file)
        if hasattr(cf, "branch") and cf.branch.shape[1] > 9:
            shift_col = cf.branch.iloc[:, 9]  # SHIFT column (0-indexed col 9)
            n_phase_shifters = int((shift_col.abs() > 1e-6).sum())
            results["details"]["n_phase_shifters"] = n_phase_shifters
            print(f"Phase shifters in raw data: {n_phase_shifters}")

        results["status"] = "pass"
        print(f"\n=== C-9 PASS: PTDF {PTDF.shape} in {ptdf_elapsed:.3f}s ===")

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
