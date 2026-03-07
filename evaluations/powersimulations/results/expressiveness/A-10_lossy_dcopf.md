---
test_id: A-10
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 47.03
peak_memory_mb: null
loc: 299
solver: "HiGHS"
timestamp: "2026-03-07T05:00:00Z"
---

# A-10: Lossy DCOPF with LMP Decomposition

## Result: FAIL

PSI does not support lossy DC OPF. All DC formulations (`PTDFPowerModel`,
`DCPPowerModel`) use lossless approximation. There is no mechanism to include loss
factors in the optimization. LMP decomposition into energy + congestion components
is possible, but the loss component is always zero.

## Approach

Four investigations were conducted to systematically verify the absence of lossy DC
OPF support.

### Investigation 1: PSI Network Formulations

PSI exposes the following DC network formulations:
- `CopperPlatePowerModel`: No network constraints, no losses
- `PTDFPowerModel`: PTDF-based DC OPF, lossless
- `DCPPowerModel`: DC power flow with angle variables, lossless

None include loss approximation. PSI does not expose PowerModels.jl's `DCPLLPowerModel`
(lossy DC formulation), though it is listed as a known type in PSI's source.

### Investigation 2: PowerNetworkMatrices PTDF

The PTDF matrix from `PowerNetworkMatrices.jl` is a standard lossless PTDF (39 buses x
46 branches). Struct fields: `data`, `axes`, `lookup`, `subnetworks`,
`ref_bus_positions`, `tol`, `radial_network_reduction`. No loss factors or B-prime loss
components are included.

### Investigation 3: Standard DC OPF Power Balance

Solved a standard DC OPF with `PTDFPowerModel` and verified:
- **Total generation equals total load** (lossless balance confirmed)
- Objective value: 22.70
- Available duals: `CopperPlateBalanceConstraint__System` only

LMP decomposition check:
- Energy component: available (CopperPlateBalanceConstraint dual)
- Congestion component: available if line flow constraints bind
- **Loss component: NOT AVAILABLE** -- DC formulation is lossless

### Investigation 4: DCPPowerModel Nodal LMPs

Solved with `DCPPowerModel` to extract nodal LMPs via `NodalBalanceActiveConstraint`:
- 39 nodal LMPs extracted
- LMP range: min=-0.43217, max=-0.43217, spread=2.5e-6
- LMPs are NOT perfectly uniform (micro-differences reflect numerical precision and
  minimal congestion), but no loss component exists

### Branch Resistance Data

- 34 of 34 lines have nonzero resistance values (sample: r=0.0004 to 0.0014)
- Losses exist physically but are ignored by PSI's DC formulations

## Output

| Metric | Value |
|--------|-------|
| DC OPF objective | 22.70 |
| Losses in power balance | 0.0 MW |
| LMP decomposition | Energy + congestion only; loss = 0 |
| Nonzero resistance branches | 34/34 lines |
| Nodal LMP spread | 2.5e-6 (congestion only) |

## What Would Be Needed

1. A lossy DC formulation (e.g., iterative loss approximation with B-prime matrix)
2. Or integration with PowerModels.jl's `DCPLLPowerModel` (lossy DC formulation)
3. PSI does not expose PowerModels formulations that include loss approximation
4. Manual loss injection via JuMP would require iterative quadratic loss terms that
   fundamentally change the problem structure -- not a viable workaround

## Workarounds

None available. The lossless DC approximation is fundamental to PSI's network
formulations. Classified as **blocking** -- no practical workaround exists within
the PSI framework.

## Timing

- **Wall-clock (total):** 47.0s (includes JIT compilation)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a10_lossy_dcopf.jl`
