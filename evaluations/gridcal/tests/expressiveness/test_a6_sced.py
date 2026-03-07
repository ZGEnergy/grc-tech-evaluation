"""A-6: SCED (Economic Dispatch) on IEEE 39-bus (TINY).

Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Depends on: A-5 (SCUC) -- which FAILED.
Pass condition: Solves. Dispatch schedule extractable. UC and ED cleanly separable.
Ramp rates demonstrably enforced.

Since A-5 failed (time-series OPF crashes with TapPhaseControl error), this test
documents the dependency gap and attempts a snapshot DC OPF as substitute.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Execute A-6 SCED test."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")

        # ── Document A-5 dependency failure ──
        details["a5_dependency"] = {
            "status": "failed",
            "reason": (
                "A-5 SCUC failed: time-series OPF crashes on case39.m with "
                "'ValueError: 0 is not a valid TapPhaseControl'. No commitment "
                "schedule available to fix for ED."
            ),
            "impact": (
                "Cannot test UC/ED separation because UC (A-5) never produced "
                "a commitment schedule. Testing snapshot DC OPF as substitute."
            ),
        }

        # ── Attempt 1: Snapshot DC OPF (economic dispatch substitute) ──
        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        # Document generator parameters relevant to ED
        gen_info = []
        for i, g in enumerate(grid.generators):
            gen_info.append(
                {
                    "index": i,
                    "name": g.name,
                    "Pmin": round(g.Pmin, 2),
                    "Pmax": round(g.Pmax, 2),
                    "Cost": round(g.Cost, 6),
                    "Cost2": round(g.Cost2, 6),
                    "RampUp": getattr(g, "RampUp", None),
                    "RampDown": getattr(g, "RampDown", None),
                }
            )
        details["generator_info"] = gen_info

        opts = vge.OptimalPowerFlowOptions()
        opts.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        results = vge.linear_opf(grid, options=opts)
        t_snap = time.perf_counter() - t0

        details["snapshot_ed"] = {
            "converged": bool(results.converged),
            "wall_clock_seconds": round(t_snap, 6),
            "generator_dispatch_mw": [round(float(x), 4) for x in results.generator_power],
            "total_generation_mw": round(float(results.generator_power.sum()), 4),
            "shadow_prices": [round(float(x), 6) for x in results.bus_shadow_prices],
        }

        # ── Attempt 2: Two-period ED with ramp constraints ──
        # Try to demonstrate ramp rate enforcement by solving two consecutive
        # snapshots with different loads, then checking if ramp constraints bind.
        grid2 = vge.open_file(NETWORK_FILE)

        # Modify load for period 2 (20% increase)
        for load in grid2.loads:
            load.P = load.P * 1.20
            load.Q = load.Q * 1.20

        # Set tight ramp limits on all generators
        ramp_limit = 50.0  # MW per period
        for gen in grid2.generators:
            gen.RampUp = ramp_limit
            gen.RampDown = ramp_limit

        # Check if consider_ramps option exists
        opts2 = vge.OptimalPowerFlowOptions()
        opts2.mip_solver = MIPSolvers.HIGHS
        has_ramp_option = hasattr(opts2, "consider_ramps")
        details["has_consider_ramps_option"] = has_ramp_option

        if has_ramp_option:
            opts2.consider_ramps = True

        t0 = time.perf_counter()
        results2 = vge.linear_opf(grid2, options=opts2)
        t_ramp = time.perf_counter() - t0

        details["ramp_test"] = {
            "converged": bool(results2.converged),
            "wall_clock_seconds": round(t_ramp, 6),
            "ramp_limit_mw": ramp_limit,
            "generator_dispatch_mw": [round(float(x), 4) for x in results2.generator_power],
        }

        # Compare dispatches
        if results.converged and results2.converged:
            dispatch_diff = np.abs(results2.generator_power - results.generator_power)
            max_ramp = float(np.max(dispatch_diff))
            details["ramp_test"]["dispatch_change_mw"] = [round(float(x), 4) for x in dispatch_diff]
            details["ramp_test"]["max_dispatch_change_mw"] = round(max_ramp, 4)
            details["ramp_test"]["ramp_enforced"] = max_ramp <= ramp_limit + 1e-3
            details["ramp_test"]["note"] = (
                "Ramp constraints in snapshot OPF are NOT inter-temporal -- "
                "each snapshot is solved independently. The consider_ramps "
                "option requires time-series OPF which crashes on case39.m."
            )

        # ── Attempt 3: Time-series OPF for true ED with ramps ──
        try:
            import pandas as pd

            grid3 = vge.open_file(NETWORK_FILE)
            n_hours = 4
            time_idx = pd.date_range("2025-01-01", periods=n_hours, freq="h")
            grid3.time_profile = time_idx

            load_profile = np.array([0.90, 1.00, 1.10, 1.05])
            for ld in grid3.loads:
                ld.P_prof = ld.P * load_profile
                ld.Q_prof = ld.Q * load_profile

            for gen in grid3.generators:
                gen.RampUp = ramp_limit
                gen.RampDown = ramp_limit

            ts_opts = vge.OptimalPowerFlowOptions()
            ts_opts.mip_solver = MIPSolvers.HIGHS
            if has_ramp_option:
                ts_opts.consider_ramps = True

            time_indices = np.arange(n_hours)
            opf_vars, lp_model = vge.run_linear_opf_ts(
                grid3,
                time_indices=time_indices,
                solver_type=MIPSolvers.HIGHS,
                ramp_constraints=True,
            )
            details["ts_ed"] = {
                "converged": True,
                "note": "Time-series OPF succeeded for ED",
            }
        except Exception as e:
            details["ts_ed_error"] = str(e)
            details["ts_ed_note"] = (
                "Time-series OPF failed (expected -- TapPhaseControl bug on case39.m). "
                "Cannot demonstrate inter-temporal ramp enforcement."
            )

        # ── UC/ED Separation Assessment ──
        details["uc_ed_separation"] = {
            "separable": False,
            "reason": (
                "GridCal does not expose UC and ED as separate APIs. The OPF has a "
                "dispatch_mode (Normal vs UnitCommitment) but no way to fix a "
                "commitment schedule and solve ED only. The user cannot pass a "
                "binary commitment vector to the OPF solver."
            ),
            "available_modes": [],
        }

        try:
            from VeraGridEngine.enumerations import OpfDispatchMode

            details["uc_ed_separation"]["available_modes"] = [m.name for m in OpfDispatchMode]
        except ImportError:
            pass

        # ── Determine status ──
        snapshot_ok = details["snapshot_ed"]["converged"]
        wall_clock = details["snapshot_ed"]["wall_clock_seconds"]

        if snapshot_ok:
            # Snapshot ED works but UC/ED not separable, ramps not inter-temporal
            status = "fail"
            details["status_rationale"] = (
                "Snapshot DC OPF converges and dispatch is extractable, but: "
                "(1) A-5 SCUC failed so no commitment schedule exists to fix; "
                "(2) UC and ED are not cleanly separable; "
                "(3) Ramp rates cannot be demonstrated as inter-temporally enforced "
                "because time-series OPF crashes on case39.m."
            )
        else:
            status = "fail"

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"
        wall_clock = 0.0

    return {
        "status": status,
        "wall_clock_seconds": wall_clock,
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
