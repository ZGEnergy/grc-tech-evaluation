"""
Test A-1: Solve DC Power Flow

Dimension: expressiveness
Network: TINY (case39 — IEEE 39-bus New England)
Pass condition: Converges. Nodal injections, line flows, and voltage angles
    accessible as structured output (DataFrame, dict, or named array — not raw solver vector).
Tool: pypsa 1.1.2
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

        # 2. Solve DC power flow (linear power flow)
        net.lpf()

        # 3. Extract and validate results — must be structured output

        # Bus-level: voltage angles (p.u. radians) and power injections
        bus_angles = net.buses_t.v_ang  # DataFrame: snapshots x buses
        bus_p = net.buses_t.p  # DataFrame: snapshots x buses (nodal injections)

        # Line flows (DataFrame)
        line_p0 = net.lines_t.p0  # Active power at "from" end
        _line_p1 = net.lines_t.p1  # Active power at "to" end

        # Transformer flows if present
        _trafo_p0 = net.transformers_t.p0
        _trafo_p1 = net.transformers_t.p1

        # 4. Validate outputs are non-empty and structured (DataFrames)
        assert bus_angles.shape[0] > 0, "No snapshot results for voltage angles"
        assert bus_angles.shape[1] == len(net.buses), "Angle count mismatch with bus count"
        assert line_p0.shape[1] == len(net.lines), "Line flow count mismatch"

        # Check that angles are not all zero (that would indicate no solve happened)
        # The slack bus should be zero, but others should have non-zero angles
        angles_series = bus_angles.iloc[0]
        non_slack_angles = angles_series[angles_series != 0.0]
        assert len(non_slack_angles) > 0, "All voltage angles are zero — solve may not have run"

        # Check line flows are non-trivial
        max_flow = line_p0.iloc[0].abs().max()
        assert max_flow > 0, "All line flows are zero"

        # 5. Record details
        results["status"] = "pass"
        results["details"] = {
            "bus_count": len(net.buses),
            "line_count": len(net.lines),
            "transformer_count": len(net.transformers),
            "generator_count": len(net.generators),
            "output_format": "pandas.DataFrame",
            "bus_angles_shape": list(bus_angles.shape),
            "bus_p_shape": list(bus_p.shape),
            "line_p0_shape": list(line_p0.shape),
            "angle_range_rad": [float(angles_series.min()), float(angles_series.max())],
            "max_line_flow_mw": float(max_flow),
            "sample_angles": {str(k): float(v) for k, v in angles_series.head(5).items()},
            "sample_line_flows": {str(k): float(v) for k, v in line_p0.iloc[0].head(5).items()},
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
