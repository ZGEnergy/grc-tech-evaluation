"""
Test A-2: Solve AC power flow (Newton-Raphson) on TINY.

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Converges. Convergence residual below tolerance. NR iterations reported.
    Voltage magnitudes differ from flat-start on >95% of buses. Bus voltages, angles,
    P/Q flows, losses accessible.
Tool: gridcal (VeraGridEngine) 5.6.28

Note: Solver config specifies Ipopt, but GridCal has NO Ipopt integration for ACPF.
GridCal uses its own Newton-Raphson solver (SolverType.NR). This is documented as a
finding — GridCal's native NR is the appropriate solver for ACPF.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute A-2 ACPF test and return structured results."""
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
        from VeraGridEngine.enumerations import SolverType

        # 1. Load network
        grid = load_gridcal(network_file)
        n_buses = grid.get_bus_number()
        results["details"]["bus_count"] = n_buses

        # 2. Configure AC power flow with Newton-Raphson (flat start)
        # GridCal does NOT use Ipopt for ACPF — it uses its own NR implementation.
        pf_opts = vge.PowerFlowOptions(
            solver_type=SolverType.NR,
            tolerance=1e-6,
            max_iter=100,
        )

        # 3. Execute ACPF
        pf_results = vge.power_flow(grid, options=pf_opts)

        # 4. Extract results
        converged = bool(pf_results.converged)
        results["details"]["converged"] = converged
        results["details"]["solver"] = "NR (native, not Ipopt)"

        # Iteration count and convergence residual
        iterations = int(pf_results.iterations) if hasattr(pf_results, "iterations") else None
        error = float(pf_results.error) if hasattr(pf_results, "error") else None
        results["details"]["nr_iterations"] = iterations
        results["details"]["convergence_residual"] = error

        if not converged:
            results["errors"].append(
                f"ACPF did not converge (iterations={iterations}, residual={error})"
            )
            # Attempt DC warm start fallback per convergence protocol
            results["details"]["fallback_attempted"] = True

            # Solve DCPF first
            dc_opts = vge.PowerFlowOptions(solver_type=SolverType.Linear)
            dc_results = vge.power_flow(grid, options=dc_opts)

            if dc_results.converged:
                # Use DC solution angles as initialization
                pf_opts_warm = vge.PowerFlowOptions(
                    solver_type=SolverType.NR,
                    tolerance=1e-6,
                    max_iter=200,
                    use_stored_guess=True,
                )
                # Set bus voltage angles from DCPF
                for i, bus in enumerate(grid.get_buses()):
                    bus.Va0 = float(np.angle(dc_results.voltage[i]))

                pf_results = vge.power_flow(grid, options=pf_opts_warm)
                converged = bool(pf_results.converged)
                iterations = (
                    int(pf_results.iterations) if hasattr(pf_results, "iterations") else None
                )
                error = float(pf_results.error) if hasattr(pf_results, "error") else None
                results["details"]["dc_warmstart_converged"] = converged
                results["details"]["dc_warmstart_iterations"] = iterations
                results["details"]["dc_warmstart_residual"] = error

        if not converged:
            results["errors"].append("ACPF did not converge even with DC warm start")
            return results

        # Voltage magnitudes and angles
        voltage = pf_results.voltage
        magnitudes = np.abs(voltage)
        angles_deg = np.degrees(np.angle(voltage))

        bus_names = [b.name for b in grid.get_buses()]

        # Check convergence quality: >95% of buses differ from flat start (1.0 pu)
        non_flat_count = np.sum(np.abs(magnitudes - 1.0) > 1e-6)
        pct_non_flat = float(non_flat_count) / n_buses * 100.0
        results["details"]["pct_buses_differ_from_flat"] = pct_non_flat
        results["details"]["non_flat_bus_count"] = int(non_flat_count)

        # Voltage magnitudes
        results["details"]["voltage_magnitudes_pu"] = {
            bus_names[i]: float(magnitudes[i]) for i in range(n_buses)
        }
        results["details"]["voltage_angles_deg"] = {
            bus_names[i]: float(angles_deg[i]) for i in range(n_buses)
        }

        # Branch flows (P and Q)
        sf = pf_results.Sf
        losses = pf_results.losses
        branch_names = [b.name for b in grid.get_branches()]
        n_branches = len(sf)

        results["details"]["branch_p_flows_mw"] = {
            branch_names[i]: float(np.real(sf[i])) for i in range(n_branches)
        }
        results["details"]["branch_q_flows_mvar"] = {
            branch_names[i]: float(np.imag(sf[i])) for i in range(n_branches)
        }
        results["details"]["branch_losses_mw"] = {
            branch_names[i]: float(np.real(losses[i])) for i in range(n_branches)
        }

        # Total losses
        total_losses_mw = float(np.sum(np.real(losses)))
        results["details"]["total_losses_mw"] = total_losses_mw

        # DataFrame export test
        try:
            bus_df = pf_results.get_bus_df()
            results["details"]["bus_df_columns"] = list(bus_df.columns)
        except Exception as e:
            results["details"]["bus_df_export"] = f"Failed: {e}"

        try:
            branch_df = pf_results.get_branch_df()
            results["details"]["branch_df_columns"] = list(branch_df.columns)
        except Exception as e:
            results["details"]["branch_df_export"] = f"Failed: {e}"

        # Summary stats
        results["details"]["vm_min"] = float(np.min(magnitudes))
        results["details"]["vm_max"] = float(np.max(magnitudes))
        results["details"]["vm_mean"] = float(np.mean(magnitudes))
        results["details"]["max_angle_deg"] = float(np.max(np.abs(angles_deg)))

        # 5. Determine convergence evidence quality (v11 hierarchy)
        # Tier 1: residual_reported — the solver exposes final NR mismatch
        # Tier 2: iteration_count_reported
        # Tier 3: binary_convergence_api
        # Tier 4: proxy_voltage
        if error is not None and iterations is not None and iterations > 0:
            convergence_evidence_quality = "residual_reported"
        elif iterations is not None and iterations > 0:
            convergence_evidence_quality = "iteration_count_reported"
        elif converged:
            convergence_evidence_quality = "binary_convergence_api"
        else:
            convergence_evidence_quality = "proxy_voltage"

        results["details"]["convergence_evidence_quality"] = convergence_evidence_quality

        # 6. Check pass condition
        pass_checks = {
            "converged": converged,
            "iterations_reported": iterations is not None and iterations > 0,
            "residual_below_tol": error is not None and error < 1e-4,
            "voltage_profile_nontrivial": pct_non_flat > 95.0,
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
