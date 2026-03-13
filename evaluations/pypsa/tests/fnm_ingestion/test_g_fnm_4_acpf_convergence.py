"""
Test G-FNM-4: ACPF Convergence

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01, ~30000 buses)
Pass condition: Convergence is a positive finding, not a requirement. Record
  convergence yes/no, algorithm, residual, iterations. No reference solution
  (MATPOWER cannot solve this case). Non-convergence = informational finding.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import re
import time
import traceback
from pathlib import Path

import numpy as np

CLEANED_MAT = Path("/workspace/data/fnm/reference/cleaned/fnm_main_island.mat")
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


def load_cleaned_case() -> tuple[dict, str]:
    """Load the pre-cleaned MATPOWER case. Prefer .m parser over scipy .mat.

    Note: fnm_main_island.mat is an Octave text-format .mat file, not scipy-compatible.
    The .m file is the reliably-parseable format.
    """
    if CLEANED_M.exists():
        return parse_matpower_m(CLEANED_M), "m"
    elif CLEANED_MAT.exists():
        import scipy.io

        try:
            mat = scipy.io.loadmat(str(CLEANED_MAT))
            mpc_struct = mat["mpc"][0, 0]
            ppc = {
                "version": "2",
                "baseMVA": float(mpc_struct["baseMVA"].flat[0]),
                "bus": mpc_struct["bus"],
                "gen": mpc_struct["gen"],
                "branch": mpc_struct["branch"],
            }
            return ppc, "mat"
        except ValueError:
            raise FileNotFoundError(
                f"{CLEANED_MAT} is Octave text format (not scipy-compatible) "
                f"and {CLEANED_M} not found"
            )
    else:
        raise FileNotFoundError(f"Neither {CLEANED_MAT} nor {CLEANED_M} found")


def run() -> dict:
    """Execute G-FNM-4 ACPF convergence test and return structured results.

    Returns:
        dict with keys:
        - status: always "informational" for this test
        - wall_clock_seconds: float
        - details: dict with convergence info
        - errors: list of error messages
        - workarounds: list of workaround descriptions
    """
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
        # ── 1. Load cleaned MATPOWER case ────────────────────────────────
        ppc, load_method = load_cleaned_case()
        baseMVA = ppc["baseMVA"]
        bus_array = ppc["bus"]
        gen_array = ppc["gen"]
        branch_array = ppc["branch"]

        results["details"]["baseMVA"] = baseMVA
        results["details"]["tool_version"] = pypsa.__version__
        results["details"]["load_method"] = load_method

        if load_method == "m":
            results["workarounds"].append(
                "Parsed MATPOWER .m file with regex-based parser since the .mat file "
                "is Octave text format (not scipy-compatible) and PyPSA has no native "
                "MATPOWER reader."
            )
        else:
            results["workarounds"].append(
                "Loaded pre-cleaned MATPOWER .mat file via scipy.io.loadmat. "
                "PyPSA has no native MATPOWER reader."
            )

        branch_status = branch_array[:, 10].astype(int)
        n_active = int((branch_status == 1).sum())

        results["details"]["network_size"] = {
            "buses": int(bus_array.shape[0]),
            "branches_total": int(branch_array.shape[0]),
            "branches_active": n_active,
            "generators": int(gen_array.shape[0]),
        }

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
        results["details"]["solver"] = "Newton-Raphson (PyPSA built-in)"

        # ── 4. Interpret convergence result ─────────────────────────────
        convergence_details: dict = {}
        overall_converged = False
        total_iterations = 0
        final_residual = None

        try:
            if isinstance(converged, dict):
                for key, df in converged.items():
                    convergence_details[str(key)] = str(df)

                if "converged" in converged:
                    conv_df = converged["converged"]
                    overall_converged = bool(conv_df.all().all())
                    convergence_details["converged_all"] = overall_converged
                    convergence_details["converged_per_subnetwork"] = (
                        conv_df.to_dict() if hasattr(conv_df, "to_dict") else str(conv_df)
                    )

                if "n_iter" in converged:
                    n_iter_df = converged["n_iter"]
                    total_iterations = int(n_iter_df.max().max())
                    convergence_details["n_iter_max"] = total_iterations

                if "error" in converged:
                    err_df = converged["error"]
                    max_err = err_df.max().max()
                    final_residual = float(max_err) if not np.isnan(max_err) else None
                    convergence_details["final_error_max"] = str(max_err)
            else:
                convergence_details["raw_return"] = str(converged)
        except Exception as e:
            convergence_details["parse_error"] = f"{type(e).__name__}: {e}"

        results["details"]["convergence"] = convergence_details
        results["details"]["converged"] = overall_converged
        results["details"]["convergence_iterations"] = total_iterations
        results["details"]["convergence_residual"] = final_residual

        # ── 5. Extract solution statistics if converged ─────────────────
        if overall_converged:
            results["details"]["convergence_finding"] = (
                "POSITIVE: PyPSA converged on the ERCOT FNM main island with flat start, "
                "where MATPOWER 8.1 failed (voltage collapse at ~30% load)."
            )

            try:
                if (
                    hasattr(net, "buses_t")
                    and "v_mag_pu" in net.buses_t
                    and len(net.buses_t.v_mag_pu) > 0
                ):
                    vm = net.buses_t.v_mag_pu.iloc[0].values
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

                # Convergence quality check per convergence protocol
                if total_iterations == 0:
                    results["details"]["convergence_quality_warning"] = (
                        "Zero iterations reported — solver may not have actually run. "
                        "Convergence at initial guess is suspect."
                    )
            except Exception as e:
                results["details"]["solution_extraction_error"] = f"{type(e).__name__}: {e}"
        else:
            results["details"]["convergence_finding"] = (
                "EXPECTED: PyPSA did not converge on the ERCOT FNM main island, "
                "consistent with MATPOWER 8.1 failure. The FNM RAW file is a "
                "planning model with flat start and no solved voltage profile."
            )

        results["details"]["matpower_comparison"] = {
            "matpower_converged": False,
            "matpower_methods_tried": [
                "NR (flat start, all variants: NR, NR-IC, NR-SP, NR-SH, NR-IH)",
                "FDXB/FDBX (1000 iterations)",
                "Manual continuation (1%→30% converged, fails at 35%)",
                "runcpf continuation power flow (stuck at nose point ~30%)",
            ],
            "matpower_max_load_pct": 30,
            "source": "data/fnm/reference/acpf/summary_acpf.json",
            "note": "No reference ACPF solution exists; convergence is a positive finding",
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = round(time.perf_counter() - start, 3)

    return results


if __name__ == "__main__":
    import json as _json

    result = run()
    print(_json.dumps(result, indent=2, default=str))
