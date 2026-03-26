"""
Test C-2: ACPF on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses, 12,706 branches, 2,485 generators)
Pass condition: Completes successfully. Convergence verified (max bus power mismatch < 1e-4 p.u.).
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

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower


def _get_cpu_info() -> tuple[int, int]:
    """Return (threads_used, threads_available). pandapower NR is single-threaded."""
    available = os.cpu_count() or 1
    return 1, available


def _verify_convergence(net, base_mva: float) -> dict:
    """Verify ACPF convergence quality beyond the solver's reported status.

    Returns convergence evidence dict with tier classification.
    """
    evidence: dict = {
        "converged_flag": bool(net.converged),
        "convergence_evidence_quality": "binary_convergence_api",
    }

    # Check iteration count from internal _ppc structure
    iterations = None
    if hasattr(net, "_ppc") and net._ppc is not None:
        iterations = net._ppc.get("iterations", None)
        if iterations is not None:
            evidence["iterations"] = int(iterations)
            evidence["convergence_evidence_quality"] = "iteration_count_reported"

    # Check for residual / tolerance info
    # pandapower stores tolerance_mva in options; the converged flag + iteration count
    # is the best we get without deeper internal access
    tolerance_mva = net._options.get("tolerance_mva", None) if hasattr(net, "_options") else None
    if tolerance_mva is not None:
        evidence["tolerance_mva"] = float(tolerance_mva)
        # Convert to per-unit: mismatch_pu = tolerance_mva / baseMVA
        evidence["tolerance_pu"] = float(tolerance_mva / base_mva)

    # Voltage profile check — verify solution differs from flat start
    vm = net.res_bus["vm_pu"]
    non_unity = (vm - 1.0).abs() > 1e-6
    pct_non_unity = float(non_unity.sum()) / len(vm) * 100.0
    evidence["pct_buses_non_unity_vm"] = pct_non_unity
    evidence["vm_min"] = float(vm.min())
    evidence["vm_max"] = float(vm.max())
    evidence["vm_mean"] = float(vm.mean())

    # If we have iterations, that's our primary evidence
    # If not, and voltage profile is non-flat, we use proxy_voltage
    if iterations is None and pct_non_unity > 95:
        evidence["convergence_evidence_quality"] = "proxy_voltage"

    return evidence


def run(
    network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute ACPF on MEDIUM network with Newton-Raphson, verify convergence."""
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

        # Load network
        net = load_pandapower(network_file)

        # Thread reporting
        threads_used, threads_available = _get_cpu_info()
        results["details"]["cpu_threads_used"] = threads_used
        results["details"]["cpu_threads_available"] = threads_available

        # Network stats
        base_mva = float(net.sn_mva)
        results["details"]["base_mva"] = base_mva
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)

        # Check lightsim2grid availability
        ls2g_available = False
        try:
            from lightsim2grid import newtonpf  # noqa: F401

            ls2g_available = True
        except ImportError:
            pass
        results["details"]["lightsim2grid_available"] = ls2g_available

        # =========================================================
        # ATTEMPT 1: Newton-Raphson with DC init (standard pandapower)
        # =========================================================
        tracemalloc.start()

        nr_kwargs: dict = {
            "algorithm": "nr",
            "init": "dc",
            "calculate_voltage_angles": True,
            "tolerance_mva": 1e-8,
            "max_iteration": 100,
        }

        solve_start = time.perf_counter()
        try:
            pp.runpp(net, **nr_kwargs)
        except Exception as e:
            results["details"]["nr_standard_error"] = f"{type(e).__name__}: {e}"

        nr_time = time.perf_counter() - solve_start

        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results["details"]["nr_standard"] = {
            "wall_clock_seconds": nr_time,
            "converged": bool(net.converged),
        }

        if net.converged:
            conv_evidence = _verify_convergence(net, base_mva)
            results["details"]["nr_standard"].update(conv_evidence)
            results["details"]["peak_memory_mb"] = peak / (1024 * 1024)

            # Extract key power flow results
            vm = net.res_bus["vm_pu"]
            va = net.res_bus["va_degree"]
            results["details"]["nr_standard"]["vm_stats"] = {
                "min": float(vm.min()),
                "max": float(vm.max()),
                "mean": float(vm.mean()),
                "std": float(vm.std()),
            }
            results["details"]["nr_standard"]["va_stats"] = {
                "min": float(va.min()),
                "max": float(va.max()),
                "mean": float(va.mean()),
            }

            # Line loading
            line_loading = net.res_line["loading_percent"]
            results["details"]["nr_standard"]["max_line_loading_pct"] = float(line_loading.max())
            results["details"]["nr_standard"]["mean_line_loading_pct"] = float(line_loading.mean())

            # Total generation and losses
            results["details"]["nr_standard"]["total_gen_mw"] = float(
                net.res_gen["p_mw"].sum() + net.res_ext_grid["p_mw"].sum()
            )
            results["details"]["nr_standard"]["total_load_mw"] = float(net.res_load["p_mw"].sum())
            total_loss = float(net.res_line["pl_mw"].sum())
            if len(net.res_trafo) > 0:
                total_loss += float(net.res_trafo["pl_mw"].sum())
            results["details"]["nr_standard"]["total_loss_mw"] = total_loss

            # Record primary timing and convergence
            results["details"]["solve_wall_clock_seconds"] = nr_time
            results["details"]["convergence_evidence_quality"] = conv_evidence[
                "convergence_evidence_quality"
            ]
            if "iterations" in conv_evidence:
                results["details"]["convergence_iterations"] = conv_evidence["iterations"]

        # =========================================================
        # ATTEMPT 2: Newton-Raphson with lightsim2grid (comparison)
        # =========================================================
        if ls2g_available:
            net_ls2g = load_pandapower(network_file)

            ls2g_kwargs = dict(nr_kwargs)
            ls2g_kwargs["lightsim2grid"] = True

            tracemalloc.start()
            ls2g_start = time.perf_counter()
            try:
                pp.runpp(net_ls2g, **ls2g_kwargs)
                ls2g_converged = bool(net_ls2g.converged)
            except Exception as e:
                ls2g_converged = False
                results["details"]["ls2g_error"] = f"{type(e).__name__}: {e}"
            ls2g_time = time.perf_counter() - ls2g_start

            _current_ls2g, peak_ls2g = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            results["details"]["nr_lightsim2grid"] = {
                "wall_clock_seconds": ls2g_time,
                "converged": ls2g_converged,
                "peak_memory_mb": peak_ls2g / (1024 * 1024),
            }

            if ls2g_converged:
                ls2g_evidence = _verify_convergence(net_ls2g, base_mva)
                results["details"]["nr_lightsim2grid"].update(ls2g_evidence)

                # Speedup ratio
                if nr_time > 0:
                    results["details"]["ls2g_speedup_ratio"] = nr_time / ls2g_time

        # =========================================================
        # ATTEMPT 3: Flat start fallback (if DC init failed)
        # =========================================================
        if not net.converged:
            net_flat = load_pandapower(network_file)

            flat_kwargs = dict(nr_kwargs)
            flat_kwargs["init"] = "flat"

            tracemalloc.start()
            flat_start = time.perf_counter()
            try:
                pp.runpp(net_flat, **flat_kwargs)
            except Exception as e:
                results["details"]["flat_start_error"] = f"{type(e).__name__}: {e}"
            flat_time = time.perf_counter() - flat_start

            _current_flat, peak_flat = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            results["details"]["nr_flat_start"] = {
                "wall_clock_seconds": flat_time,
                "converged": bool(net_flat.converged),
                "peak_memory_mb": peak_flat / (1024 * 1024),
            }

            if net_flat.converged:
                flat_evidence = _verify_convergence(net_flat, base_mva)
                results["details"]["nr_flat_start"].update(flat_evidence)
                results["details"]["solve_wall_clock_seconds"] = flat_time
                results["details"]["convergence_evidence_quality"] = flat_evidence[
                    "convergence_evidence_quality"
                ]
                results["details"]["peak_memory_mb"] = peak_flat / (1024 * 1024)
                if "iterations" in flat_evidence:
                    results["details"]["convergence_iterations"] = flat_evidence["iterations"]

        results["details"]["pandapower_version"] = pp.__version__

        # Pass if any attempt converged
        converged_any = (
            results["details"].get("nr_standard", {}).get("converged", False)
            or results["details"].get("nr_lightsim2grid", {}).get("converged", False)
            or results["details"].get("nr_flat_start", {}).get("converged", False)
        )

        if converged_any:
            results["status"] = "pass"
        else:
            results["errors"].append("ACPF did not converge with any initialization method")

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
