"""
Test A-4: Take DC OPF dispatch from A-3, run full ACPF on that dispatch.

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Achievable within the same model context (no export to file and reimport).
    Voltage violations and thermal limit violations identifiable from results.
Tool: gridcal (VeraGridEngine) 5.6.28

Solver config specifies Ipopt, but GridCal has NO Ipopt integration for ACPF.
GridCal uses its own Newton-Raphson solver (SolverType.NR). This is documented as a finding.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal

COST_MAP = {
    "hydro": {"c1": 5.0, "c2": 0.005},
    "nuclear": {"c1": 10.0, "c2": 0.010},
    "coal_large": {"c1": 25.0, "c2": 0.025},
    "gas_CC": {"c1": 40.0, "c2": 0.040},
}

BRANCH_DERATING = 0.70


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute A-4 AC feasibility test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers, SolverType

        # 1. Load network
        grid = load_gridcal(network_file)
        generators = grid.get_generators()
        branches = grid.get_branches()
        buses = grid.get_buses()
        n_buses = grid.get_bus_number()
        n_gens = len(generators)
        results["details"]["bus_count"] = n_buses
        results["details"]["gen_count"] = n_gens
        results["details"]["branch_count"] = len(branches)

        # 2. Apply differentiated costs from Modified Tiny data
        ts_dir = Path(timeseries_dir) if timeseries_dir else None
        if ts_dir and (ts_dir / "gen_temporal_params.csv").exists():
            gen_params = {}
            with open(ts_dir / "gen_temporal_params.csv") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    gen_params[int(row["gen_index"])] = row

            for idx, gen in enumerate(generators):
                if idx in gen_params:
                    tech_key = gen_params[idx]["tech_class_key"]
                    if tech_key in COST_MAP:
                        gen.Cost = COST_MAP[tech_key]["c1"]
                        gen.Cost2 = COST_MAP[tech_key]["c2"]
                        gen.Cost0 = 0.0
        else:
            results["errors"].append("gen_temporal_params.csv not found")

        # 3. Apply 70% branch derating (same as A-3)
        for branch in branches:
            if hasattr(branch, "rate") and branch.rate > 0:
                branch.rate = branch.rate * BRANCH_DERATING

        # 4. Solve DC OPF (same as A-3)
        opf_opts = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
        )
        opf_results = vge.linear_opf(grid, opf_opts)

        if not opf_results.converged:
            results["errors"].append("DC OPF (A-3 prerequisite) did not converge")
            return results

        dispatch = opf_results.generator_power
        results["details"]["dcopf_converged"] = True
        results["details"]["dcopf_dispatch_mw"] = {
            generators[i].name or f"gen_{i}": float(dispatch[i]) for i in range(n_gens)
        }
        results["details"]["dcopf_total_gen_mw"] = float(np.sum(dispatch))

        # 5. Fix generator dispatch to DC OPF values — WITHIN SAME MODEL CONTEXT
        #    No export/reimport. Just set gen.P and run ACPF on the same grid object.
        for i, gen in enumerate(generators):
            gen.P = float(dispatch[i])

        results["details"]["same_model_context"] = True
        results["details"]["solver_note"] = (
            "GridCal has no Ipopt integration. Using native NR solver (SolverType.NR)."
        )

        # 6. Run ACPF with flat start
        pf_opts = vge.PowerFlowOptions(
            solver_type=SolverType.NR,
            tolerance=1e-6,
            max_iter=100,
        )
        pf_results = vge.power_flow(grid, options=pf_opts)

        converged = bool(pf_results.converged)
        iterations = int(pf_results.iterations) if hasattr(pf_results, "iterations") else None
        residual = float(pf_results.error) if hasattr(pf_results, "error") else None
        results["details"]["acpf_converged"] = converged
        results["details"]["acpf_iterations"] = iterations
        results["details"]["acpf_residual"] = residual

        if not converged:
            # DC warm start fallback per convergence protocol
            dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
            dc_results = vge.power_flow(grid, options=dc_opts)
            if dc_results.converged:
                for i, bus in enumerate(buses):
                    bus.Va0 = float(np.angle(dc_results.voltage[i]))
                pf_opts_warm = vge.PowerFlowOptions(
                    solver_type=SolverType.NR,
                    tolerance=1e-6,
                    max_iter=200,
                    use_stored_guess=True,
                )
                pf_results = vge.power_flow(grid, options=pf_opts_warm)
                converged = bool(pf_results.converged)
                results["details"]["dc_warmstart_needed"] = True
                results["details"]["dc_warmstart_converged"] = converged

        if not converged:
            results["errors"].append("ACPF did not converge even with DC warm start")
            return results

        # 7. Extract voltage results
        voltage = pf_results.voltage
        v_mag = np.abs(voltage)
        np.degrees(np.angle(voltage))

        results["details"]["vm_min"] = float(np.min(v_mag))
        results["details"]["vm_max"] = float(np.max(v_mag))

        # 8. Identify voltage violations (outside [0.95, 1.05] pu)
        bus_names = [b.name for b in buses]
        voltage_violations = []
        for i in range(n_buses):
            if v_mag[i] < 0.95 or v_mag[i] > 1.05:
                voltage_violations.append(
                    {
                        "bus": bus_names[i],
                        "vm_pu": float(v_mag[i]),
                        "violation": "under" if v_mag[i] < 0.95 else "over",
                    }
                )
        results["details"]["voltage_violations"] = voltage_violations
        results["details"]["voltage_violation_count"] = len(voltage_violations)

        # 9. Identify thermal violations (loading > 100% of derated rating)
        loading = np.abs(pf_results.loading)
        branch_names = [b.name for b in branches]
        thermal_violations = []
        for i in range(len(loading)):
            if loading[i] > 1.0:
                thermal_violations.append(
                    {
                        "branch": branch_names[i] if i < len(branch_names) else f"branch_{i}",
                        "loading_pct": float(loading[i] * 100),
                    }
                )
        results["details"]["thermal_violations"] = thermal_violations
        results["details"]["thermal_violation_count"] = len(thermal_violations)

        # 10. Reactive power information
        losses = pf_results.losses
        total_losses_mw = float(np.sum(np.real(losses)))
        results["details"]["total_losses_mw"] = total_losses_mw

        # 11. Check pass conditions
        pass_checks = {
            "dcopf_converged": True,
            "acpf_converged": converged,
            "same_model_context": True,  # no export/reimport needed
            "violations_identifiable": len(voltage_violations) > 0 or len(thermal_violations) > 0,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
