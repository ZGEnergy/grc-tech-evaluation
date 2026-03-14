---
test_id: A-10
tool: gridcal
dimension: expressiveness
network: TINY
status: qualified_pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "dae00140"
wall_clock_seconds: 1.81
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 265
solver: "HiGHS"
timestamp: "2026-03-13T00:00:00Z"
---

# A-10: DC OPF with loss approximation on TINY, decompose LMPs

## Result: QUALIFIED PASS

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
| LMP max ($/MWh) | 84.376 | 84.376 | +0.003 |
| Sum branch losses (MW) | 0.0 | 0.055 | +0.055 |
| Losses as % of load | 0.0% | 0.0009% | -- |

**Loss approximation produces non-zero but extremely small losses.** The 0.055 MW total loss
(0.0009% of load) is orders of magnitude below the ACPF reference of 43.6 MW (0.7% of load).
The loss factor formula uses `R * rate / V^2` where `rate` is the branch thermal rating rather
than the actual power flow. For the case39 network, where branch resistances are very small
(0.0002--0.007 pu) and nominal voltages are in the 100s of kV, this produces negligible loss
factors.

**LMP differences are measurable but tiny** (max 0.003 $/MWh). The lossy LMPs show small
deviations from lossless values, confirming the loss approximation does inject non-zero loss
terms into the optimization.

**Branch-level losses** (top 5 by magnitude):

| Branch | Loss (MW) |
|--------|-----------|
| 2_25_1 | 0.0055 |
| 29_38_1 | 0.0047 |
| 26_29_1 | 0.0040 |
| 1_2_1 | 0.0031 |
| 21_22_1 | 0.0026 |

### Consistency checks

| Check | Result | Notes |
|-------|--------|-------|
| (a) Loss components positive | PASS | Total losses > 0 |
| (b) Losses 0.5--3% of load | FAIL | 0.0009% -- far below expected range |
| (c) Lossy objective > lossless | PASS | Total gen is higher (0.05 MW) |
| (d) LMP decomposition sums to total | N/A | GridCal does not decompose LMPs |

## Workarounds

None required for running the feature. The `add_losses_approximation` flag is a documented,
public API option. However, the quality of the results falls short of the pass condition:

1. **Loss magnitude:** Losses are 0.0009% of load vs the 0.5--3% expected range. The
   linearized loss formula underestimates losses because it uses branch thermal ratings (static)
   rather than actual power flows (dynamic) in the loss factor calculation.

2. **LMP decomposition:** GridCal does not provide decomposed LMPs (energy + congestion + loss
   components). Only `bus_shadow_prices` (total LMPs) and `overloads` (branch shadow prices) are
   available. There is no API to extract the loss component of LMPs separately.

## Timing

- **Wall-clock:** 1.81 s (includes both lossless and lossy runs)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a10_lossy_dcopf_lmp.py`

Key code:

```python
# Lossy DCOPF — single flag enables loss approximation
opf_opts_lossy = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,
    add_losses_approximation=True,
)
res_lossy = vge.linear_opf(grid, opf_opts_lossy)

# Branch-level losses accessible from results
branch_losses = res_lossy.losses  # array of per-branch losses in MW
```
