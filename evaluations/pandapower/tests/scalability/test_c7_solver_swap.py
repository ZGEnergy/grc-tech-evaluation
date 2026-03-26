"""
Test C-7: Repeat C-3 with each available open-source solver (solver swap)

Dimension: scalability
Network: MEDIUM (case_ACTIVSg10k — 10,000 buses, 12,706 branches, 2,485 generators)
Pass condition: Solver swap requires only parameter change, not reformulation.
Tool: pandapower 3.4.0

pandapower's `rundcopp` uses PYPOWER PIPS exclusively. No solver swap mechanism
exists. This test documents the limitation and records FAIL.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))


def _get_cpu_info() -> tuple[int, int]:
    available = os.cpu_count() or 1
    return 1, available


def run(
    network_file: str = "/workspace/data/networks/case_ACTIVSg10k.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Document solver swap limitation for pandapower DC OPF."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import inspect

        import pandapower as pp

        results["details"]["pandapower_version"] = pp.__version__

        threads_used, threads_available = _get_cpu_info()
        results["details"]["cpu_threads_used"] = threads_used
        results["details"]["cpu_threads_available"] = threads_available

        # 1. Inspect rundcopp signature for solver parameters
        sig = inspect.signature(pp.rundcopp)
        params = list(sig.parameters.keys())
        results["details"]["rundcopp_parameters"] = params

        # Check for solver-related parameters
        solver_params = [p for p in params if "solver" in p.lower()]
        results["details"]["solver_related_params"] = solver_params
        results["details"]["has_solver_swap"] = len(solver_params) > 0

        # 2. Inspect runopp (AC OPF) for comparison
        sig_ac = inspect.signature(pp.runopp)
        params_ac = list(sig_ac.parameters.keys())
        solver_params_ac = [p for p in params_ac if "solver" in p.lower()]
        results["details"]["runopp_parameters"] = params_ac
        results["details"]["runopp_solver_params"] = solver_params_ac

        # 3. Check internal OPF implementation
        # pandapower's rundcopp calls _optimal_powerflow which uses PYPOWER's pips
        from pandapower import run as pp_run

        dcopp_funcs = [f for f in dir(pp_run) if "dcopp" in f.lower() or "optimal" in f.lower()]
        results["details"]["internal_opf_functions"] = dcopp_funcs

        # 4. Document the only available solver
        results["details"]["available_solvers"] = ["PYPOWER PIPS (internal)"]
        results["details"]["solver_swap_mechanism"] = "none"
        results["details"]["failure_reason"] = "unsupported_in_installed_version"

        # 5. Note that alternative approach (scipy linprog as in A-9) requires
        # complete reformulation, not a parameter change
        results["details"]["alternative_approaches"] = {
            "scipy_linprog": {
                "available": True,
                "requires_reformulation": True,
                "description": (
                    "A-9 demonstrated DCOPF via manual PTDF construction + "
                    "scipy.optimize.linprog. This requires complete problem "
                    "reformulation outside pandapower's OPF -- not a parameter change."
                ),
            }
        }

        results["details"]["conclusion"] = (
            "pandapower's rundcopp() has no solver swap mechanism. It exclusively "
            "uses PYPOWER's built-in PIPS (Primal-Dual Interior Point Solver). "
            "There is no parameter to select an alternative solver. The only way "
            "to use a different solver (e.g., HiGHS via scipy) requires complete "
            "reformulation of the OPF problem outside pandapower, as demonstrated "
            "in test A-9. This fails the pass condition which requires solver swap "
            "via parameter change only."
        )

        results["status"] = "fail"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
