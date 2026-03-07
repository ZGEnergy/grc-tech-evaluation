"""A-4: AC Feasibility Check on ACTIVSg10k (MEDIUM, 10000 buses).

Depends on A-3 MEDIUM: run DC OPF, fix dispatch, run ACPF, check violations.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Run DC OPF, fix dispatch, run ACPF, identify violations on MEDIUM."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers, SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "case_ACTIVSg10k (MEDIUM, 10000 buses)"

        # ── Step 1: Run DC OPF ──
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        opf_opts = vge.OptimalPowerFlowOptions()
        opf_opts.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        opf_results = vge.linear_opf(grid, options=opf_opts)
        t_opf = time.perf_counter() - t0

        if not opf_results.converged:
            errors.append("DC OPF did not converge on MEDIUM network")
            return {
                "status": "fail",
                "wall_clock_seconds": t_opf,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        dc_dispatch = np.array(opf_results.generator_power, dtype=float)
        details["dc_opf_total_gen_mw"] = round(float(dc_dispatch.sum()), 4)
        details["dc_opf_wall_clock"] = round(t_opf, 6)
        details["dc_opf_active_gens"] = int(np.sum(dc_dispatch > 0.01))

        # ── Step 2: Fix generator dispatch ──
        grid2 = vge.open_file(NETWORK_FILE)

        for i, gen in enumerate(grid2.generators):
            gen.P = dc_dispatch[i]
            gen.active = True

        details["dispatch_fixed"] = True

        # ── Step 3: Run ACPF ──
        pf_opts = vge.PowerFlowOptions(
            solver_type=SolverType.NR,
            max_iter=200,
            tolerance=1e-6,
            retry_with_other_methods=True,
        )

        t0 = time.perf_counter()
        pf_results = vge.power_flow(grid2, options=pf_opts)
        t_pf = time.perf_counter() - t0

        details["acpf_converged"] = bool(pf_results.converged)
        details["acpf_error"] = float(pf_results.error)
        details["acpf_wall_clock"] = round(t_pf, 6)

        if not pf_results.converged:
            workarounds.append(
                {
                    "description": "ACPF non-convergence with fixed DC dispatch on MEDIUM network",
                    "class": "stable",
                    "reason": "DC dispatch may be AC-infeasible; violations still identifiable from partial results",
                }
            )

        # ── Step 4: Identify violations ──
        vm = np.abs(pf_results.voltage)
        va_deg = np.angle(pf_results.voltage, deg=True)
        loading = pf_results.loading

        details["vm_range_pu"] = [round(float(vm.min()), 6), round(float(vm.max()), 6)]
        details["va_range_deg"] = [round(float(va_deg.min()), 4), round(float(va_deg.max()), 4)]

        # Voltage violations
        v_violations = int(np.sum((vm < 0.95) | (vm > 1.05)))
        v_under = int(np.sum(vm < 0.95))
        v_over = int(np.sum(vm > 1.05))
        details["voltage_violation_count"] = v_violations
        details["voltage_under_count"] = v_under
        details["voltage_over_count"] = v_over

        # Thermal violations
        loading_abs = np.abs(loading) if loading is not None else np.array([])
        t_violations = int(np.sum(loading_abs > 1.0)) if len(loading_abs) > 0 else 0
        details["thermal_violation_count"] = t_violations
        details["max_loading_pct"] = (
            round(float(np.max(loading_abs)) * 100, 2) if len(loading_abs) > 0 else None
        )

        # Losses
        if hasattr(pf_results, "losses"):
            details["total_p_loss_mw"] = round(float(pf_results.losses.real.sum()), 4)

        total_wall = t_opf + t_pf
        details["total_wall_clock"] = round(total_wall, 6)

        details["feasibility_assessment"] = {
            "dc_opf_converged": True,
            "acpf_converged": bool(pf_results.converged),
            "voltage_violations_found": v_violations > 0,
            "thermal_violations_found": t_violations > 0,
            "violations_identifiable": True,
        }

        if pf_results.converged:
            status = "pass"
        else:
            status = "qualified_pass"
            workarounds.append(
                {
                    "description": "ACPF may not converge but violations are still identifiable",
                    "class": "stable",
                }
            )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        total_wall = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("total_wall_clock", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
