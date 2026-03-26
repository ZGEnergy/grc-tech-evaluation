---
test_id: A-10
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "0a550931"
status: constrained_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.37
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 265
solver: "HiGHS"
timestamp: "2026-03-24T00:00:00Z"
---

# A-10: DC OPF with loss approximation on TINY, decompose LMPs

## Result: CONSTRAINED PASS

## Approach

GridCal supports loss approximation via `add_losses_approximation=True` in
`OptimalPowerFlowOptions`. The formulation adds linearized loss terms to the PTDF-based DC OPF.
For each branch, losses are approximated as `|flow| * R * rate / V^2` using absolute flow
variables and a loss factor derived from branch resistance, thermal rating, and bus nominal
voltage. Losses are split equally between the from and to buses.

Ran both lossless and lossy DCOPF with differentiated costs and 70% branch derating (same
as A-3 setup) to compare results.

## Output

| Metric | Lossless | Lossy | Difference |
|--------|----------|-------|------------|
| Total gen (MW) | 6,254.23 | 6,254.28 | +0.05 |
| LMP min ($/MWh) | 5.00 | 5.00 | 0.00 |
| LMP max ($/MWh) | 84.376 | 84.376 | +3.31e-03 |
| Sum branch losses (MW) | 0.0 | 0.055 | +0.055 |
| Losses as % of load | 0.0% | 8.74e-04% | -- |

**Loss approximation produces non-zero but extremely small losses.** The 5.46e-02 MW total loss
(8.74e-04% of load) is orders of magnitude below the ACPF reference of 43.6 MW (0.7% of load).
The loss factor formula uses `R * rate / V^2` where `rate` is the branch thermal rating rather
than the actual power flow. For the case39 network, where branch resistances are very small
(2.00e-04 -- 7.00e-03 pu) and nominal voltages are in the hundreds of kV, this produces negligible
loss factors. [tool-specific]

**LMP differences are measurable but tiny** (max 3.31e-03 $/MWh). The lossy LMPs show small
deviations from lossless values, confirming the loss approximation does inject non-zero loss
terms into the optimization.

**Branch-level losses** (top 5 by magnitude):

| Branch | Loss (MW) |
|--------|-----------|
| 2_25_1 | 5.54e-03 |
| 29_38_1 | 4.74e-03 |
| 26_29_1 | 4.03e-03 |
| 1_2_1 | 3.07e-03 |
| 23_24_1 | 2.77e-03 |

### Consistency checks

| Check | Result | Notes |
|-------|--------|-------|
| (a) Loss components positive | PASS | Total losses > 0 |
| (b) Losses 0.5--3% of load | FAIL | 8.74e-04% -- far below expected range |
| (c) Lossy objective > lossless | PASS | Total gen is higher (5.46e-02 MW) |
| (d) LMP decomposition sums to total | N/A | GridCal does not decompose LMPs |

### Why constrained_pass rather than pass or qualified_pass

Two significant gaps prevent a higher outcome:

1. **Loss magnitude underestimation:** Losses at 8.74e-04% vs the expected 0.5--3% range
   represent a >500x underestimate. The linearized `R * rate / V^2` formula is structurally
   problematic because it uses the static branch thermal rating rather than the actual flow.
   This is a formulation quality issue, not a solver issue. [tool-specific]

2. **No LMP decomposition:** GridCal provides only `bus_shadow_prices` (total LMPs) and
   `overloads` (branch shadow prices). There is no API to extract loss, congestion, or
   energy components separately. The pass condition requires "LMP decomposition extractable
   as structured output" -- this is not available. [tool-specific]

## Workarounds

None attempted. The feature exists but its output quality is insufficient for the pass condition.
The `add_losses_approximation` flag is a documented public API option, so no workaround is needed
to activate the feature -- the limitation is in the formulation quality.

## Timing

- **Wall-clock:** 1.37 s (includes both lossless and lossy runs)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a10_lossy_dcopf_lmp.py`

Key code:

```python
# Lossy DCOPF -- single flag enables loss approximation
opf_opts_lossy = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
    add_losses_approximation=True,
)
res_lossy = vge.linear_opf(grid, opf_opts_lossy)

# Branch-level losses accessible from results
branch_losses = res_lossy.losses  # array of per-branch losses in MW
```
