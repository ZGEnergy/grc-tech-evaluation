---
test_id: A-3
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "c579053e"
status: partial_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.27
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 229
solver: "HiGHS"
timestamp: "2026-03-24T00:00:00Z"
---

# A-3: Solve DC OPF with differentiated gen costs and 70% branch derating on TINY

## Result: PARTIAL PASS

## Approach

Loaded the IEEE 39-bus network via `load_gridcal()`. Applied two augmentations from the
Modified Tiny dataset:

1. **Differentiated generator costs** from `gen_temporal_params.csv`: hydro $5/MWh,
   nuclear $10/MWh, coal $25/MWh, gas CC $40/MWh. Set via `gen.Cost` (linear) and
   `gen.Cost2` (quadratic) attributes.

2. **70% branch derating**: multiplied all `branch.rate` values by 0.70.

Configured DC OPF via `OptimalPowerFlowOptions(solver=SolverType.LINEAR_OPF, mip_solver=MIPSolvers.HIGHS)`.
Executed via `vge.linear_opf(grid, opf_opts)`.

Results accessed via:
- `results.bus_shadow_prices` -- nodal LMPs
- `results.generator_power` -- dispatch
- `results.Sf` -- branch flows
- `results.loading` -- branch loading fractions

## Output

| Metric | Value |
|--------|-------|
| Converged | True |
| Total generation (MW) | 6,254.2 |
| LMP min ($/MWh) | 5.00 |
| LMP max ($/MWh) | 84.38 |
| LMP spread ($/MWh) | 79.38 |
| LMP mean ($/MWh) | 48.03 |
| Binding branches (>= 99%) | 7 |
| Max branch loading | 112.24% |

**Binding branches** (loading >= 99%):

| Branch | Loading |
|--------|---------|
| 2_3_1 | 112.24% (overloaded -- soft constraint) |
| 6_11_1 | 100.00% |
| 16_19_1 | 100.00% |
| 10_32_1 | 100.00% |
| 19_33_1 | 100.00% |
| 22_35_1 | 100.00% |
| 29_38_1 | 100.00% |

**Soft constraint detection (v11):** Branch 2_3_1 has loading of 112.24%, exceeding the
100% + 1e-4 p.u. tolerance for hard constraint enforcement. The `overloads` result attribute
reports -42.85 MW on this branch, confirming that GridCal's `linear_opf` uses soft branch
flow constraints (LP slack variables with penalty costs). This is a known characteristic of
GridCal's PTDF-based formulation. [tool-specific: soft constraint formulation in linear_opf]

**LMP variation** shows strong congestion signal with prices ranging from $5/MWh at the
hydro bus (30) to $84.38/MWh at bus 3 (behind the overloaded branch 2_3_1). The LMP spread
of $79.38/MWh demonstrates that the cost differentiation and branch derating produce meaningful
congestion in the OPF solution.

## Workarounds

None required for the API itself. The soft-constraint formulation is a design choice in
GridCal's linear_opf, not a workaround. However, the lack of a hard-constraint mode means
the tool cannot enforce strict thermal limits.

- **What:** GridCal linear_opf uses soft branch flow constraints
- **Why:** The PTDF-based formulation uses penalty variables rather than hard inequality constraints
- **Durability:** N/A (this is a formulation design choice, not a workaround)
- **Grade impact:** partial_pass per v11 protocol -- soft-constraint DCOPF must be labeled distinctly from hard-constraint DCOPF

## Timing

- **Wall-clock:** 1.27 s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a3_dcopf.py`

Key code showing cost augmentation:

```python
# Apply differentiated costs directly to generator objects
for idx, gen in enumerate(generators):
    gen.Cost = COST_MAP[tech_key]["c1"]   # linear $/MWh
    gen.Cost2 = COST_MAP[tech_key]["c2"]  # quadratic $/MW^2h

# Branch derating
for branch in branches:
    branch.rate = branch.rate * 0.70

# Solve
opf_opts = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
)
opf_results = vge.linear_opf(grid, opf_opts)

# LMPs directly accessible
lmps = opf_results.bus_shadow_prices
# Max branch loading: 112.24% (soft constraint detected)
max_loading = np.max(np.abs(opf_results.loading))  # 1.1224
```
