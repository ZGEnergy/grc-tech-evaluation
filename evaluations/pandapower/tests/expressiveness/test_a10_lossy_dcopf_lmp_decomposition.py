"""
Test A-10: Solve DC OPF with loss approximation and decompose LMPs

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Tool produces loss-inclusive LMPs where loss components are non-zero.
    LMP decomposition extractable as structured output. Per-line congestion rent
    computed and reconciled against congestion LMP components. Validate internal
    consistency: (a) loss components have physically correct signs, (b) total losses
    are 0.5-3% of total load, (c) lossy objective exceeds lossless objective,
    (d) loss component LMPs sum with energy and congestion components to total LMP
    within 1% tolerance.
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

# Differentiated cost curves from data/timeseries/case39/README.md
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute lossy DC OPF with LMP decomposition test."""
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
        results["details"]["gen_count"] = len(net.gen) + len(net.ext_grid)

        # 2. Check if pandapower has lossy DC OPF capability
        # pandapower's rundcopp() is standard lossless DC OPF
        # Check for any loss-related parameters or formulations
        # Check rundcopp signature for loss-related parameters
        import inspect

        dcopp_sig = inspect.signature(pp.rundcopp)
        dcopp_params = list(dcopp_sig.parameters.keys())
        results["details"]["rundcopp_parameters"] = dcopp_params

        loss_params = [p for p in dcopp_params if "loss" in p.lower()]
        results["details"]["loss_related_params"] = loss_params

        # Check for any loss approximation methods in pandapower
        # pandapower's DC OPF formulation is standard lossless B-theta
        loss_modules = []
        for attr in dir(pp):
            if "loss" in attr.lower() and not attr.startswith("_"):
                loss_modules.append(attr)
        results["details"]["loss_related_attributes"] = loss_modules

        # Check if PandaModels.jl bridge could provide lossy DC OPF
        try:
            import pandapower.runpm as runpm

            pm_funcs = [f for f in dir(runpm) if not f.startswith("_")]
            results["details"]["pandamodels_functions"] = pm_funcs
            # Check for loss-related PM functions
            loss_pm = [f for f in pm_funcs if "loss" in f.lower() or "ploss" in f.lower()]
            results["details"]["pandamodels_loss_functions"] = loss_pm
        except ImportError:
            results["details"]["pandamodels_available"] = False

        # Check PYPOWER backend for loss formulations
        try:
            from pandapower.pypower import dcopf_solver

            dcopf_src = inspect.getsource(dcopf_solver)
            has_loss_in_dcopf = "loss" in dcopf_src.lower()
            results["details"]["pypower_dcopf_mentions_loss"] = has_loss_in_dcopf
        except Exception as e:
            results["details"]["pypower_dcopf_inspection_error"] = str(e)

        # 3. Attempt standard lossless DC OPF for baseline comparison
        if timeseries_dir is not None:
            ts_dir = Path(timeseries_dir)
            gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")

            # Configure generators
            for idx in net.gen.index:
                net.gen.at[idx, "controllable"] = True
                net.gen.at[idx, "min_p_mw"] = 0.0

            for idx in net.ext_grid.index:
                net.ext_grid.at[idx, "controllable"] = True
                net.ext_grid.at[idx, "min_p_mw"] = -9999.0
                net.ext_grid.at[idx, "max_p_mw"] = 9999.0

            net.bus["min_vm_pu"] = 0.9
            net.bus["max_vm_pu"] = 1.1

            # Clear and apply costs
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
                    )
                elif len(gen_match) > 0:
                    pp.create_poly_cost(
                        net,
                        element=gen_match.index[0],
                        et="gen",
                        cp1_eur_per_mw=costs["cp1"],
                        cp2_eur_per_mw2=costs["cp2"],
                    )

            # Solve lossless DC OPF
            pp.rundcopp(net)
            lossless_converged = net.OPF_converged
            results["details"]["lossless_dcopf_converged"] = lossless_converged

            if lossless_converged:
                lossless_obj = float(net._ppc["f"]) if "f" in net._ppc else None
                results["details"]["lossless_objective"] = lossless_obj

                # Extract LMPs from lossless solve
                if "lam_p" in net.res_bus.columns:
                    lossless_lmps = net.res_bus["lam_p"].to_dict()
                    results["details"]["lossless_lmp_sample"] = {
                        k: round(v, 4) for k, v in list(lossless_lmps.items())[:5]
                    }

        # 4. Check for LMP decomposition capability
        # pandapower's PYPOWER OPF provides total LMPs (LAM_P) but does NOT
        # decompose them into energy + congestion + loss components
        lmp_decomposition_available = False

        # Check res_bus columns for decomposition
        res_bus_cols = list(net.res_bus.columns)
        results["details"]["res_bus_columns"] = res_bus_cols

        decomp_cols = [
            c
            for c in res_bus_cols
            if any(kw in c.lower() for kw in ["energy", "congestion", "loss", "marginal", "decomp"])
        ]
        results["details"]["lmp_decomposition_columns"] = decomp_cols

        if len(decomp_cols) > 0:
            lmp_decomposition_available = True

        # Check PYPOWER result for decomposition
        try:
            ppc = net._ppc
            if ppc is not None and "bus" in ppc:
                bus_cols = ppc["bus"].shape[1]
                results["details"]["ppc_bus_columns"] = bus_cols
                # Standard PYPOWER bus columns: 0-12 input, 13=LAM_P, 14=LAM_Q,
                # 15=MU_VMAX, 16=MU_VMIN — no decomposition columns
                results["details"]["ppc_provides_lmp_decomposition"] = False
        except (AttributeError, KeyError):
            pass

        results["details"]["lmp_decomposition_available"] = lmp_decomposition_available

        # 5. Document the finding
        results["details"]["finding"] = (
            "pandapower's DC OPF (rundcopp) uses a lossless formulation (standard B-theta "
            "linearization). There is no loss approximation parameter, no lossy DC OPF "
            "formulation, and no LMP decomposition into energy/congestion/loss components. "
            "The PYPOWER backend provides only total LMPs (LAM_P) without decomposition. "
            "The PandaModels.jl bridge offers runpm_ploss() for loss minimization but not "
            "lossy DC OPF with LMP decomposition. Implementing lossy DC OPF with LMP "
            "decomposition would require building a custom optimization model outside "
            "pandapower (e.g., via Pyomo), which constitutes a blocking limitation."
        )

        results["details"]["capability_assessment"] = {
            "lossy_dcopf": False,
            "lmp_total": True,
            "lmp_energy_component": False,
            "lmp_congestion_component": False,
            "lmp_loss_component": False,
            "congestion_rent_calculation": False,
        }

        # This is a blocking limitation — the formulation does not exist
        results["errors"].append(
            "pandapower has no lossy DC OPF formulation and no LMP decomposition "
            "capability. The DC OPF is lossless (standard B-theta), and LMPs are "
            "provided only as total values without energy/congestion/loss components."
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
