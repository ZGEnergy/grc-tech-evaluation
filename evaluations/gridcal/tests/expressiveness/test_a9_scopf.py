"""A-9: SCOPF (Preventive Security-Constrained OPF) on IEEE 39-bus (TINY)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"
NETWORK_FILE = str(DATA_DIR / "case39.m")


def run() -> dict:
    """Attempt SCOPF — expected to fail (not implemented, issue #364)."""
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
        branches = list(grid.lines) + list(grid.transformers2w)
        details["branches"] = len(branches)
        details["generators"] = len(grid.generators)

        # ── Check 1: Does OPF options have contingency-related flags? ──
        opts = vge.OptimalPowerFlowOptions()
        contingency_attrs = {}
        for attr in dir(opts):
            if any(
                kw in attr.lower()
                for kw in [
                    "contingenc",
                    "security",
                    "n_1",
                    "n1",
                    "scopf",
                    "prevent",
                    "corrective",
                    "post_contingency",
                ]
            ):
                try:
                    contingency_attrs[attr] = str(getattr(opts, attr))
                except Exception:
                    contingency_attrs[attr] = "<unreadable>"
        details["opf_contingency_options"] = contingency_attrs
        details["has_contingency_options"] = len(contingency_attrs) > 0

        # Check consider_contingencies flag
        if hasattr(opts, "consider_contingencies"):
            details["consider_contingencies_default"] = str(opts.consider_contingencies)
            try:
                opts.consider_contingencies = True
                details["consider_contingencies_set"] = True
            except Exception as e:
                details["consider_contingencies_set_error"] = str(e)

        # ── Check 2: Does GridCal have a contingency analysis module? ──
        contingency_modules = {}
        for mod_name in [
            "VeraGridEngine.Simulations.ContingencyAnalysis",
            "VeraGridEngine.Simulations.SCOPF",
            "VeraGridEngine.Simulations.SecurityConstrainedOPF",
        ]:
            try:
                __import__(mod_name)
                contingency_modules[mod_name] = "found"
            except ImportError:
                contingency_modules[mod_name] = "not found"
        details["contingency_modules"] = contingency_modules

        # ── Check 3: Search for SCOPF-related classes ──
        scopf_classes = []
        try:
            import VeraGridEngine.Simulations as sims

            for attr in dir(sims):
                if any(kw in attr.lower() for kw in ["scopf", "security", "contingenc"]):
                    scopf_classes.append(attr)
        except Exception:
            pass
        details["scopf_related_classes"] = scopf_classes

        # ── Check 4: Try contingency analysis (N-1 post-hoc, not SCOPF) ──
        try:
            from VeraGridEngine.Simulations.ContingencyAnalysis import (
                ContingencyAnalysisOptions,  # noqa: F401
            )

            details["contingency_analysis_available"] = True

            # This is post-hoc N-1, not preventive SCOPF
            details["contingency_analysis_note"] = (
                "ContingencyAnalysis exists but performs post-hoc N-1 analysis, "
                "not preventive SCOPF. It runs power flow under each contingency "
                "but does NOT re-optimize dispatch to respect all N-1 limits simultaneously."
            )
        except ImportError:
            details["contingency_analysis_available"] = False

        # ── Check 5: Try running OPF with consider_contingencies=True ──
        if hasattr(opts, "consider_contingencies"):
            try:
                opts.consider_contingencies = True
                opts.mip_solver = MIPSolvers.HIGHS

                # Define contingencies (N-1 on all branches)
                # Check how GridCal defines contingencies
                contingency_setup = {}
                if hasattr(grid, "contingencies"):
                    contingency_setup["has_contingencies_list"] = True
                    contingency_setup["contingencies_count"] = len(grid.contingencies)
                else:
                    contingency_setup["has_contingencies_list"] = False

                if hasattr(grid, "contingency_groups"):
                    contingency_setup["has_contingency_groups"] = True
                else:
                    contingency_setup["has_contingency_groups"] = False

                details["contingency_setup"] = contingency_setup

                # Try to create contingencies for all branches
                try:
                    from VeraGridEngine.Devices import Contingency, ContingencyGroup

                    group = ContingencyGroup(name="N-1_all_branches")
                    grid.add_contingency_group(group)

                    for i, branch in enumerate(branches):
                        c = Contingency(
                            device=branch,
                            name=f"N-1_{branch.name}",
                            group=group,
                        )
                        grid.add_contingency(c)

                    details["contingencies_created"] = len(branches)

                    t0 = time.perf_counter()
                    results = vge.linear_opf(grid, options=opts)
                    t_scopf = time.perf_counter() - t0

                    details["scopf_attempt"] = {
                        "converged": bool(results.converged),
                        "wall_clock_seconds": round(t_scopf, 6),
                        "generator_power": [round(float(x), 4) for x in results.generator_power],
                    }

                    # Compare with unconstrained DC OPF
                    grid2 = vge.open_file(NETWORK_FILE)
                    opts2 = vge.OptimalPowerFlowOptions()
                    opts2.mip_solver = MIPSolvers.HIGHS
                    results2 = vge.linear_opf(grid2, options=opts2)

                    details["base_dcopf"] = {
                        "generator_power": [round(float(x), 4) for x in results2.generator_power],
                    }

                    # Check if dispatch differs (would indicate SCOPF is actually working)
                    gp_scopf = np.array(results.generator_power)
                    gp_base = np.array(results2.generator_power)
                    dispatch_differs = not np.allclose(gp_scopf, gp_base, atol=0.1)
                    details["dispatch_differs_from_base"] = dispatch_differs

                    if dispatch_differs:
                        details["scopf_assessment"] = (
                            "Dispatch differs from base DC OPF, suggesting contingency "
                            "constraints may be active. However, verification that ALL N-1 "
                            "limits are simultaneously respected is needed."
                        )
                    else:
                        details["scopf_assessment"] = (
                            "Dispatch identical to base DC OPF. consider_contingencies flag "
                            "may not actually enforce N-1 constraints in the optimization."
                        )

                except ImportError as e:
                    details["contingency_creation_error"] = f"Import error: {e}"
                except Exception as e:
                    details["contingency_creation_error"] = str(e)
                    details["contingency_creation_traceback"] = __import__("traceback").format_exc()

            except Exception as e:
                details["scopf_attempt_error"] = str(e)
                details["scopf_attempt_traceback"] = __import__("traceback").format_exc()

        # ── Final assessment ──
        details["known_issues"] = [
            "Issue #364: SCOPF not implemented",
            "ContingencyAnalysis is post-hoc N-1, not preventive SCOPF",
            "consider_contingencies flag in OPF may not enforce N-1 limits",
        ]

        # SCOPF is not implemented
        scopf_works = details.get("scopf_attempt", {}).get("converged", False) and details.get(
            "dispatch_differs_from_base", False
        )
        if scopf_works:
            status = "qualified_pass"
            details["assessment"] = "SCOPF-like behavior observed but unverified"
        else:
            status = "fail"
            errors.append("SCOPF not implemented in GridCal (issue #364)")
            details["assessment"] = (
                "GridCal does not implement preventive SCOPF. "
                "ContingencyAnalysis provides post-hoc N-1 screening but not "
                "simultaneous optimization respecting all N-1 constraints."
            )

    except Exception as e:
        import traceback

        errors.append(f"Exception: {type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        status = "fail"

    return {
        "status": status,
        "wall_clock_seconds": details.get("scopf_attempt", {}).get("wall_clock_seconds", 0.0),
        "details": details,
        "errors": errors,
        "workarounds": workarounds,
    }


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
