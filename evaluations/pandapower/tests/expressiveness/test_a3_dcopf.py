"""
Test A-3: Solve DC OPF with gen costs and line flow limits

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable
    from solution. With differentiated costs and 70% derating, at least 2 branches
    have non-zero shadow prices (binding flow constraints). Report max LMP spread
    across buses.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
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

BRANCH_DERATING = 0.70


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute DC OPF test and return structured results."""
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

        # 1. Load network
        net = load_pandapower(network_file)
        results["details"]["bus_count"] = len(net.bus)
        results["details"]["line_count"] = len(net.line)
        results["details"]["trafo_count"] = len(net.trafo)
        results["details"]["gen_count"] = len(net.gen)
        results["details"]["ext_grid_count"] = len(net.ext_grid)

        # 2. Load differentiated costs from timeseries dir
        if timeseries_dir is None:
            results["errors"].append("timeseries_dir is required for A-3 TINY")
            return results

        ts_dir = Path(timeseries_dir)
        gen_params = pd.read_csv(ts_dir / "gen_temporal_params.csv")
        results["details"]["gen_params_loaded"] = len(gen_params)

        # 3. Apply differentiated costs to generators and ext_grid
        # pandapower OPF requires cost functions via create_poly_cost
        # First, set controllable=True and P limits on generators
        for idx in net.gen.index:
            net.gen.at[idx, "controllable"] = True
            net.gen.at[idx, "min_p_mw"] = 0.0
            # max_p_mw is already set from MATPOWER data

        # ext_grid is the slack bus — also needs cost and controllable for OPF
        for idx in net.ext_grid.index:
            net.ext_grid.at[idx, "controllable"] = True
            # Set reasonable P limits for ext_grid
            net.ext_grid.at[idx, "min_p_mw"] = -9999.0
            net.ext_grid.at[idx, "max_p_mw"] = 9999.0

        # Set bus voltage limits (required for OPF even in DC mode)
        net.bus["min_vm_pu"] = 0.9
        net.bus["max_vm_pu"] = 1.1

        # Clear existing cost functions (from_mpc may have created them)
        net.poly_cost.drop(net.poly_cost.index, inplace=True)
        if hasattr(net, "pwl_cost"):
            net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

        # Apply cost functions using gen_temporal_params tech_class_key
        # gen_params is indexed by gen_index (0-based matching MATPOWER order)
        # pandapower gen table may differ in indexing from MATPOWER after conversion
        # The ext_grid (bus 39 in case39) is gen_index=9 in MATPOWER

        # Map MATPOWER gen indices to pandapower elements
        # In pandapower from_mpc, one generator becomes ext_grid (the slack),
        # the rest become gen elements
        for _, row in gen_params.iterrows():
            gen_idx_mat = int(row["gen_index"])
            tech = row["tech_class_key"]
            costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
            # gen_temporal_params uses 1-indexed MATPOWER bus IDs;
            # pandapower from_mpc uses 0-indexed buses
            bus_id_pp = int(row["bus_id"]) - 1

            # Find the pandapower element for this generator
            # Check ext_grid first
            ext_match = net.ext_grid[net.ext_grid["bus"] == bus_id_pp]
            gen_match = net.gen[net.gen["bus"] == bus_id_pp]

            if len(ext_match) > 0:
                eidx = ext_match.index[0]
                pp.create_poly_cost(
                    net,
                    element=eidx,
                    et="ext_grid",
                    cp1_eur_per_mw=costs["cp1"],
                    cp2_eur_per_mw2=costs["cp2"],
                    cp0_eur=0.0,
                )
            elif len(gen_match) > 0:
                gidx = gen_match.index[0]
                pp.create_poly_cost(
                    net,
                    element=gidx,
                    et="gen",
                    cp1_eur_per_mw=costs["cp1"],
                    cp2_eur_per_mw2=costs["cp2"],
                    cp0_eur=0.0,
                )
            else:
                results["errors"].append(
                    f"Could not find pandapower element for MATPOWER gen_index={gen_idx_mat} "
                    f"at pp bus {bus_id_pp} (MATPOWER bus {int(row['bus_id'])})"
                )

        results["details"]["cost_functions_created"] = len(net.poly_cost)

        # 4. Apply branch derating (70%)
        # Derate lines
        net.line["max_loading_percent"] = 100.0  # Ensure the column exists
        original_max_i_ka = net.line["max_i_ka"].copy()
        net.line["max_i_ka"] = original_max_i_ka * BRANCH_DERATING

        # Derate transformers
        if len(net.trafo) > 0:
            net.trafo["max_loading_percent"] = 100.0

        results["details"]["branch_derating"] = BRANCH_DERATING

        # 5. Solve DC OPF
        solve_start = time.perf_counter()
        pp.rundcopp(net)
        solve_time = time.perf_counter() - solve_start
        results["details"]["solve_seconds"] = solve_time

        # 6. Check convergence
        opf_converged = net.OPF_converged
        results["details"]["opf_converged"] = opf_converged
        if not opf_converged:
            results["errors"].append("DC OPF did not converge")
            return results

        # 7. Extract dispatch results
        gen_dispatch = net.res_gen["p_mw"].to_dict()
        ext_grid_dispatch = net.res_ext_grid["p_mw"].to_dict()
        results["details"]["gen_dispatch_mw"] = gen_dispatch
        results["details"]["ext_grid_dispatch_mw"] = ext_grid_dispatch
        results["details"]["total_generation_mw"] = float(
            net.res_gen["p_mw"].sum() + net.res_ext_grid["p_mw"].sum()
        )
        results["details"]["total_load_mw"] = float(net.load["p_mw"].sum())

        # 8. Extract LMPs / shadow prices
        # pandapower's PYPOWER OPF stores bus shadow prices in net._ppc
        lmp_extracted = False
        lmp_source = None
        bus_lmps = {}

        # Try extracting from internal PYPOWER result
        try:
            ppc = net._ppc
            # PYPOWER stores bus marginal prices in bus column 13 (LAM_P)
            if ppc is not None and "bus" in ppc:
                bus_data = ppc["bus"]
                # Column indices: LAM_P=13, LAM_Q=14, MU_VMAX=15, MU_VMIN=16
                if bus_data.shape[1] > 13:
                    lam_p = bus_data[:, 13]
                    results["details"]["lam_p_raw"] = lam_p.tolist()
                    if np.any(np.abs(lam_p) > 1e-10):
                        lmp_extracted = True
                        lmp_source = "net._ppc['bus'][:, 13] (LAM_P)"
                        # Map internal bus indices back to pandapower bus indices
                        # _ppc uses internal indexing; need pd2ppc lookups
                        try:
                            bus_lookup = net._pd2ppc_lookups.get("bus", None)
                            if bus_lookup is not None:
                                for pp_bus_idx in net.bus.index:
                                    internal_idx = bus_lookup[pp_bus_idx]
                                    bus_lmps[int(pp_bus_idx)] = float(lam_p[internal_idx])
                        except Exception:
                            # Fallback: assume sequential mapping
                            for i, val in enumerate(lam_p):
                                bus_lmps[i] = float(val)
        except (AttributeError, KeyError, IndexError) as e:
            results["details"]["lmp_extraction_error"] = str(e)

        # Also check res_bus for any LMP-like columns
        res_bus_cols = list(net.res_bus.columns)
        results["details"]["res_bus_columns"] = res_bus_cols
        lmp_cols = [c for c in res_bus_cols if "lam" in c.lower() or "lmp" in c.lower()]
        results["details"]["lmp_columns_in_res_bus"] = lmp_cols

        results["details"]["lmp_extracted"] = lmp_extracted
        results["details"]["lmp_source"] = lmp_source
        results["details"]["bus_lmps"] = bus_lmps

        if bus_lmps:
            lmp_values = list(bus_lmps.values())
            max_lmp = max(lmp_values)
            min_lmp = min(lmp_values)
            lmp_spread = max_lmp - min_lmp
            results["details"]["max_lmp"] = max_lmp
            results["details"]["min_lmp"] = min_lmp
            results["details"]["lmp_spread"] = lmp_spread
        else:
            results["details"]["lmp_spread"] = None

        # 9. Extract branch shadow prices / binding constraints
        binding_branches = 0
        branch_shadow_prices = {}

        try:
            ppc = net._ppc
            if ppc is not None and "branch" in ppc:
                branch_data = ppc["branch"]
                # MU_SF=13, MU_ST=14 (shadow prices on from/to flow limits)
                if branch_data.shape[1] > 14:
                    mu_sf = branch_data[:, 13]
                    mu_st = branch_data[:, 14]
                    for i in range(len(mu_sf)):
                        mu = max(abs(mu_sf[i]), abs(mu_st[i]))
                        if mu > 1e-6:
                            binding_branches += 1
                            branch_shadow_prices[i] = {
                                "mu_sf": float(mu_sf[i]),
                                "mu_st": float(mu_st[i]),
                            }
        except (AttributeError, KeyError, IndexError) as e:
            results["details"]["shadow_price_extraction_error"] = str(e)

        results["details"]["binding_branches"] = binding_branches
        results["details"]["branch_shadow_prices"] = branch_shadow_prices

        # 10. Check line loading
        line_loading = net.res_line["loading_percent"]
        results["details"]["max_line_loading_pct"] = float(line_loading.max())
        results["details"]["lines_above_95pct_loading"] = int((line_loading > 95.0).sum())

        # 11. Objective value
        try:
            ppc = net._ppc
            if ppc is not None and "f" in ppc:
                results["details"]["objective_value"] = float(ppc["f"])
        except (AttributeError, KeyError):
            pass

        results["details"]["output_format"] = "pandas.DataFrame + net._ppc internals"

        # 12. Check pass conditions
        if not lmp_extracted:
            results["workarounds"].append(
                "LMPs extracted from internal PYPOWER structure (net._ppc['bus'][:, 13]) "
                "rather than a public API. This is a fragile workaround that accesses "
                "private attributes."
            )

        if binding_branches < 2:
            results["errors"].append(
                f"Only {binding_branches} branches have non-zero shadow prices "
                f"(need >= 2 with 70% derating and differentiated costs)"
            )
            # Still report results but don't pass
        else:
            results["status"] = "pass" if lmp_extracted else "qualified_pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
