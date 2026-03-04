"""
Test A-2: Solve AC Power Flow (Newton-Raphson)

Dimension: expressiveness
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Converges. Bus voltage magnitudes and angles, line P/Q flows,
    and losses accessible as structured output.
Tool: pypsa 1.1.2
Solver: Ipopt (nonlinear power flow via optimize with AC formulation)

Note: PyPSA does not have a native Newton-Raphson AC power flow solver.
      It uses optimization-based power flow (pypsa.Network.pf()) which calls
      a Newton-Raphson-like iterative method. We follow the convergence protocol:
      flat start first, then DC warm start fallback if needed.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import pypsa
from matpowercaseframes import CaseFrames

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"


def _load_network(case_file: str) -> pypsa.Network:
    """Load a MATPOWER .m file into a PyPSA Network via matpowercaseframes."""
    cf = CaseFrames(str(DATA_DIR / case_file))
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    return net


def run(network_file: str = "data/networks/case39.m") -> dict:
    """Execute the test and return structured results.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    case_file = Path(network_file).name

    start = time.perf_counter()
    try:
        # 1. Load network
        net = _load_network(case_file)

        # 2. Attempt AC power flow with flat start (default)
        # PyPSA's pf() is a Newton-Raphson nonlinear power flow solver
        convergence_info = net.pf()

        # convergence_info is a dict of DataFrames per sub-network
        # Check convergence
        converged = True
        _iterations = 0
        dc_warm_start_needed = False

        for sn_name, info_df in convergence_info.items():
            if hasattr(info_df, "converged"):
                if not info_df["converged"].all():
                    converged = False
            elif isinstance(info_df, dict):
                if not info_df.get("converged", False):
                    converged = False

        if not converged:
            # Fallback: DC warm start
            dc_warm_start_needed = True
            results["details"]["flat_start_converged"] = False

            # Solve DCPF first
            net_dc = _load_network(case_file)
            net_dc.lpf()

            # Use DC angles as initial conditions for AC solve
            net2 = _load_network(case_file)
            # Set initial voltage angles from DC solution
            for bus in net2.buses.index:
                if bus in net_dc.buses_t.v_ang.columns:
                    net2.buses.at[bus, "v_ang"] = net_dc.buses_t.v_ang.iloc[0][bus]

            convergence_info = net2.pf()
            net = net2

            # Re-check convergence
            converged = True
            for sn_name, info_df in convergence_info.items():
                if hasattr(info_df, "converged"):
                    if not info_df["converged"].all():
                        converged = False
        else:
            results["details"]["flat_start_converged"] = True

        # 3. Extract structured outputs
        # Bus voltage magnitudes and angles
        bus_v_mag = net.buses_t.v_mag_pu  # DataFrame: snapshots x buses
        bus_v_ang = net.buses_t.v_ang  # DataFrame: snapshots x buses

        # Line active and reactive power flows
        line_p0 = net.lines_t.p0  # Active power at "from" end
        line_p1 = net.lines_t.p1  # Active power at "to" end
        line_q0 = net.lines_t.q0  # Reactive power at "from" end
        _line_q1 = net.lines_t.q1  # Reactive power at "to" end

        # Transformer flows
        trafo_p0 = net.transformers_t.p0
        trafo_p1 = net.transformers_t.p1
        _trafo_q0 = net.transformers_t.q0
        _trafo_q1 = net.transformers_t.q1

        # Compute losses per line: P_loss = p0 + p1 (since p1 is negative for receiving end)
        line_losses = line_p0.iloc[0] + line_p1.iloc[0]
        trafo_losses = trafo_p0.iloc[0] + trafo_p1.iloc[0]
        total_losses = line_losses.sum() + trafo_losses.sum()

        # 4. Validate outputs
        assert bus_v_mag.shape[0] > 0, "No snapshot results for voltage magnitudes"
        assert bus_v_mag.shape[1] == len(net.buses), "V_mag count mismatch with bus count"
        assert bus_v_ang.shape[1] == len(net.buses), "V_ang count mismatch with bus count"
        assert line_p0.shape[1] == len(net.lines), "Line P flow count mismatch"
        assert line_q0.shape[1] == len(net.lines), "Line Q flow count mismatch"

        # Voltage magnitudes should be near 1.0 pu for a well-conditioned case
        v_mag_series = bus_v_mag.iloc[0]
        assert v_mag_series.min() > 0.8, f"Min voltage {v_mag_series.min()} too low"
        assert v_mag_series.max() < 1.2, f"Max voltage {v_mag_series.max()} too high"

        # Angles should not all be zero
        v_ang_series = bus_v_ang.iloc[0]
        non_zero_angles = v_ang_series[v_ang_series.abs() > 1e-10]
        assert len(non_zero_angles) > 0, "All voltage angles are zero"

        # 5. Record results
        results["status"] = "pass" if converged else "fail"
        if dc_warm_start_needed and converged:
            results["status"] = "qualified_pass"
            results["workarounds"].append(
                "DC warm start was needed for convergence — flat start failed"
            )

        results["details"].update(
            {
                "converged": converged,
                "dc_warm_start_needed": dc_warm_start_needed,
                "output_format": "pandas.DataFrame",
                "bus_count": len(net.buses),
                "line_count": len(net.lines),
                "transformer_count": len(net.transformers),
                "v_mag_range_pu": [float(v_mag_series.min()), float(v_mag_series.max())],
                "v_ang_range_rad": [float(v_ang_series.min()), float(v_ang_series.max())],
                "total_losses_mw": float(total_losses),
                "max_line_flow_mw": float(line_p0.iloc[0].abs().max()),
                "sample_v_mag": {str(k): float(v) for k, v in v_mag_series.head(5).items()},
                "sample_v_ang": {str(k): float(v) for k, v in v_ang_series.head(5).items()},
                "sample_line_p0": {str(k): float(v) for k, v in line_p0.iloc[0].head(5).items()},
                "sample_line_q0": {str(k): float(v) for k, v in line_q0.iloc[0].head(5).items()},
                "sample_line_losses": {str(k): float(v) for k, v in line_losses.head(5).items()},
            }
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
