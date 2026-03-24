"""
probe-003: Verify A-3 branch shadow price claim for pandapower.

Claim: "All 46 branches have non-zero shadow prices in A-3 DC OPF"
Question: Are these meaningful binding constraints or numerical artifacts from
          the interior-point solver?

The original test used threshold: mu > 1e-6
"""

import importlib.util
import os
import sys
import time

import numpy as np
import pandas as pd
import pandapower as pp
from pandapower.converter.matpower import from_mpc

print(f"pandapower version: {pp.__version__}")


def load_network(case_path):
    """Load network using shared loader if available, else use from_mpc directly."""
    loader_path = "/workspace/evaluations/pandapower/shared/matpower_loader.py"
    if os.path.exists(loader_path):
        spec = importlib.util.spec_from_file_location("matpower_loader", loader_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.load_pandapower(case_path)
    else:
        return from_mpc(case_path, f_hz=60)


# ── 1. Load network ──────────────────────────────────────────────────────────
case_path = "/workspace/data/networks/case39.m"
print(f"\nLoading network: {case_path}")
net = load_network(case_path)
n_lines = len(net.line)
n_trafo = len(net.trafo)
total_branches = n_lines + n_trafo
print(
    f"  buses: {len(net.bus)}, lines: {n_lines}, trafos: {n_trafo}, gens: {len(net.gen)}, ext_grid: {len(net.ext_grid)}"
)

# ── 2. Apply differentiated costs (exact replication of A-3 eval) ─────────────
COST_BY_TECH = {
    "hydro": {"cp1": 5.0, "cp2": 0.005},
    "nuclear": {"cp1": 10.0, "cp2": 0.010},
    "coal_large": {"cp1": 25.0, "cp2": 0.025},
    "gas_CC": {"cp1": 40.0, "cp2": 0.040},
}

gen_params = pd.read_csv("/workspace/data/timeseries/case39/gen_temporal_params.csv")

# Set controllable
for idx in net.gen.index:
    net.gen.at[idx, "controllable"] = True
    net.gen.at[idx, "min_p_mw"] = 0.0
for idx in net.ext_grid.index:
    net.ext_grid.at[idx, "controllable"] = True
    net.ext_grid.at[idx, "min_p_mw"] = -9999.0
    net.ext_grid.at[idx, "max_p_mw"] = 9999.0

net.bus["min_vm_pu"] = 0.9
net.bus["max_vm_pu"] = 1.1

# Clear existing costs
net.poly_cost.drop(net.poly_cost.index, inplace=True)
if hasattr(net, "pwl_cost"):
    net.pwl_cost.drop(net.pwl_cost.index, inplace=True)

# Apply costs matching original script logic
for _, row in gen_params.iterrows():
    tech = row["tech_class_key"]
    costs = COST_BY_TECH.get(tech, COST_BY_TECH["gas_CC"])
    bus_id_pp = int(row["bus_id"]) - 1

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

print(f"  Cost functions created: {len(net.poly_cost)}")

# ── 3. Apply 70% thermal derating ────────────────────────────────────────────
BRANCH_DERATING = 0.70
net.line["max_loading_percent"] = 100.0
net.line["max_i_ka"] = net.line["max_i_ka"] * BRANCH_DERATING
if len(net.trafo) > 0:
    net.trafo["max_loading_percent"] = 100.0
print(f"  Applied 70% derating to {n_lines} lines and {n_trafo} trafos")

# ── 4. Solve DC OPF ──────────────────────────────────────────────────────────
print("\nRunning DC OPF...")
t0 = time.time()
pp.rundcopp(net, verbose=False)
t_solve = time.time() - t0
print(f"  OPF converged: {net.OPF_converged}")
print(f"  Solve time: {t_solve:.3f}s")

if not net.OPF_converged:
    print("ERROR: OPF did not converge!")
    sys.exit(1)

# ── 5. Extract branch shadow prices ──────────────────────────────────────────
print("\n" + "=" * 70)
print("BRANCH SHADOW PRICE ANALYSIS")
print("=" * 70)

ppc = net._ppc
branch_data = ppc["branch"]
mu_sf = branch_data[:, 13]  # MU_SF
mu_st = branch_data[:, 14]  # MU_ST
n_ppc_branches = len(mu_sf)

print(f"\nTotal branches in PYPOWER (ppc) model: {n_ppc_branches}")
print(f"  (Lines: {n_lines}, Trafos: {n_trafo}, Total: {total_branches})")

# Shadow price as max of both directions
shadow_price = np.maximum(np.abs(mu_sf), np.abs(mu_st))

print("\nRaw shadow price distribution (max(|MU_SF|, |MU_ST|)):")
print(f"  Min:    {shadow_price.min():.6e}")
print(f"  Max:    {shadow_price.max():.6e}")
print(f"  Mean:   {shadow_price.mean():.6e}")
print(f"  Median: {np.median(shadow_price):.6e}")
print(f"  P25:    {np.percentile(shadow_price, 25):.6e}")
print(f"  P75:    {np.percentile(shadow_price, 75):.6e}")

# Exactly zero
n_exactly_zero = int(np.sum(shadow_price == 0.0))
print(f"\n  Exactly zero: {n_exactly_zero}")

# Threshold analysis - the ORIGINAL TEST used 1e-6
print("\nThreshold analysis (original test used 1e-6):")
thresholds = [0.0, 1e-10, 1e-8, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0, 100.0]
print(f"  {'Threshold':>12}  {'Count':>6}  {'Fraction':>8}  Assessment")
for thresh in thresholds:
    count = int(np.sum(shadow_price > thresh))
    if thresh == 1e-6:
        assess = "<-- ORIGINAL TEST THRESHOLD"
    elif thresh <= 1e-4:
        assess = "likely artifact"
    elif thresh <= 0.1:
        assess = "borderline"
    else:
        assess = "likely meaningful"
    print(f"  {thresh:>12.2e}  {count:>6d}  {count / n_ppc_branches:>8.1%}  {assess}")

# ── 6. LMP statistics ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ECONOMIC SIGNIFICANCE ASSESSMENT")
print("=" * 70)

lam_p = ppc["bus"][:, 13]  # LAM_P - bus marginal prices
print("\nLMP statistics ($/MWh):")
print(f"  Min LMP: {lam_p.min():.4f}")
print(f"  Max LMP: {lam_p.max():.4f}")
print(f"  Spread:  {lam_p.max() - lam_p.min():.4f}")

lmp_spread = lam_p.max() - lam_p.min()
n_meaningful = int(np.sum(shadow_price > 1.0))
n_moderate = int(np.sum(shadow_price > 0.1))
n_small = int(np.sum(shadow_price > 0.01))
n_tiny = int(np.sum(shadow_price > 1e-4))
n_above_orig = int(np.sum(shadow_price > 1e-6))

print(f"\nShadow price magnitude categories (LMP spread = {lmp_spread:.2f} $/MWh):")
print(f"  > 1.0 (economically significant):   {n_meaningful:3d} / {n_ppc_branches}")
print(f"  > 0.1 (moderate):                   {n_moderate:3d} / {n_ppc_branches}")
print(f"  > 0.01 (small but maybe meaningful): {n_small:3d} / {n_ppc_branches}")
print(f"  > 1e-4 (very small):                {n_tiny:3d} / {n_ppc_branches}")
print(f"  > 1e-6 (original test threshold):   {n_above_orig:3d} / {n_ppc_branches}")

# ── 7. Branch-by-branch table with loading ───────────────────────────────────
print("\n" + "=" * 70)
print("FULL BRANCH TABLE (lines only)")
print("=" * 70)

if hasattr(net, "res_line") and len(net.res_line) > 0:
    loading_pct = net.res_line["loading_percent"].values

    print(f"\nAll {n_lines} lines (loading vs shadow price):")
    print(
        f"  {'Line':>5}  {'Loading%':>9}  {'MU_SF':>12}  {'MU_ST':>12}  {'max|mu|':>12}  Category"
    )
    for i in range(n_lines):
        mu_sf_i = mu_sf[i]
        mu_st_i = mu_st[i]
        sp_i = shadow_price[i]
        if sp_i > 1.0:
            cat = "BINDING"
        elif sp_i > 0.01:
            cat = "moderate"
        elif sp_i > 1e-6:
            cat = "artifact?"
        else:
            cat = "zero"
        print(
            f"  {i:>5}  {loading_pct[i]:>9.3f}  {mu_sf_i:>12.6e}  {mu_st_i:>12.6e}  {sp_i:>12.6e}  {cat}"
        )

    n_above_95 = int(np.sum(loading_pct > 95.0))
    n_above_80 = int(np.sum(loading_pct > 80.0))
    n_above_50 = int(np.sum(loading_pct > 50.0))
    print("\nLine loading summary:")
    print(f"  Lines > 95% loading: {n_above_95}")
    print(f"  Lines > 80% loading: {n_above_80}")
    print(f"  Lines > 50% loading: {n_above_50}")

    # Correlation
    corr = np.corrcoef(loading_pct, shadow_price[:n_lines])[0, 1]
    print(f"\n  Pearson correlation (loading% vs shadow_price): {corr:.4f}")

    # Low vs high loading shadow prices
    low_loading = loading_pct < 50.0
    high_loading = loading_pct >= 50.0
    print(f"\n  Low-loading lines (<50%, n={int(np.sum(low_loading))}):")
    if np.sum(low_loading) > 0:
        print(
            f"    Mean |shadow_price|: {shadow_price[:n_lines][low_loading].mean():.6e}"
        )
        print(
            f"    Max |shadow_price|:  {shadow_price[:n_lines][low_loading].max():.6e}"
        )
        print(
            f"    Min |shadow_price|:  {shadow_price[:n_lines][low_loading].min():.6e}"
        )
    print(f"\n  High-loading lines (>=50%, n={int(np.sum(high_loading))}):")
    if np.sum(high_loading) > 0:
        print(
            f"    Mean |shadow_price|: {shadow_price[:n_lines][high_loading].mean():.6e}"
        )
        print(
            f"    Max |shadow_price|:  {shadow_price[:n_lines][high_loading].max():.6e}"
        )
        print(
            f"    Min |shadow_price|:  {shadow_price[:n_lines][high_loading].min():.6e}"
        )

# ── 8. Summary and verdict ────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PROBE VERDICT")
print("=" * 70)

print(f"""
Claim: "All 46 branches have non-zero shadow prices in A-3 DC OPF"
Original test threshold: mu > 1e-6

Findings:
  - PYPOWER model has {n_ppc_branches} branches
  - Branches with |shadow_price| > 1e-6: {n_above_orig}  (original claim basis)
  - Branches with |shadow_price| > 1e-2: {n_small}   (potentially meaningful)
  - Branches with |shadow_price| > 1.0:  {n_meaningful}   (economically significant)

The interior-point (PYPOWER) solver produces numerically nonzero duals on
ALL constraints even when not binding. The threshold of 1e-6 is extremely
permissive and captures solver numerical noise. The physically meaningful
definition of "binding" requires shadow prices on the order of $/MWh (the
same scale as LMPs, spread = {lam_p.max() - lam_p.min():.2f} $/MWh).
""")
