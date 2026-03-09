"""
Probe 007 supplemental: Congestion experiment with gentler limit reductions.
"""

import numpy as np
import pandapower as pp
from pandapower.converter.matpower.from_mpc import from_mpc

print("--- Congestion Experiment: 80% of DCPF flow on top 10 lines ---")
net = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
pp.rundcpp(net)

# Find top loaded lines by absolute flow
line_flows = net.res_line["p_from_mw"].abs()
top_lines = line_flows.nlargest(10).index

for idx in top_lines:
    current_flow_mw = abs(net.res_line.at[idx, "p_from_mw"])
    vn_kv = net.bus.at[net.line.at[idx, "from_bus"], "vn_kv"]
    target_mw = current_flow_mw * 0.80
    target_i_ka = target_mw / (np.sqrt(3) * vn_kv) if vn_kv > 0 else 0
    if target_i_ka > 0:
        net.line.at[idx, "max_i_ka"] = target_i_ka
        print(
            f"  Line {idx}: flow={current_flow_mw:.1f} MW, new limit={target_mw:.1f} MW"
        )

try:
    pp.rundcopp(net)
    if net["OPF_converged"]:
        lmps = net.res_bus["lam_p"].values
        print("Converged: Yes")
        print(f"LMP min: {np.min(lmps):.6f}")
        print(f"LMP max: {np.max(lmps):.6f}")
        print(f"LMP std: {np.std(lmps):.6e}")
        print(f"Unique LMPs: {len(np.unique(np.round(lmps, 4)))}")
        print(f"LMPs changed: {not np.allclose(lmps, lmps[0], atol=1e-6)}")
    else:
        print("Did not converge")
except Exception as e:
    print(f"Error: {e}")

# Try even gentler: 90% on top 5
print("\n--- Congestion Experiment: 90% of DCPF flow on top 5 lines ---")
net2 = from_mpc("/workspace/data/networks/case_ACTIVSg10k.m", f_hz=60)
pp.rundcpp(net2)

line_flows2 = net2.res_line["p_from_mw"].abs()
top_lines2 = line_flows2.nlargest(5).index

for idx in top_lines2:
    current_flow_mw = abs(net2.res_line.at[idx, "p_from_mw"])
    vn_kv = net2.bus.at[net2.line.at[idx, "from_bus"], "vn_kv"]
    target_mw = current_flow_mw * 0.90
    target_i_ka = target_mw / (np.sqrt(3) * vn_kv) if vn_kv > 0 else 0
    if target_i_ka > 0:
        net2.line.at[idx, "max_i_ka"] = target_i_ka
        print(
            f"  Line {idx}: flow={current_flow_mw:.1f} MW, new limit={target_mw:.1f} MW"
        )

try:
    pp.rundcopp(net2)
    if net2["OPF_converged"]:
        lmps2 = net2.res_bus["lam_p"].values
        print("Converged: Yes")
        print(f"LMP min: {np.min(lmps2):.6f}")
        print(f"LMP max: {np.max(lmps2):.6f}")
        print(f"LMP std: {np.std(lmps2):.6e}")
        print(f"Unique LMPs: {len(np.unique(np.round(lmps2, 4)))}")
        print(f"LMPs changed: {not np.allclose(lmps2, lmps2[0], atol=1e-6)}")
    else:
        print("Did not converge")
except Exception as e:
    print(f"Error: {e}")
