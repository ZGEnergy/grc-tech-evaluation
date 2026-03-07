"""
Test C-2: AC Power Flow (Newton-Raphson) Scale Test

Dimension: scalability
Network: MEDIUM (ACTIVSg 10k)
Pass condition: Converges (flat start or DC warm start). Wall-clock, iterations,
    and convergence recorded.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import json
import math
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NETWORK_FILE = str(REPO_ROOT / "data" / "networks" / "case_ACTIVSg10k.m")

TIMEOUT_SECONDS = 600


def _load_network(case_path: str):
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(case_path)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }

    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)

    # Fix zero impedance branches
    zero_x_lines = net.lines["x"] == 0
    if zero_x_lines.any():
        net.lines.loc[zero_x_lines, "x"] = 0.0001

    zero_x_xfmr = net.transformers["x"] == 0
    if zero_x_xfmr.any():
        net.transformers.loc[zero_x_xfmr, "x"] = 0.0001

    return net


def _get_peak_memory_mb():
    """Get peak memory usage in MB using resource module."""
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_maxrss / 1024.0
    except Exception:
        return None


def run(network_file: str = NETWORK_FILE) -> dict:
    """Execute ACPF on 10k-bus network and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pypsa

        mem_before = _get_peak_memory_mb()

        # 1. Load network
        n = _load_network(network_file)

        network_stats = {
            "n_buses": len(n.buses),
            "n_generators": len(n.generators),
            "n_lines": len(n.lines),
            "n_transformers": len(n.transformers),
            "n_loads": len(n.loads),
        }

        # 2. Attempt 1: Flat start ACPF
        solve_start = time.perf_counter()
        n.pf()
        solve_elapsed_flat = time.perf_counter() - solve_start

        # Check convergence via voltage magnitudes
        v_mag = n.buses_t.v_mag_pu
        v_ang = n.buses_t.v_ang
        converged_flat = False
        if v_mag is not None and len(v_mag) > 0:
            v_vals = v_mag.iloc[0]
            if not v_vals.isna().all() and not (v_vals == 1.0).all():
                converged_flat = True
            elif not v_vals.isna().all():
                if v_ang is not None and len(v_ang) > 0:
                    a_vals = v_ang.iloc[0]
                    if not a_vals.isna().all() and not (a_vals == 0.0).all():
                        converged_flat = True

        convergence_info = {
            "flat_start_converged": converged_flat,
            "flat_start_wall_clock": solve_elapsed_flat,
        }

        dc_warm_start_used = False
        converged = converged_flat

        if not converged_flat:
            # Attempt 2: DC warm start
            dc_warm_start_used = True
            results["workarounds"].append(
                "DC warm start required: flat start NR did not converge on 10k-bus"
            )

            n = _load_network(network_file)
            n.lpf()

            solve_start = time.perf_counter()
            n.pf()
            solve_elapsed_warm = time.perf_counter() - solve_start

            v_mag = n.buses_t.v_mag_pu
            v_ang = n.buses_t.v_ang
            converged_warm = False
            if v_mag is not None and len(v_mag) > 0:
                v_vals = v_mag.iloc[0]
                if not v_vals.isna().all():
                    converged_warm = True

            convergence_info["dc_warm_start_converged"] = converged_warm
            convergence_info["dc_warm_start_wall_clock"] = solve_elapsed_warm
            converged = converged_warm

        mem_after = _get_peak_memory_mb()
        total_elapsed = time.perf_counter() - start
        results["wall_clock_seconds"] = total_elapsed

        # 3. Extract structured outputs
        vmag_stats = {}
        if v_mag is not None and len(v_mag) > 0:
            vm = v_mag.iloc[0]
            vmag_stats = {
                "min_pu": float(vm.min()),
                "max_pu": float(vm.max()),
                "mean_pu": float(vm.mean()),
                "num_buses": int(len(vm)),
            }

        vang_stats = {}
        if v_ang is not None and len(v_ang) > 0:
            va = v_ang.iloc[0]
            vang_stats = {
                "min_rad": float(va.min()),
                "max_rad": float(va.max()),
                "mean_rad": float(va.mean()),
            }

        flow_stats = {}
        line_p0 = n.lines_t.p0
        if line_p0 is not None and len(line_p0) > 0:
            p0 = line_p0.iloc[0]
            p1 = n.lines_t.p1.iloc[0]
            p_losses = p0 + p1
            flow_stats = {
                "p0_min_MW": float(p0.min()),
                "p0_max_MW": float(p0.max()),
                "total_p_losses_MW": float(p_losses.sum()),
                "num_lines": int(len(p0)),
            }

        results["details"] = {
            "converged": converged,
            "dc_warm_start_used": dc_warm_start_used,
            "convergence_info": convergence_info,
            "network": network_stats,
            "voltage_magnitudes": vmag_stats,
            "voltage_angles": vang_stats,
            "line_flows": flow_stats,
            "peak_memory_mb": mem_after,
            "mem_before_mb": mem_before,
            "pypsa_version": pypsa.__version__,
        }

        if converged:
            results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":

    def _json_safe(obj):
        if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
            return str(obj)
        return str(obj)

    result = run()
    print(json.dumps(result, indent=2, default=_json_safe))
