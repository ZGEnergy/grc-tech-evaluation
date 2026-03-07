"""A-11: Distributed Slack OPF on IEEE 39-bus (TINY)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Check for distributed slack OPF and compare LMPs with single-slack."""
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

        # ── Check 1: Search for distributed slack options in OPF ──
        opts = vge.OptimalPowerFlowOptions()
        slack_attrs = {}
        for attr in dir(opts):
            if any(
                kw in attr.lower()
                for kw in [
                    "slack",
                    "distribut",
                    "reference",
                    "participation",
                    "balance",
                ]
            ):
                try:
                    slack_attrs[attr] = str(getattr(opts, attr))
                except Exception:
                    slack_attrs[attr] = "<unreadable>"
        details["opf_slack_options"] = slack_attrs

        # ── Check 2: Search for distributed slack in PowerFlowOptions ──
        pf_opts = vge.PowerFlowOptions()
        pf_slack_attrs = {}
        for attr in dir(pf_opts):
            if any(
                kw in attr.lower()
                for kw in [
                    "slack",
                    "distribut",
                    "reference",
                    "participation",
                    "balance",
                ]
            ):
                try:
                    pf_slack_attrs[attr] = str(getattr(pf_opts, attr))
                except Exception:
                    pf_slack_attrs[attr] = "<unreadable>"
        details["pf_slack_options"] = pf_slack_attrs

        # ── Check 3: Check generator participation factor attributes ──
        gen_slack_attrs = {}
        gen = grid.generators[0]
        for attr in dir(gen):
            if any(
                kw in attr.lower()
                for kw in [
                    "slack",
                    "particip",
                    "distribut",
                    "factor",
                    "share",
                ]
            ):
                try:
                    gen_slack_attrs[attr] = str(getattr(gen, attr))
                except Exception:
                    gen_slack_attrs[attr] = "<unreadable>"
        details["generator_slack_attributes"] = gen_slack_attrs

        # ── Check 4: Check bus slack-related attributes ──
        bus_slack_attrs = {}
        bus = grid.buses[0]
        for attr in dir(bus):
            if any(
                kw in attr.lower()
                for kw in [
                    "slack",
                    "type",
                    "reference",
                    "distribut",
                ]
            ):
                try:
                    bus_slack_attrs[attr] = str(getattr(bus, attr))
                except Exception:
                    bus_slack_attrs[attr] = "<unreadable>"
        details["bus_slack_attributes"] = bus_slack_attrs

        # ── Check 5: Search for distributed slack in enumerations ──
        try:
            from VeraGridEngine import enumerations as enums

            slack_enums = {}
            for attr in dir(enums):
                if any(kw in attr.lower() for kw in ["slack", "distribut", "balance"]):
                    slack_enums[attr] = str(getattr(enums, attr))
            details["slack_enumerations"] = slack_enums
        except Exception:
            pass

        # ── Step 1: Single-slack DC OPF (baseline from A-3) ──
        grid_ss = vge.open_file(NETWORK_FILE)
        opts_ss = vge.OptimalPowerFlowOptions()
        opts_ss.mip_solver = MIPSolvers.HIGHS

        t0 = time.perf_counter()
        res_ss = vge.linear_opf(grid_ss, options=opts_ss)
        t_ss = time.perf_counter() - t0

        details["single_slack_dcopf"] = {
            "converged": bool(res_ss.converged),
            "wall_clock_seconds": round(t_ss, 6),
            "generator_power": [round(float(x), 4) for x in res_ss.generator_power],
            "total_gen_mw": round(float(res_ss.generator_power.sum()), 4),
            "shadow_prices": [round(float(x), 6) for x in res_ss.bus_shadow_prices],
        }

        # ── Step 2: Try distributed slack OPF ──
        # Check if there's a distribute_slack or similar option
        distributed_attempted = False

        # Try OPF option
        if hasattr(opts, "distribute_slack"):
            grid_ds = vge.open_file(NETWORK_FILE)
            opts_ds = vge.OptimalPowerFlowOptions()
            opts_ds.mip_solver = MIPSolvers.HIGHS
            opts_ds.distribute_slack = True
            distributed_attempted = True

            try:
                t0 = time.perf_counter()
                res_ds = vge.linear_opf(grid_ds, options=opts_ds)
                t_ds = time.perf_counter() - t0

                details["distributed_slack_dcopf"] = {
                    "converged": bool(res_ds.converged),
                    "wall_clock_seconds": round(t_ds, 6),
                    "generator_power": [round(float(x), 4) for x in res_ds.generator_power],
                    "shadow_prices": [round(float(x), 6) for x in res_ds.bus_shadow_prices],
                }

                # Compare LMPs
                lmp_ss = np.array(res_ss.bus_shadow_prices)
                lmp_ds = np.array(res_ds.bus_shadow_prices)
                lmp_diff = float(np.max(np.abs(lmp_ds - lmp_ss)))
                details["lmp_comparison"] = {
                    "max_diff": round(lmp_diff, 6),
                    "lmps_differ": lmp_diff > 1e-6,
                }
            except Exception as e:
                details["distributed_slack_error"] = str(e)

        # Try PowerFlow distributed slack (for ACPF)
        if hasattr(pf_opts, "distribute_slack") or "distributed_slack" in str(pf_slack_attrs):
            details["pf_distributed_slack_available"] = True

            # Try ACPF with distributed slack
            try:
                from VeraGridEngine.enumerations import SolverType

                grid_pf = vge.open_file(NETWORK_FILE)
                pf_opts_ds = vge.PowerFlowOptions(
                    solver_type=SolverType.NR,
                    max_iter=100,
                    tolerance=1e-6,
                )
                if hasattr(pf_opts_ds, "distribute_slack"):
                    pf_opts_ds.distribute_slack = True
                    distributed_attempted = True

                t0 = time.perf_counter()
                res_pf_ds = vge.power_flow(grid_pf, options=pf_opts_ds)
                t_pf_ds = time.perf_counter() - t0

                details["distributed_slack_acpf"] = {
                    "converged": bool(res_pf_ds.converged),
                    "wall_clock_seconds": round(t_pf_ds, 6),
                }

                # Compare with single-slack ACPF
                grid_pf_ss = vge.open_file(NETWORK_FILE)
                pf_opts_ss = vge.PowerFlowOptions(
                    solver_type=SolverType.NR,
                    max_iter=100,
                    tolerance=1e-6,
                )
                res_pf_ss = vge.power_flow(grid_pf_ss, options=pf_opts_ss)

                if res_pf_ds.converged and res_pf_ss.converged:
                    vm_ds = np.abs(res_pf_ds.voltage)
                    vm_ss = np.abs(res_pf_ss.voltage)
                    vm_diff = float(np.max(np.abs(vm_ds - vm_ss)))
                    details["pf_distributed_vs_single"] = {
                        "max_vm_diff_pu": round(vm_diff, 8),
                        "voltages_differ": vm_diff > 1e-8,
                    }

            except Exception as e:
                details["distributed_slack_acpf_error"] = str(e)

        if not distributed_attempted:
            details["distributed_slack_note"] = (
                "No distributed slack option found in OptimalPowerFlowOptions or "
                "PowerFlowOptions. GridCal reportedly added distributed slack in v3.5.8 "
                "but no API documentation available. The feature may exist under a "
                "different name or may require specific bus type configuration."
            )

            # Last resort: check if we can set participation factors on generators
            try:
                grid_pf2 = vge.open_file(NETWORK_FILE)
                pf_participation = False
                for gen in grid_pf2.generators:
                    if hasattr(gen, "participation_factor"):
                        pf_participation = True
                        break
                details["generators_have_participation_factor"] = pf_participation
            except Exception:
                pass

        # ── Assessment ──
        ds_opf_works = details.get("distributed_slack_dcopf", {}).get("converged", False)
        ds_pf_works = details.get("distributed_slack_acpf", {}).get("converged", False)
        lmps_differ = details.get("lmp_comparison", {}).get("lmps_differ", False)

        if ds_opf_works and lmps_differ:
            status = "pass"
            details["assessment"] = (
                "Distributed slack OPF converged and produces different LMPs "
                "from single-slack, as physically expected."
            )
        elif ds_opf_works or ds_pf_works:
            status = "qualified_pass"
            details["assessment"] = "Distributed slack available but effect on LMPs unclear"
        else:
            status = "fail"
            errors.append("Distributed slack OPF not available or not functional")
            details["assessment"] = (
                "GridCal does not expose a distributed slack formulation for OPF. "
                "The DC OPF uses a single reference bus. No option found to distribute "
                "slack among generators with participation factors."
            )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"

    return {
        "status": status,
        "wall_clock_seconds": details.get(
            "distributed_slack_dcopf", details.get("single_slack_dcopf", {})
        ).get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
