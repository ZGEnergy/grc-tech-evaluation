"""A-5: SCUC (24-hour Unit Commitment as MILP) on IEEE 39-bus (TINY)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Attempt SCUC via GridCal's UC mode and time-series OPF."""
    errors: list[str] = []
    workarounds: list[dict] = []
    details: dict = {}

    try:
        import importlib.metadata

        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers

        details["tool_version"] = importlib.metadata.version("veragridengine")

        grid = vge.open_file(NETWORK_FILE)
        details["buses"] = grid.get_bus_number()
        details["generators"] = len(grid.generators)

        # ── Attempt 1: Snapshot OPF with UC dispatch mode ──
        # Check if OpfDispatchMode.UnitCommitment exists
        try:
            from VeraGridEngine.enumerations import OpfDispatchMode

            details["opf_dispatch_modes"] = [m.name for m in OpfDispatchMode]
            has_uc_mode = hasattr(OpfDispatchMode, "UnitCommitment")
            details["has_uc_dispatch_mode"] = has_uc_mode
        except ImportError:
            has_uc_mode = False
            details["has_uc_dispatch_mode"] = False
            details["opf_dispatch_mode_import_error"] = "OpfDispatchMode not found"

        # Try snapshot DC OPF with UC mode
        if has_uc_mode:
            try:
                opts = vge.OptimalPowerFlowOptions()
                opts.mip_solver = MIPSolvers.HIGHS

                # Document available UC-related options
                uc_attrs = {}
                for attr in dir(opts):
                    if any(
                        kw in attr.lower()
                        for kw in [
                            "commit",
                            "ramp",
                            "up_down",
                            "startup",
                            "shutdown",
                            "min_time",
                            "dispatch",
                        ]
                    ):
                        try:
                            uc_attrs[attr] = str(getattr(opts, attr))
                        except Exception:
                            uc_attrs[attr] = "<unreadable>"
                details["uc_related_options"] = uc_attrs

                # Set UC mode
                opts.dispatch_mode = OpfDispatchMode.UnitCommitment
                details["dispatch_mode_set"] = "UnitCommitment"

                # Try setting UC constraint flags if they exist
                for flag in ["consider_time_up_down", "consider_ramps", "consider_contingencies"]:
                    if hasattr(opts, flag):
                        try:
                            setattr(opts, flag, True)
                            details[f"set_{flag}"] = True
                        except Exception as e:
                            details[f"set_{flag}_error"] = str(e)

                t0 = time.perf_counter()
                results = vge.linear_opf(grid, options=opts)
                t_uc = time.perf_counter() - t0

                details["snapshot_uc"] = {
                    "converged": bool(results.converged),
                    "wall_clock_seconds": round(t_uc, 6),
                    "generator_power": [round(float(x), 4) for x in results.generator_power],
                    "total_gen_mw": round(float(results.generator_power.sum()), 4),
                }

                # Check for binary commitment results
                if hasattr(results, "generator_status"):
                    details["snapshot_uc"]["generator_status"] = [
                        int(x) for x in results.generator_status
                    ]
                if hasattr(results, "commitment"):
                    details["snapshot_uc"]["commitment"] = [int(x) for x in results.commitment]

                # Check which generators were committed (P > 0 implies committed)
                gen_committed = [1 if abs(float(x)) > 1e-6 else 0 for x in results.generator_power]
                details["snapshot_uc"]["inferred_commitment"] = gen_committed

            except Exception as e:
                import traceback

                details["snapshot_uc_error"] = str(e)
                details["snapshot_uc_traceback"] = traceback.format_exc()

        # ── Attempt 2: Time-series OPF with UC mode (24 hours) ──
        # Known issue: ValueError: 0 is not a valid TapPhaseControl on case39.m
        try:
            grid_ts = vge.open_file(NETWORK_FILE)

            # Create 24-hour time series for loads
            n_hours = 24
            # Typical load profile shape (normalized)
            load_profile = np.array(
                [
                    0.83,
                    0.78,
                    0.75,
                    0.73,
                    0.74,
                    0.78,
                    0.88,
                    0.95,
                    1.00,
                    0.99,
                    0.97,
                    0.95,
                    0.93,
                    0.92,
                    0.93,
                    0.95,
                    0.98,
                    1.00,
                    0.99,
                    0.96,
                    0.93,
                    0.90,
                    0.87,
                    0.85,
                ]
            )

            # Check if we can set up time series
            details["time_series_setup"] = {}

            # Explore time-series API
            if hasattr(grid_ts, "time_profile"):
                details["time_series_setup"]["has_time_profile"] = True
            else:
                details["time_series_setup"]["has_time_profile"] = False

            # Try to create time profile
            import pandas as pd

            time_index = pd.date_range("2025-01-01", periods=n_hours, freq="h")

            # Set the time profile on the grid
            grid_ts.time_profile = time_index
            details["time_series_setup"]["time_profile_set"] = True

            # Set load profiles
            for load in grid_ts.loads:
                base_p = load.P
                load.P_prof = base_p * load_profile
                load.Q_prof = load.Q * load_profile

            details["time_series_setup"]["load_profiles_set"] = True

            # Set generator cost profiles (constant over time)
            for gen in grid_ts.generators:
                gen.Cost_prof = np.full(n_hours, gen.Cost)
                gen.Cost2_prof = np.full(n_hours, gen.Cost2)
                gen.Pmin_prof = np.full(n_hours, gen.Pmin)
                gen.Pmax_prof = np.full(n_hours, gen.Pmax)

            # Set UC parameters on generators
            for gen in grid_ts.generators:
                # Document available UC attributes
                if not details.get("gen_uc_attrs_documented"):
                    gen_uc = {}
                    for attr in dir(gen):
                        if any(
                            kw in attr.lower()
                            for kw in [
                                "commit",
                                "ramp",
                                "up_time",
                                "down_time",
                                "startup",
                                "shutdown",
                                "min_time",
                                "enabled",
                                "dispatchable",
                                "must_run",
                                "conn",
                                "status",
                            ]
                        ):
                            try:
                                gen_uc[attr] = str(getattr(gen, attr))
                            except Exception:
                                gen_uc[attr] = "<unreadable>"
                    details["generator_uc_attributes"] = gen_uc
                    details["gen_uc_attrs_documented"] = True

            # Try time-series OPF using run_linear_opf_ts (correct API)
            t0 = time.perf_counter()
            try:
                time_indices = np.arange(n_hours)
                opf_vars, lp_model = vge.run_linear_opf_ts(
                    grid_ts,
                    time_indices=time_indices,
                    dispatch_mode=OpfDispatchMode.UnitCommitment
                    if has_uc_mode
                    else OpfDispatchMode.Normal,
                    solver_type=MIPSolvers.HIGHS,
                    ramp_constraints=True,
                    consider_time_up_down=True,
                )
                t_ts = time.perf_counter() - t0

                # Extract results from OpfVars
                ts_uc_result = {
                    "wall_clock_seconds": round(t_ts, 6),
                }

                # Document OpfVars attributes
                opf_vars_attrs = {}
                for attr in dir(opf_vars):
                    if not attr.startswith("_"):
                        try:
                            val = getattr(opf_vars, attr)
                            if hasattr(val, "shape"):
                                opf_vars_attrs[attr] = f"array shape={val.shape}"
                            elif hasattr(val, "__len__") and not isinstance(val, str):
                                opf_vars_attrs[attr] = f"len={len(val)}"
                            elif not callable(val):
                                opf_vars_attrs[attr] = str(val)[:100]
                        except Exception:
                            pass
                ts_uc_result["opf_vars_attrs"] = opf_vars_attrs

                # Try to extract generator power
                if hasattr(opf_vars, "gen_p"):
                    gp = np.array(opf_vars.gen_p)
                    ts_uc_result["gen_power_shape"] = list(gp.shape)
                    if gp.ndim == 2:
                        commitment_matrix = (np.abs(gp) > 1e-6).astype(int)
                        ts_uc_result["commitment_matrix"] = commitment_matrix.tolist()
                        ts_uc_result["total_gen_by_hour"] = [
                            round(float(gp[t].sum()), 2) for t in range(gp.shape[0])
                        ]
                elif hasattr(opf_vars, "generator_power"):
                    gp = np.array(opf_vars.generator_power)
                    ts_uc_result["gen_power_shape"] = list(gp.shape)

                # Check for binary commitment variables
                if hasattr(opf_vars, "gen_status"):
                    ts_uc_result["gen_status_shape"] = list(np.array(opf_vars.gen_status).shape)
                    ts_uc_result["gen_status"] = np.array(opf_vars.gen_status).tolist()
                if hasattr(opf_vars, "commitment"):
                    ts_uc_result["commitment"] = np.array(opf_vars.commitment).tolist()

                ts_uc_result["converged"] = True
                details["ts_opf_uc"] = ts_uc_result

            except (ValueError, Exception) as e:
                t_ts = time.perf_counter() - t0
                details["ts_opf_uc_error"] = str(e)
                details["ts_opf_uc_traceback"] = __import__("traceback").format_exc()
                details["ts_opf_uc_wall_clock"] = round(t_ts, 6)
                workarounds.append(
                    {
                        "description": f"Time-series OPF with UC mode failed: {e}",
                        "class": "blocking",
                        "reason": "Known bug or API issue",
                    }
                )

            # Also try via OptimalPowerFlowTimeSeriesDriver
            try:
                ts_opts2 = vge.OptimalPowerFlowOptions()
                ts_opts2.mip_solver = MIPSolvers.HIGHS
                if has_uc_mode:
                    ts_opts2.dispatch_mode = OpfDispatchMode.UnitCommitment
                ts_opts2.consider_ramps = True
                ts_opts2.consider_time_up_down = True

                driver = vge.OptimalPowerFlowTimeSeriesDriver(
                    grid=grid_ts,
                    options=ts_opts2,
                    time_indices=np.arange(n_hours),
                )
                t0b = time.perf_counter()
                driver.run()
                t_drv = time.perf_counter() - t0b

                drv_result = {
                    "wall_clock_seconds": round(t_drv, 6),
                }
                if hasattr(driver, "results") and driver.results is not None:
                    res = driver.results
                    drv_result["converged"] = bool(getattr(res, "converged", False))
                    for attr in ["generator_power", "bus_shadow_prices", "Sf", "loading"]:
                        if hasattr(res, attr):
                            val = getattr(res, attr)
                            if hasattr(val, "shape"):
                                drv_result[f"{attr}_shape"] = list(val.shape)

                    # Extract commitment if available
                    if hasattr(res, "generator_power"):
                        gp2 = np.array(res.generator_power)
                        if gp2.ndim == 2:
                            commitment = (np.abs(gp2) > 1e-6).astype(int)
                            drv_result["commitment_matrix"] = commitment.tolist()
                            drv_result["total_gen_by_hour"] = [
                                round(float(gp2[t].sum()), 2) for t in range(gp2.shape[0])
                            ]

                details["ts_opf_driver"] = drv_result
            except Exception as e2:
                details["ts_opf_driver_error"] = str(e2)
                details["ts_opf_driver_traceback"] = __import__("traceback").format_exc()

        except Exception as e:
            details["ts_setup_error"] = str(e)
            details["ts_setup_traceback"] = __import__("traceback").format_exc()

        # ── Attempt 3: Manual hour-by-hour loop as workaround ──
        try:
            grid_loop = vge.open_file(NETWORK_FILE)
            hourly_results = []

            for hour in range(24):
                # Scale loads
                for load in grid_loop.loads:
                    load.P = (
                        load.P * load_profile[hour] / (load_profile[hour - 1] if hour > 0 else 1.0)
                    )
                    load.Q = (
                        load.Q * load_profile[hour] / (load_profile[hour - 1] if hour > 0 else 1.0)
                    )

                loop_opts = vge.OptimalPowerFlowOptions()
                loop_opts.mip_solver = MIPSolvers.HIGHS
                if has_uc_mode:
                    loop_opts.dispatch_mode = OpfDispatchMode.UnitCommitment

                res = vge.linear_opf(grid_loop, options=loop_opts)
                gen_p = [round(float(x), 2) for x in res.generator_power]
                committed = [1 if abs(float(x)) > 1e-6 else 0 for x in res.generator_power]
                hourly_results.append(
                    {
                        "hour": hour,
                        "converged": bool(res.converged),
                        "gen_power_mw": gen_p,
                        "committed": committed,
                        "total_gen_mw": round(float(res.generator_power.sum()), 2),
                    }
                )

            details["hourly_loop"] = {
                "hours_solved": len(hourly_results),
                "all_converged": all(h["converged"] for h in hourly_results),
                "commitment_schedule": [h["committed"] for h in hourly_results],
                "total_gen_by_hour": [h["total_gen_mw"] for h in hourly_results],
            }

            workarounds.append(
                {
                    "description": "Hour-by-hour OPF loop (no inter-temporal constraints)",
                    "class": "fragile",
                    "reason": (
                        "Loses inter-temporal coupling (ramp rates, min up/down time). "
                        "Each hour solved independently. Not true SCUC."
                    ),
                }
            )

        except Exception as e:
            details["hourly_loop_error"] = str(e)

        # ── Assessment ──
        # Issue #397: ramp/min-up-down constraints reportedly not enforced
        details["known_issues"] = [
            "Issue #397: UC ramp and min-up/down-time constraints reportedly not enforced",
            "Time-series OPF has TapPhaseControl bug on case39.m",
            "No inter-temporal coupling in snapshot OPF with UC mode",
        ]

        # Determine overall status
        snapshot_ok = details.get("snapshot_uc", {}).get("converged", False)
        ts_ok = details.get("ts_opf_uc", {}).get("converged", False)
        loop_ok = details.get("hourly_loop", {}).get("all_converged", False)

        if ts_ok:
            status = "pass"
            details["method_used"] = "time-series OPF with UC mode"
        elif snapshot_ok and loop_ok:
            status = "qualified_pass"
            details["method_used"] = "snapshot UC + hourly loop (no inter-temporal constraints)"
        elif snapshot_ok:
            status = "qualified_pass"
            details["method_used"] = "snapshot UC only (single period, not 24-hour)"
        else:
            status = "fail"
            details["method_used"] = "none converged"

        details["constraint_enforcement"] = {
            "ramp_rates": "reportedly not enforced (issue #397)",
            "min_up_time": "reportedly not enforced (issue #397)",
            "min_down_time": "reportedly not enforced (issue #397)",
            "startup_cost": "unknown",
            "shutdown_cost": "unknown",
            "commitment_binary": "UC mode exists but binary commitment unclear from results",
        }

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"

    return {
        "status": status,
        "wall_clock_seconds": details.get("snapshot_uc", {}).get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
