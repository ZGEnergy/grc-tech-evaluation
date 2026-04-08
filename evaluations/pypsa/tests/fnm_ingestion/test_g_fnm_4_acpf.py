"""G-FNM-4: ACPF convergence capability on FNM main island.

Dimension: fnm_ingestion (Suite G)
Network: LARGE — FNM main island (28000 buses, 33000 active branches)
Pass condition: Informational — convergence is a positive finding, not a requirement.
  MATPOWER 8.1 cannot solve this case (voltage collapse at ~30% load).
  If PyPSA converges, that is a solver robustness strength.
Tool: PyPSA 1.1.2

This is a convergence capability test, not a reference comparison.
"""

from __future__ import annotations

import json
import re
import time
import traceback
from pathlib import Path

import numpy as np

CLEANED_M = Path("/workspace/data/fnm/reference/cleaned/fnm_main_island.m")


def parse_matpower_m(filepath: str | Path) -> dict:
    """Parse a MATPOWER .m case file into a PPC dict."""
    with open(filepath) as f:
        content = f.read()

    ppc: dict = {"version": "2"}

    m = re.search(r"mpc\.baseMVA\s*=\s*(\d+\.?\d*)", content)
    if m:
        ppc["baseMVA"] = float(m.group(1))

    for name in ["bus", "gen", "branch"]:
        pattern = rf"mpc\.{name}\s*=\s*\[(.*?)\];"
        m = re.search(pattern, content, re.DOTALL)
        if m:
            data = m.group(1).strip()
            rows = []
            for line in data.split("\n"):
                line = line.strip().rstrip(";")
                if "%" in line:
                    line = line[: line.index("%")]
                line = line.strip()
                if line:
                    vals = [float(x) for x in line.split()]
                    rows.append(vals)
            ppc[name] = np.array(rows)

    return ppc


def run() -> dict:
    """Execute G-FNM-4 ACPF convergence test and return structured results."""
    import tracemalloc

    import pypsa

    results: dict = {
        "status": "informational",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # ── 1. Parse cleaned MATPOWER .m case ────────────────────────────
        ppc = parse_matpower_m(CLEANED_M)
        baseMVA = ppc["baseMVA"]
        bus_array = ppc["bus"]
        gen_array = ppc["gen"]
        branch_array = ppc["branch"]

        results["details"]["baseMVA"] = baseMVA
        results["details"]["tool_version"] = pypsa.__version__

        n_buses = bus_array.shape[0]
        n_branches = branch_array.shape[0]
        n_gens = gen_array.shape[0]
        branch_status = branch_array[:, 10].astype(int)
        n_active = int((branch_status == 1).sum())

        results["details"]["network_size"] = {
            "buses": n_buses,
            "branches_total": n_branches,
            "branches_active": n_active,
            "generators": n_gens,
        }

        results["workarounds"].append(
            "Parsed MATPOWER .m file with regex-based parser since the .mat file "
            "is Octave text format (not scipy-compatible) and PyPSA has no native "
            "MATPOWER reader."
        )

        # ── 2. Import into PyPSA ────────────────────────────────────────
        net = pypsa.Network()
        net.import_from_pypower_ppc(ppc)
        net.set_snapshots([0])

        results["details"]["pypsa_counts"] = {
            "buses": len(net.buses),
            "lines": len(net.lines),
            "transformers": len(net.transformers),
            "generators": len(net.generators),
            "loads": len(net.loads),
        }

        # Verify flat start initialization
        results["details"]["initialization"] = {
            "type": "flat_start",
            "note": "All VM=1.0, VA=0.0 from planning model (no solved voltage profile)",
        }

        # ── 3. Attempt ACPF solve ──────────────────────────────────────
        tracemalloc.start()
        t_solve_start = time.perf_counter()

        # PyPSA's Newton-Raphson AC power flow
        converged = net.pf()

        t_solve = time.perf_counter() - t_solve_start
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mem_mb = peak_mem / (1024 * 1024)

        results["details"]["solve_wall_clock_seconds"] = round(t_solve, 4)
        results["details"]["peak_memory_mb"] = round(peak_mem_mb, 1)

        # ── 4. Interpret convergence result ─────────────────────────────
        # net.pf() returns a dict of DataFrames with convergence info
        # The key is the sub-network index
        if hasattr(converged, "keys"):
            # It's a dict-like return
            conv_info = converged
        else:
            conv_info = converged

        results["details"]["solver"] = "Newton-Raphson (PyPSA built-in)"

        # Extract convergence info from the return value
        convergence_details = {}
        overall_converged = False
        total_iterations = 0
        final_residual = None

        try:
            # PyPSA pf() returns a dict with keys 'converged', 'n_iter', 'error'
            # as DataFrames indexed by sub-network
            if isinstance(conv_info, dict):
                for key, df in conv_info.items():
                    convergence_details[str(key)] = str(df)

                if "converged" in conv_info:
                    conv_df = conv_info["converged"]
                    overall_converged = bool(conv_df.all().all())
                    convergence_details["converged_all"] = overall_converged
                    convergence_details["converged_per_subnetwork"] = (
                        conv_df.to_dict() if hasattr(conv_df, "to_dict") else str(conv_df)
                    )

                if "n_iter" in conv_info:
                    n_iter_df = conv_info["n_iter"]
                    total_iterations = int(n_iter_df.max().max())
                    convergence_details["n_iter_max"] = total_iterations
                    convergence_details["n_iter_details"] = (
                        n_iter_df.to_dict() if hasattr(n_iter_df, "to_dict") else str(n_iter_df)
                    )

                if "error" in conv_info:
                    err_df = conv_info["error"]
                    final_residual = float(err_df.max().max())
                    convergence_details["final_error_max"] = final_residual
                    convergence_details["error_details"] = (
                        err_df.to_dict() if hasattr(err_df, "to_dict") else str(err_df)
                    )
            else:
                convergence_details["raw_return"] = str(conv_info)
        except Exception as e:
            convergence_details["parse_error"] = f"{type(e).__name__}: {e}"

        results["details"]["convergence"] = convergence_details
        results["details"]["converged"] = overall_converged
        results["details"]["convergence_iterations"] = total_iterations
        results["details"]["convergence_residual"] = final_residual

        # ── 5. If converged, extract solution statistics ────────────────
        if overall_converged:
            results["details"]["convergence_finding"] = (
                "POSITIVE: PyPSA converged on the FNM main island with flat start, "
                "where MATPOWER 8.1 failed (voltage collapse at ~30% load)."
            )

            # Extract voltage magnitudes and angles
            try:
                if (
                    hasattr(net, "buses_t")
                    and "v_mag_pu" in net.buses_t
                    and len(net.buses_t.v_mag_pu) > 0
                ):
                    vm = net.buses_t.v_mag_pu.iloc[0].values
                else:
                    vm = net.buses.v_mag_pu.values if "v_mag_pu" in net.buses.columns else None

                if (
                    hasattr(net, "buses_t")
                    and "v_ang" in net.buses_t
                    and len(net.buses_t.v_ang) > 0
                ):
                    va = np.degrees(net.buses_t.v_ang.iloc[0].values)
                else:
                    va = None

                if vm is not None:
                    vm_finite = vm[np.isfinite(vm)]
                    results["details"]["voltage_magnitude"] = {
                        "min_pu": round(float(np.min(vm_finite)), 6),
                        "max_pu": round(float(np.max(vm_finite)), 6),
                        "mean_pu": round(float(np.mean(vm_finite)), 6),
                        "std_pu": round(float(np.std(vm_finite)), 6),
                        "pct_outside_0p95_1p05": round(
                            float(np.mean((vm_finite < 0.95) | (vm_finite > 1.05)) * 100), 2
                        ),
                        "pct_still_1p0": round(float(np.mean(np.isclose(vm_finite, 1.0)) * 100), 2),
                    }

                if va is not None:
                    va_finite = va[np.isfinite(va)]
                    results["details"]["voltage_angle"] = {
                        "min_deg": round(float(np.min(va_finite)), 4),
                        "max_deg": round(float(np.max(va_finite)), 4),
                        "mean_deg": round(float(np.mean(va_finite)), 4),
                        "std_deg": round(float(np.std(va_finite)), 4),
                    }

                # Total losses
                try:
                    total_gen = 0.0
                    total_load = 0.0

                    if (
                        hasattr(net, "generators_t")
                        and "p" in net.generators_t
                        and len(net.generators_t.p) > 0
                    ):
                        total_gen = float(net.generators_t.p.iloc[0].sum())
                    total_load = float(net.loads.p_set.sum())

                    results["details"]["power_balance"] = {
                        "total_generation_mw": round(total_gen, 2),
                        "total_load_mw": round(total_load, 2),
                        "total_losses_mw": round(total_gen - total_load, 2),
                        "loss_percentage": (
                            round((total_gen - total_load) / total_gen * 100, 4)
                            if total_gen > 0
                            else None
                        ),
                    }
                except Exception as e:
                    results["details"]["power_balance_error"] = f"{type(e).__name__}: {e}"

            except Exception as e:
                results["details"]["solution_extraction_error"] = f"{type(e).__name__}: {e}"

        else:
            results["details"]["convergence_finding"] = (
                "EXPECTED: PyPSA did not converge on the FNM main island, "
                "consistent with MATPOWER 8.1 failure. The FNM RAW file is a "
                "planning model with flat start and no solved voltage profile."
            )

        # ── 6. Convergence quality check ────────────────────────────────
        # Per convergence protocol: verify convergence is genuine
        if overall_converged and total_iterations == 0:
            results["details"]["convergence_quality_warning"] = (
                "Zero iterations reported — solver may not have actually run."
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
