"""
Test B-9: Compute PTDF matrix and verify against DCPF flows

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: PTDF matrix accessible via native API, internal matrix
    extraction, or unit-injection computation. Flow predictions match DCPF
    results within numerical tolerance (1e-6). If the network contains
    phase-shifting transformers (nonzero SHIFT column in branch data), the PTDF
    validation must either (a) apply Pbusinj/Pfinj correction terms from the
    admittance matrix construction, or (b) exclude branches with nonzero shift
    angles from the accuracy comparison.
Tool: pandapower 3.4.0

Note: pandapower has pandapower.pypower.makePTDF.makePTDF(). Case39 has
phase-shifting transformers -- handle per methodology guardrails.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute PTDF extraction and validation test."""
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

        # 1. Load network and run DCPF
        net = load_pandapower(network_file)
        pp.rundcpp(net)

        if not net.converged:
            results["errors"].append("DCPF did not converge")
            return results

        # 2. Get the internal PYPOWER representation
        ppc = net._ppc
        bus = ppc["bus"]
        branch = ppc["branch"]
        baseMVA = ppc["baseMVA"]

        nb = bus.shape[0]
        nbr = branch.shape[0]
        results["details"]["num_buses"] = nb
        results["details"]["num_branches"] = nbr
        results["details"]["baseMVA"] = float(baseMVA)

        # 3. Check for phase-shifting transformers
        # MATPOWER branch column 9 = SHIFT (phase shift angle in degrees)
        shift_col = branch[:, 9] if branch.shape[1] > 9 else np.zeros(nbr)
        phase_shifter_mask = np.abs(shift_col) > 1e-6
        n_phase_shifters = int(phase_shifter_mask.sum())
        phase_shifter_indices = np.where(phase_shifter_mask)[0].tolist()

        results["details"]["n_phase_shifters"] = n_phase_shifters
        results["details"]["phase_shifter_branch_indices"] = phase_shifter_indices
        if n_phase_shifters > 0:
            results["details"]["phase_shifter_shifts_deg"] = [
                float(shift_col[i]) for i in phase_shifter_indices
            ]

        # 4. Compute PTDF matrix using pandapower's makePTDF
        ptdf_start = time.perf_counter()
        H = makePTDF(baseMVA, bus, branch)
        ptdf_time = time.perf_counter() - ptdf_start

        results["details"]["ptdf_shape"] = list(H.shape)
        results["details"]["ptdf_compute_seconds"] = ptdf_time
        results["details"]["ptdf_api"] = (
            "pandapower.pypower.makePTDF.makePTDF(baseMVA, bus, branch)"
        )

        # 5. Get DCPF results for comparison
        # Branch flows from DCPF (MW)
        dcpf_flows_mw = branch[:, 13]  # PF column
        results["details"]["dcpf_flows_sample"] = dcpf_flows_mw[:10].tolist()

        # Compute Pinj from voltage angles using Bf (avoids bus injection reconstruction)
        Bbus, Bf, Pbusinj, Pfinj, *_ = makeBdc(bus, branch)

        # Va from DCPF (radians)
        Va_deg = bus[:, 8]  # VA column in degrees
        Va_rad = np.deg2rad(Va_deg)

        # Compute flows from Bf: flow_pu = Bf @ Va + Pfinj
        dcpf_flows_from_bf = (
            (Bf @ Va_rad + Pfinj).A.flatten()
            if hasattr(Bf @ Va_rad + Pfinj, "A")
            else (Bf @ Va_rad + Pfinj).flatten()
        )

        # Convert to MW
        dcpf_flows_from_bf_mw = dcpf_flows_from_bf * baseMVA

        results["details"]["dcpf_flows_from_bf_sample"] = dcpf_flows_from_bf_mw[:10].tolist()

        # 6. Compute PTDF-predicted flows
        # Pinj = Bbus @ Va + Pbusinj (in per-unit)
        # But PTDF gives: flow_pu = H @ Pinj
        # We need Pinj in per-unit
        Pinj_pu = (
            (Bbus @ Va_rad).A.flatten()
            if hasattr(Bbus @ Va_rad, "A")
            else (Bbus @ Va_rad).flatten()
        )

        # Add Pbusinj correction for phase shifters
        Pbusinj_arr = Pbusinj.A.flatten() if hasattr(Pbusinj, "A") else np.array(Pbusinj).flatten()
        Pfinj_arr = Pfinj.A.flatten() if hasattr(Pfinj, "A") else np.array(Pfinj).flatten()

        # Net injection including phase shifter corrections
        Pinj_corrected = Pinj_pu + Pbusinj_arr

        # PTDF flow prediction: H @ Pinj (without correction)
        ptdf_flows_pu_raw = H @ Pinj_pu
        ptdf_flows_mw_raw = ptdf_flows_pu_raw * baseMVA

        # PTDF flow prediction with phase-shifter corrections:
        # flow = H @ (Pinj + Pbusinj) + Pfinj
        ptdf_flows_pu_corrected = H @ Pinj_corrected + Pfinj_arr
        ptdf_flows_mw_corrected = ptdf_flows_pu_corrected * baseMVA

        # 7. Compare PTDF predictions against DCPF flows
        # Use dcpf_flows_from_bf_mw as the reference (computed from Bf @ Va + Pfinj)

        # Raw comparison (without correction)
        diff_raw = np.abs(ptdf_flows_mw_raw - dcpf_flows_from_bf_mw)
        max_diff_raw = float(np.max(diff_raw))
        mean_diff_raw = float(np.mean(diff_raw))

        # Corrected comparison
        diff_corrected = np.abs(ptdf_flows_mw_corrected - dcpf_flows_from_bf_mw)
        max_diff_corrected = float(np.max(diff_corrected))
        mean_diff_corrected = float(np.mean(diff_corrected))

        results["details"]["raw_comparison"] = {
            "max_diff_mw": max_diff_raw,
            "mean_diff_mw": mean_diff_raw,
            "within_tolerance": max_diff_raw < 1e-6,
        }

        results["details"]["corrected_comparison"] = {
            "max_diff_mw": max_diff_corrected,
            "mean_diff_mw": mean_diff_corrected,
            "within_tolerance": max_diff_corrected < 1e-6,
        }

        # 8. If phase shifters present, also compare excluding phase-shifter branches
        if n_phase_shifters > 0:
            non_ps_mask = ~phase_shifter_mask
            diff_excl = np.abs(ptdf_flows_mw_raw[non_ps_mask] - dcpf_flows_from_bf_mw[non_ps_mask])
            max_diff_excl = float(np.max(diff_excl)) if len(diff_excl) > 0 else 0.0
            mean_diff_excl = float(np.mean(diff_excl)) if len(diff_excl) > 0 else 0.0

            results["details"]["excluding_phase_shifters"] = {
                "branches_compared": int(non_ps_mask.sum()),
                "branches_excluded": n_phase_shifters,
                "max_diff_mw": max_diff_excl,
                "mean_diff_mw": mean_diff_excl,
                "within_tolerance": max_diff_excl < 1e-6,
            }

        # 9. Report worst branches
        worst_raw_idx = int(np.argmax(diff_raw))
        results["details"]["worst_branch_raw"] = {
            "branch_index": worst_raw_idx,
            "from_bus": int(branch[worst_raw_idx, 0]),
            "to_bus": int(branch[worst_raw_idx, 1]),
            "diff_mw": float(diff_raw[worst_raw_idx]),
            "is_phase_shifter": bool(phase_shifter_mask[worst_raw_idx]),
            "shift_deg": float(shift_col[worst_raw_idx]),
        }

        # 10. PTDF matrix properties
        results["details"]["ptdf_stats"] = {
            "min": float(H.min()),
            "max": float(H.max()),
            "sparsity": float(np.sum(np.abs(H) < 1e-10) / H.size),
            "rank": int(np.linalg.matrix_rank(H)),
        }

        # 11. Check pass condition
        # Use corrected comparison or excluded comparison
        if max_diff_corrected < 1e-6:
            results["status"] = "pass"
            results["details"]["validation_method"] = (
                "PTDF with Pbusinj/Pfinj correction terms matches DCPF within 1e-6 MW"
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
                results["errors"].append(
                    f"PTDF flows do not match DCPF within tolerance. "
                    f"Max diff (corrected): {max_diff_corrected:.2e} MW, "
                    f"Max diff (excl PS): {max_diff_excl:.2e} MW"
                )
        else:
            results["errors"].append(
                f"PTDF flows do not match DCPF within tolerance. Max diff: {max_diff_raw:.2e} MW"
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
