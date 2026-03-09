"""
Probe 007: Verify uniform LMP claim on ACTIVSg10k DC OPF.

Checks:
1. Branch loading distribution (any > 90%? any at 100%?)
2. LMP distribution (truly all identical?)
3. If uniform, scale down some branch limits and re-solve to confirm LMPs change with congestion
"""

import time

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc

start_time = time.perf_counter()

print("=" * 60)
print("PROBE 007: Uniform LMP verification on ACTIVSg10k DCOPF")
print("=" * 60)

# 1. Load network
print("\n--- Loading ACTIVSg10k ---")
net = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
print(f"Buses: {len(net.bus)}")
print(f"Lines: {len(net.line)}")
print(f"Trafos: {len(net.trafo)}")
print(f"Generators: {len(net.gen)}")
print(f"Ext grids: {len(net.ext_grid)}")
print(f"Poly costs: {len(net.poly_cost)}")

# Check if costs exist, add if not
has_costs = len(net.poly_cost) > 0 or len(net.pwl_cost) > 0
print(f"Has cost curves from import: {has_costs}")

# 2. Run DC OPF
print("\n--- Running DC OPF (base case) ---")
t0 = time.perf_counter()
pp.rundcopp(net)
t1 = time.perf_counter()
print(f"Converged: {net['OPF_converged']}")
print(f"Wall clock: {t1 - t0:.2f}s")
print(f"Objective: {float(net.res_cost):.2f}")

# 3. Extract and analyze LMPs
print("\n--- LMP Analysis ---")
lmps = net.res_bus["lam_p"].values
lmp_min = float(np.min(lmps))
lmp_max = float(np.max(lmps))
lmp_mean = float(np.mean(lmps))
lmp_std = float(np.std(lmps))
lmp_unique = len(np.unique(np.round(lmps, 6)))

print(f"LMP min: {lmp_min:.6f}")
print(f"LMP max: {lmp_max:.6f}")
print(f"LMP mean: {lmp_mean:.6f}")
print(f"LMP std: {lmp_std:.6e}")
print(f"Unique LMPs (rounded to 6dp): {lmp_unique}")
print(f"All identical (within 1e-6): {np.allclose(lmps, lmps[0], atol=1e-6)}")

# 4. Analyze branch loading
print("\n--- Branch Loading Analysis ---")
# For lines
if len(net.res_line) > 0 and "loading_percent" in net.res_line.columns:
    line_loading = net.res_line["loading_percent"].values
    line_loading_valid = line_loading[~np.isnan(line_loading)]
    print(f"Lines with loading data: {len(line_loading_valid)}/{len(net.res_line)}")
    if len(line_loading_valid) > 0:
        print(f"  Max loading: {np.max(line_loading_valid):.2f}%")
        print(f"  Mean loading: {np.mean(line_loading_valid):.2f}%")
        print(f"  Lines > 90%: {np.sum(line_loading_valid > 90)}")
        print(f"  Lines > 95%: {np.sum(line_loading_valid > 95)}")
        print(
            f"  Lines = 100%: {np.sum(np.isclose(line_loading_valid, 100, atol=0.1))}"
        )
else:
    print("No line loading results available")

# For trafos
if len(net.res_trafo) > 0 and "loading_percent" in net.res_trafo.columns:
    trafo_loading = net.res_trafo["loading_percent"].values
    trafo_loading_valid = trafo_loading[~np.isnan(trafo_loading)]
    print(f"Trafos with loading data: {len(trafo_loading_valid)}/{len(net.res_trafo)}")
    if len(trafo_loading_valid) > 0:
        print(f"  Max trafo loading: {np.max(trafo_loading_valid):.2f}%")
        print(f"  Trafos > 90%: {np.sum(trafo_loading_valid > 90)}")

# Check branch flow from ppc if available
print("\n--- Branch flow analysis via ppc ---")
if hasattr(net, "_ppc") and net._ppc is not None:
    ppc = net._ppc
    branch = ppc["branch"]
    from pandapower.pypower.idx_brch import PF, RATE_A

    flows = np.abs(branch[:, PF])
    rates = branch[:, RATE_A]
    # Filter branches with non-zero rate
    has_rate = rates > 0
    print(f"Branches with RATE_A > 0: {np.sum(has_rate)}/{len(rates)}")
    if np.sum(has_rate) > 0:
        loading_pct = (flows[has_rate] / rates[has_rate]) * 100
        print(f"  Max loading: {np.max(loading_pct):.2f}%")
        print(f"  Mean loading: {np.mean(loading_pct):.2f}%")
        print(f"  Branches > 90%: {np.sum(loading_pct > 90)}")
        print(f"  Branches > 95%: {np.sum(loading_pct > 95)}")
        print(f"  Branches > 99%: {np.sum(loading_pct > 99)}")
        print(f"  Branches = 100%: {np.sum(np.isclose(loading_pct, 100, atol=0.1))}")

        # Top 10 most loaded
        top_idx = np.argsort(loading_pct)[-10:][::-1]
        rated_indices = np.where(has_rate)[0]
        print("\n  Top 10 loaded branches:")
        for rank, i in enumerate(top_idx):
            br_idx = rated_indices[i]
            print(
                f"    {rank + 1}. Branch {br_idx}: {loading_pct[i]:.2f}% "
                f"(flow={flows[br_idx]:.2f} MW, limit={rates[br_idx]:.2f} MW)"
            )
    else:
        print("  No branches have rate limits set!")
else:
    print("No _ppc data available (need to run rundcopp with internals)")

# Try to also get the ppc from a DC power flow for comparison
print("\n--- Running DCPF to get ppc data ---")
net2 = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
pp.rundcpp(net2)
if hasattr(net2, "_ppc") and net2._ppc is not None:
    ppc2 = net2._ppc
    branch2 = ppc2["branch"]
    from pandapower.pypower.idx_brch import PF as PF2, RATE_A as RATE_A2

    flows2 = np.abs(branch2[:, PF2])
    rates2 = branch2[:, RATE_A2]
    has_rate2 = rates2 > 0
    print(f"DCPF - Branches with RATE_A > 0: {np.sum(has_rate2)}/{len(rates2)}")
    if np.sum(has_rate2) > 0:
        loading_pct2 = (flows2[has_rate2] / rates2[has_rate2]) * 100
        print(f"  DCPF Max loading: {np.max(loading_pct2):.2f}%")
        print(f"  DCPF Branches > 90%: {np.sum(loading_pct2 > 90)}")

# 5. If LMPs are uniform, try creating congestion
if np.allclose(lmps, lmps[0], atol=1e-6):
    print("\n--- Congestion Experiment: Reducing branch limits ---")
    net3 = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)

    # First, find the most loaded branches from DCPF
    pp.rundcpp(net3)
    if hasattr(net3, "_ppc") and net3._ppc is not None:
        ppc3 = net3._ppc
        branch3 = ppc3["branch"]
        dcpf_flows = np.abs(branch3[:, PF])

    # Now reduce line limits to 50% of current flow on top-loaded lines
    # This should force congestion
    if "max_i_ka" in net3.line.columns:
        # Get current flows from DCPF results
        line_flows = net3.res_line["p_from_mw"].abs().values
        # Find lines with significant flow
        significant = line_flows > 10  # MW
        n_reduced = 0
        for idx in net3.line.index[significant]:
            current_flow_mw = abs(net3.res_line.at[idx, "p_from_mw"])
            if current_flow_mw > 10:
                # Set max_i_ka to force limit at 50% of current flow
                # P = sqrt(3) * V * I * cos(phi), but for DC approx: P_MW = sqrt(3) * V_kV * I_kA
                vn_kv = net3.bus.at[net3.line.at[idx, "from_bus"], "vn_kv"]
                target_mw = current_flow_mw * 0.5
                target_i_ka = target_mw / (np.sqrt(3) * vn_kv) if vn_kv > 0 else 0
                if target_i_ka > 0:
                    net3.line.at[idx, "max_i_ka"] = target_i_ka
                    n_reduced += 1
            if n_reduced >= 50:
                break

        print(f"Reduced limits on {n_reduced} lines to 50% of DCPF flow")

        # Re-run DC OPF
        try:
            pp.rundcopp(net3)
            if net3["OPF_converged"]:
                lmps3 = net3.res_bus["lam_p"].values
                lmp3_min = float(np.min(lmps3))
                lmp3_max = float(np.max(lmps3))
                lmp3_std = float(np.std(lmps3))
                lmp3_unique = len(np.unique(np.round(lmps3, 6)))
                print("Congested case converged: Yes")
                print(f"Congested LMP min: {lmp3_min:.6f}")
                print(f"Congested LMP max: {lmp3_max:.6f}")
                print(f"Congested LMP std: {lmp3_std:.6e}")
                print(f"Congested unique LMPs: {lmp3_unique}")
                print(f"LMPs changed: {not np.allclose(lmps3, lmps3[0], atol=1e-6)}")
                print(f"Objective: {float(net3.res_cost):.2f}")
            else:
                print("Congested case did NOT converge")
        except Exception as e:
            print(f"Congested case error: {e}")

elapsed = time.perf_counter() - start_time
print(f"\n--- Total elapsed: {elapsed:.2f}s ---")
