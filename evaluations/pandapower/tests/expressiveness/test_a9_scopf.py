"""
Test A-9: Solve DC OPF with N-1 contingency flow constraints embedded in optimization

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Solves. Base-case dispatch respects all contingency flow limits
    simultaneously. Dispatch and cost differ from unconstrained DC OPF (A-3).
    Contingency constraints are part of the optimization, not checked post-hoc.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))

from matpower_loader import load_pandapower

# Differentiated cost curves (same as A-3)
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}

BRANCH_DERATING = 0.70


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute SCOPF test — pandapower has no native SCOPF.

    This test documents that pandapower lacks SCOPF and investigates whether
    it can be achieved via manual constraint enumeration or the PandaModels.jl
    bridge. pandapower's contingency analysis (run_contingency) is post-hoc
    checking, not embedded in optimization.
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import pandapower as pp

        results["details"]["pandapower_version"] = pp.__version__

        # 1. Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["branch_count"] = len(net.line) + len(net.trafo)

        # 2. Document native SCOPF capabilities
        results["details"]["native_scopf"] = False
        results["details"]["contingency_analysis_type"] = "post-hoc"

        # Check available contingency functions
        has_contingency_module = hasattr(pp, "contingency")
        results["details"]["has_contingency_module"] = has_contingency_module

        # Check available OPF functions
        opf_functions = [
            f for f in dir(pp) if "opf" in f.lower() or "opp" in f.lower() or "scopf" in f.lower()
        ]
        results["details"]["opf_related_functions"] = opf_functions

        # Check for PandaModels.jl bridge
        pandamodels_available = False
        try:
            import pandamodels  # noqa: F401

            pandamodels_available = True
        except ImportError:
            pass
        results["details"]["pandamodels_available"] = pandamodels_available

        # 3. Document what pandapower CAN do for contingency analysis
        results["details"]["contingency_capabilities"] = {
            "run_contingency": (
                "Post-hoc N-1 contingency analysis via "
                "pandapower.contingency.run_contingency(). "
                "Runs power flow for each contingency case independently. "
                "Does NOT embed contingency constraints in optimization."
            ),
            "run_contingency_ls2g": (
                "Accelerated post-hoc contingency analysis via lightsim2grid backend. "
                "Same limitation: post-hoc, not optimization-embedded."
            ),
        }

        # 4. Investigate whether manual SCOPF construction is feasible
        # pandapower's OPF uses PYPOWER interior-point which does NOT support
        # user-injected constraints. The custom constraint API (B-1) is limited
        # to predefined constraint types (voltage, loading, P/Q limits).
        results["details"]["manual_scopf_feasibility"] = {
            "pypower_opf_custom_constraints": False,
            "explanation": (
                "pandapower's native OPF (via PYPOWER interior-point) does not "
                "support arbitrary user-defined constraints. There is no API to "
                "inject contingency flow constraints into the optimization problem. "
                "The OPF formulation is hard-coded in the PYPOWER solver. "
                "To implement SCOPF, one would need to: "
                "(1) Build a custom optimization model from scratch using Pyomo or "
                "scipy.optimize, manually constructing the PTDF-based DC OPF with "
                "N-1 contingency constraints, OR "
                "(2) Use the PandaModels.jl Julia bridge (not installed in this "
                "environment) which could access PowerModels.jl formulations — "
                "but PowerModels.jl does not have native SCOPF either."
            ),
        }

        # 5. Demonstrate that contingency analysis is post-hoc only
        # Run a standard DC OPF first, then show the contingency analysis
        # is a separate post-hoc step

        # Apply differentiated costs (same setup as A-3)
        if timeseries_dir is not None:
            ts_dir = Path(timeseries_dir)
            gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

            for idx in net.gen.index:
                net.gen.at[idx, "controllable"] = True
                net.gen.at[idx, "min_p_mw"] = 0.0

            for idx in net.ext_grid.index:
                net.ext_grid.at[idx, "controllable"] = True
                net.ext_grid.at[idx, "min_p_mw"] = -9999.0
                net.ext_grid.at[idx, "max_p_mw"] = 9999.0

            net.bus["min_vm_pu"] = 0.9
            net.bus["max_vm_pu"] = 1.1

            net.poly_cost.drop(net.poly_cost.index, inplace=True)
            if hasattr(net, "pwl_cost") and len(net.pwl_cost) > 0:
                net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

            for _, row in gen_params.iterrows():
                tech = row["tech_class_key"]
                costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
                bus_id_pp = int(row["bus_id"]) - 1

                ext_match = net.ext_grid[net.ext_grid["bus"] == bus_id_pp]
                gen_match = net.gen[net.gen["bus"] == bus_id_pp]

                if len(ext_match) > 0:
                    pp.create_poly_cost(
                        net,
                        element=ext_match.index[0],
                        et="ext_grid",
                        cp1_eur_per_mw=costs["cp1"],
                        cp2_eur_per_mw2=costs["cp2"],
                        cp0_eur=0.0,
                    )
                elif len(gen_match) > 0:
                    pp.create_poly_cost(
                        net,
                        element=gen_match.index[0],
                        et="gen",
                        cp1_eur_per_mw=costs["cp1"],
                        cp2_eur_per_mw2=costs["cp2"],
                        cp0_eur=0.0,
                    )

        # Apply branch derating
        net.line["max_loading_percent"] = 100.0
        net.line["max_i_ka"] = net.line["max_i_ka"] * BRANCH_DERATING
        if len(net.trafo) > 0:
            net.trafo["max_loading_percent"] = 100.0

        # Run standard DC OPF (for reference — this is what A-3 does)
        pp.rundcopp(net)
        base_opf_converged = net.OPF_converged
        results["details"]["base_dcopf_converged"] = base_opf_converged

        if base_opf_converged:
            base_cost = float(net._ppc["f"]) if hasattr(net, "_ppc") and "f" in net._ppc else None
            base_gen_dispatch = net.res_gen["p_mw"].tolist()
            base_ext_dispatch = net.res_ext_grid["p_mw"].tolist()
            results["details"]["base_dcopf_cost"] = base_cost
            results["details"]["base_gen_dispatch_mw"] = base_gen_dispatch
            results["details"]["base_ext_dispatch_mw"] = base_ext_dispatch

            # Run post-hoc contingency analysis to show it exists but is not SCOPF
            try:
                from pandapower.contingency import run_contingency

                # Create a contingency list — remove each line one at a time
                nminus1_lines = list(net.line.index[net.line["in_service"]])
                results["details"]["n_contingencies_possible"] = len(nminus1_lines)

                # Run contingency analysis (post-hoc, not optimization-embedded)
                contingency_start = time.perf_counter()
                run_contingency(net, nminus1_cases=nminus1_lines)
                contingency_time = time.perf_counter() - contingency_start
                results["details"]["contingency_analysis_time_s"] = contingency_time

                # Check if any contingency violates limits
                if hasattr(net, "res_line_contingency"):
                    max_loading = net.res_line_contingency.max().max()
                    results["details"]["max_contingency_loading_pct"] = float(max_loading)
                    violations = (net.res_line_contingency > 100.0).any().any()
                    results["details"]["contingency_violations_exist"] = bool(violations)
                else:
                    results["details"]["contingency_result_format"] = (
                        "run_contingency does not produce res_line_contingency; "
                        "results may be stored differently in pandapower 3.4.0"
                    )
            except ImportError:
                results["details"]["contingency_module_import_error"] = True
            except Exception as ce:
                results["details"]["contingency_analysis_error"] = str(ce)

        # 6. Final assessment
        results["details"]["assessment"] = (
            "pandapower 3.4.0 does NOT support SCOPF (Security-Constrained OPF). "
            "It has post-hoc contingency analysis (run_contingency) that checks "
            "N-1 violations AFTER solving an unconstrained OPF, but the contingency "
            "constraints are NOT embedded in the optimization. "
            "There is no API to inject user-defined constraints into the PYPOWER "
            "OPF solver. Achieving SCOPF would require building a complete custom "
            "optimization model from scratch (e.g., using Pyomo with PTDF-based "
            "formulation and explicit N-1 branch flow constraints), which is a "
            "blocking workaround — it does not use pandapower's OPF at all."
        )

        results["errors"].append(
            "pandapower 3.4.0 does not support SCOPF. Contingency analysis is "
            "post-hoc only (run_contingency), not embedded in optimization. "
            "No API exists to inject contingency constraints into the OPF formulation."
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
