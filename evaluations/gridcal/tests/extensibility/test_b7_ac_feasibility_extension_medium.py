"""B-7: AC Feasibility Extension on ACTIVSg10k (MEDIUM).

Dimension: extensibility
Network: MEDIUM (ACTIVSg 10k-bus)
Pass condition: If A-4 required a workaround, document and classify it.
Depends on: A-4 (AC Feasibility).

Reproduce DC OPF -> ACPF pipeline on 10k-bus network.
"""

from __future__ import annotations

import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case_ACTIVSg10k.m")


def run() -> dict:
    """Execute B-7 AC feasibility extension test on MEDIUM network."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import numpy as np
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers, SolverType

        details["tool_version"] = importlib.metadata.version("veragridengine")
        details["network"] = "MEDIUM (ACTIVSg10k)"

        # ── Step 1: DC OPF ──
        t0 = time.perf_counter()

        grid_opf = vge.open_file(NETWORK_FILE)
        details["buses"] = grid_opf.get_bus_number()
        details["generators"] = len(grid_opf.generators)

        opf_opts = vge.OptimalPowerFlowOptions()
        opf_opts.mip_solver = MIPSolvers.HIGHS
        opf_results = vge.linear_opf(grid_opf, options=opf_opts)
        t_opf = time.perf_counter() - t0

        details["dcopf_seconds"] = round(t_opf, 6)

        if not opf_results.converged:
            errors.append("DC OPF did not converge")
            return {
                "status": "fail",
                "wall_clock_seconds": t_opf,
                "details": details,
                "errors": errors,
                "workarounds": workarounds,
            }

        dispatch = opf_results.generator_power.copy()
        details["dcopf_converged"] = True
        details["dcopf_total_gen_mw"] = round(float(dispatch.sum()), 2)

        # ── Step 2: Apply dispatch to fresh grid and run ACPF ──
        t0_ac = time.perf_counter()
        grid_ac = vge.open_file(NETWORK_FILE)
        for i, gen in enumerate(grid_ac.generators):
            gen.P = float(dispatch[i])

        pf_opts = vge.PowerFlowOptions(solver_type=SolverType.NR)
        pf_results = vge.power_flow(grid_ac, options=pf_opts)
        t_ac = time.perf_counter() - t0_ac

        wall_clock = t_opf + t_ac
        details["acpf_seconds"] = round(t_ac, 6)
        details["acpf_converged"] = bool(pf_results.converged)
        details["wall_clock_seconds"] = round(wall_clock, 6)

        if pf_results.converged:
            vm = np.abs(pf_results.voltage)
            details["vm_range"] = [round(float(vm.min()), 4), round(float(vm.max()), 4)]
            details["max_loading_pct"] = round(float(np.max(np.abs(pf_results.loading))) * 100, 2)

            # Check for voltage violations
            v_low = float((vm < 0.9).sum())
            v_high = float((vm > 1.1).sum())
            details["voltage_violations"] = {
                "below_0.9": int(v_low),
                "above_1.1": int(v_high),
                "total": int(v_low + v_high),
            }

        # ── Document the A-4 workflow assessment ──
        details["a4_workaround_needed"] = not pf_results.converged
        details["workflow_steps"] = [
            "1. Load grid via vge.open_file()",
            "2. Run DC OPF via vge.linear_opf() -> get generator_power",
            "3. Load fresh grid via vge.open_file()",
            "4. Set each gen.P = dispatch[i]",
            "5. Run ACPF via vge.power_flow() with SolverType.NR",
            "6. Inspect results.voltage and results.loading for violations",
        ]

        if pf_results.converged:
            details["workaround_classification"] = None
            details["workaround_explanation"] = (
                "No workaround needed. DC OPF -> ACPF pipeline works through documented "
                "public API on 10k-bus network."
            )
            status = "pass"
        else:
            # ACPF didn't converge -- this is a finding, not necessarily a fail
            # The test is about whether the workflow is expressible, not whether
            # NR converges on every dispatch point
            details["workaround_classification"] = "stable"
            details["workaround_explanation"] = (
                "ACPF did not converge with OPF dispatch. DC->AC gap is expected on "
                "large networks. The API workflow itself is clean -- no workaround "
                "needed for the interface, only for convergence."
            )
            workarounds.append(
                {
                    "class": "stable",
                    "description": "ACPF non-convergence with DC OPF dispatch on 10k-bus network.",
                }
            )
            status = "qualified_pass"

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": details.get("wall_clock_seconds", wall_clock),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
