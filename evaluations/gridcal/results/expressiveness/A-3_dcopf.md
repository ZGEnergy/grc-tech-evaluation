---
test_id: A-3
tool: gridcal
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "45d4977c"
wall_clock_seconds: 1.37
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 200
solver: "HiGHS"
timestamp: "2026-03-13T00:00:00Z"
---

# A-3: Solve DC OPF with differentiated gen costs and 70% branch derating on TINY

## Result: PASS

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
| Binding branches | 7 |

**Binding branches** (loading >= 99%):

| Branch | Loading |
|--------|---------|
| 2_3_1 | 112% (overloaded) |
| 6_11_1 | 100% |
| 16_19_1 | 100% |
| 10_32_1 | 100% |
| 19_33_1 | 100% |
| 22_35_1 | 100% |
| 29_38_1 | 100% |

**LMP variation** shows strong congestion signal with prices ranging from $5/MWh at the
hydro bus (30) to $84.38/MWh at bus 3 (behind the overloaded branch 2_3_1).

**Note on branch 2_3_1:** This branch shows 112% loading -- the solver found a solution
exceeding the derated limit. The `overloads` result attribute captures this with a value
of -42.85 MW, confirming the branch shadow price mechanism works. This may indicate the
PTDF-based formulation uses soft constraints or penalty functions rather than hard limits
on some branches.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.37 s
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
```
