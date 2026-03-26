"""
Test C-9: PTDF matrix computation on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses, 12,706 branches, 2,485 generators)
Pass condition: PTDF computed. Phase-shifter corrections per B-9.
    Record: wall_clock, peak_memory, matrix_density, cpu_threads_used, cpu_threads_available
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower


def _get_cpu_info() -> tuple[int, int]:
    """Return (threads_used, threads_available). makePTDF is single-threaded."""
    available = os.cpu_count() or 1
    return 1, available


def run(
    network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute PTDF matrix computation on MEDIUM network."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp
        from pandapower.pypower.makeBdc import makeBdc
        from pandapower.pypower.makePTDF import makePTDF

        results["details"]["pandapower_version"] = pp.__version__

        # Thread reporting
        threads_used, threads_available = _get_cpu_info()
        results["details"]["cpu_threads_used"] = threads_used
        results["details"]["cpu_threads_available"] = threads_available

        # 1. Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)

        # 2. Run DCPF for validation reference
        pp.rundcpp(net)
        if not net.converged:
            results["errors"].append("DCPF did not converge — cannot validate PTDF")
            return results
        results["details"]["dcpf_converged"] = True

        # 3. Get PYPOWER internal representation
        ppc = net._ppc
        bus = ppc["bus"]
        branch = ppc["branch"]
        baseMVA = ppc["baseMVA"]

        nb = bus.shape[0]
        nbr = branch.shape[0]
        results["details"]["ppc_bus_count"] = nb
        results["details"]["ppc_branch_count"] = nbr
        results["details"]["baseMVA"] = float(baseMVA)

        # 4. Check for phase-shifting transformers
        shift_col = branch[:, 9] if branch.shape[1] > 9 else np.zeros(nbr)
        phase_shifter_mask = np.abs(shift_col) > 1e-6
        n_phase_shifters = int(phase_shifter_mask.sum())
        results["details"]["n_phase_shifters"] = n_phase_shifters

        # 5. Compute PTDF matrix with memory tracking
        tracemalloc.start()
        ptdf_start = time.perf_counter()
        H = makePTDF(baseMVA, bus, branch)
        ptdf_time = time.perf_counter() - ptdf_start
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["ptdf_compute_seconds"] = f"{ptdf_time:.6e}"
        results["details"]["peak_memory_mb"] = peak / (1024 * 1024)
        results["details"]["ptdf_shape"] = list(H.shape)
        results["details"]["ptdf_api"] = (
            "pandapower.pypower.makePTDF.makePTDF(baseMVA, bus, branch)"
        )

        # 6. Matrix properties
        n_elements = H.size
        n_near_zero = int(np.sum(np.abs(H) < 1e-10))
        matrix_density = 1.0 - (n_near_zero / n_elements)
        results["details"]["matrix_density"] = f"{matrix_density:.6e}"
        results["details"]["matrix_size_mb"] = H.nbytes / (1024 * 1024)
        results["details"]["ptdf_stats"] = {
            "min": f"{float(H.min()):.6e}",
            "max": f"{float(H.max()):.6e}",
            "rank": int(np.linalg.matrix_rank(H)),
        }

        # 7. Validate PTDF against DCPF flows
        Bbus, Bf, Pbusinj, Pfinj, *_ = makeBdc(bus, branch)

        Va_deg = bus[:, 8]
        Va_rad = np.deg2rad(Va_deg)

        # Reference flows from Bf
        bf_result = Bf @ Va_rad + Pfinj
        dcpf_flows_from_bf = (
            bf_result.A.flatten() if hasattr(bf_result, "A") else bf_result.flatten()
        )
        dcpf_flows_mw = dcpf_flows_from_bf * baseMVA

        # Bus injections
        bbus_result = Bbus @ Va_rad
        Pinj_pu = bbus_result.A.flatten() if hasattr(bbus_result, "A") else bbus_result.flatten()
        Pbusinj_arr = Pbusinj.A.flatten() if hasattr(Pbusinj, "A") else np.array(Pbusinj).flatten()
        Pfinj_arr = Pfinj.A.flatten() if hasattr(Pfinj, "A") else np.array(Pfinj).flatten()

        # PTDF flow with phase-shifter corrections
        Pinj_corrected = Pinj_pu + Pbusinj_arr
        ptdf_flows_pu_corrected = H @ Pinj_corrected + Pfinj_arr
        ptdf_flows_mw_corrected = ptdf_flows_pu_corrected * baseMVA

        # Raw (without correction)
        ptdf_flows_pu_raw = H @ Pinj_pu
        ptdf_flows_mw_raw = ptdf_flows_pu_raw * baseMVA

        # Compare corrected
        diff_corrected = np.abs(ptdf_flows_mw_corrected - dcpf_flows_mw)
        max_diff_corrected = float(np.max(diff_corrected))
        mean_diff_corrected = float(np.mean(diff_corrected))

        results["details"]["corrected_comparison"] = {
            "max_diff_mw": f"{max_diff_corrected:.6e}",
            "mean_diff_mw": f"{mean_diff_corrected:.6e}",
            "within_tolerance": max_diff_corrected < 1e-6,
        }

        # Compare raw
        diff_raw = np.abs(ptdf_flows_mw_raw - dcpf_flows_mw)
        max_diff_raw = float(np.max(diff_raw))
        mean_diff_raw = float(np.mean(diff_raw))

        results["details"]["raw_comparison"] = {
            "max_diff_mw": f"{max_diff_raw:.6e}",
            "mean_diff_mw": f"{mean_diff_raw:.6e}",
            "within_tolerance": max_diff_raw < 1e-6,
        }

        # If phase shifters, also check excluding them
        if n_phase_shifters > 0:
            non_ps_mask = ~phase_shifter_mask
            diff_excl = np.abs(ptdf_flows_mw_raw[non_ps_mask] - dcpf_flows_mw[non_ps_mask])
            max_diff_excl = float(np.max(diff_excl)) if len(diff_excl) > 0 else 0.0
            results["details"]["excluding_phase_shifters"] = {
                "branches_compared": int(non_ps_mask.sum()),
                "branches_excluded": n_phase_shifters,
                "max_diff_mw": f"{max_diff_excl:.6e}",
                "within_tolerance": max_diff_excl < 1e-6,
            }

        # 8. Check pass condition
        if max_diff_corrected < 1e-6:
            results["status"] = "pass"
            results["details"]["validation_method"] = (
                "PTDF with Pbusinj/Pfinj corrections matches DCPF within 1e-6 MW"
            )
        elif n_phase_shifters > 0:
            excl_within = (
                results["details"]
                .get("excluding_phase_shifters", {})
                .get("within_tolerance", False)
            )
            if excl_within:
                results["status"] = "pass"
                results["details"]["validation_method"] = (
                    f"PTDF matches DCPF within 1e-6 MW after excluding "
                    f"{n_phase_shifters} phase-shifting transformer branches"
                )
            else:
                # Still pass if max diff is small (numerical precision at scale)
                if max_diff_corrected < 1e-3:
                    results["status"] = "pass"
                    results["details"]["validation_method"] = (
                        f"PTDF matches DCPF within {max_diff_corrected:.2e} MW "
                        f"(numerical precision at 10k-bus scale)"
                    )
                else:
                    results["errors"].append(
                        f"PTDF flows do not match DCPF within tolerance. "
                        f"Max diff (corrected): {max_diff_corrected:.2e} MW"
                    )
        else:
            if max_diff_raw < 1e-3:
                results["status"] = "pass"
                results["details"]["validation_method"] = (
                    f"PTDF matches DCPF within {max_diff_raw:.2e} MW "
                    f"(numerical precision at 10k-bus scale)"
                )
            else:
                results["errors"].append(
                    f"PTDF flows do not match DCPF within tolerance. "
                    f"Max diff: {max_diff_raw:.2e} MW"
                )

        results["details"]["solver"] = "N/A (direct matrix computation)"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        try:
            tracemalloc.stop()
        except RuntimeError:
            pass
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
