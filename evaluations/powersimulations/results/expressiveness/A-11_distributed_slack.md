---
test_id: A-11
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 47.21
peak_memory_mb: null
loc: 452
solver: "HiGHS"
timestamp: "2026-03-07T05:00:00Z"
---

# A-11: Distributed Slack OPF

## Result: QUALIFIED PASS

PSI's `PTDFPowerModel` is inherently a distributed slack formulation -- it eliminates
bus angle variables entirely and enforces power balance via a system-wide
`CopperPlateBalanceConstraint`. There is no reference bus in the optimization. However,
distributed slack participation weights are not configurable -- the distribution is
implicit in the PTDF matrix computation.

Comparison with `DCPPowerModel` (single-slack reference bus formulation) confirms both
formulations produce identical dispatch (differences < 1e-5 MW) and near-identical
objectives (difference < 1e-12), but differ fundamentally in LMP structure.

## Approach

### Step 1: PTDFPowerModel (Distributed Slack)
- Formulation eliminates bus angle variables entirely
- Power balance via system-wide `CopperPlateBalanceConstraint`
- No reference bus in the optimization
- Produces a **single system-wide energy price** (dual of copper plate constraint)
- Objective: 22.7013

### Step 2: DCPPowerModel (Single Slack)
- Uses bus angle variables with a fixed reference bus (bus-31, angle=0)
- Power balance via `NodalBalanceActiveConstraint` at each bus
- Produces **39 nodal LMPs** (one per bus)
- Objective: 22.7013
- Reference bus: bus-31

### Step 3: Comparison

Both formulations produce equivalent OPF solutions on this uncongested network.

## Output

**Formulation comparison:**

| Metric | PTDFPowerModel | DCPPowerModel |
|--------|---------------|---------------|
| Objective | 22.7013 | 22.7013 |
| Slack type | Distributed (implicit) | Single (bus-31) |
| LMP type | System-wide price | 39 nodal LMPs |
| System price | 0.4322 $/MWh | N/A |
| LMP min | N/A | -0.43217 |
| LMP max | N/A | -0.43217 |
| LMP spread | N/A | 2.5e-6 |

**Dispatch comparison (MW) -- differences < 1e-5 MW:**

| Generator | PTDF dispatch | DCP dispatch | Diff (MW) |
|-----------|--------------|-------------|-----------|
| gen-1 | 660.846 | 660.846 | -9.6e-6 |
| gen-2 | 646.000 | 646.000 | 0.0 |
| gen-3 | 660.843 | 660.843 | 7.4e-6 |
| gen-4 | 652.000 | 652.000 | 0.0 |
| gen-5 | 508.000 | 508.000 | 0.0 |
| gen-6 | 660.842 | 660.842 | 8.5e-6 |
| gen-7 | 580.000 | 580.000 | 0.0 |
| gen-8 | 564.000 | 564.000 | 0.0 |
| gen-9 | 660.845 | 660.845 | 9.0e-6 |
| gen-10 | 660.854 | 660.854 | -1.5e-5 |

- **Objective difference:** 3.8e-13 (numerically identical)
- **Max dispatch difference:** 1.5e-5 MW (numerically identical)

### Slack Analysis

- **PTDF formulation (distributed):** Eliminates bus angle variables. Power balance is
  enforced via a system-wide constraint. All generators participate equally in balancing.
  The PTDF matrix is computed relative to an internal reference bus (for B-matrix inverse),
  but this does not appear in the optimization -- the slack is distributed implicitly.
  **Weights are not configurable.**

- **DCP formulation (single slack):** Uses bus angle variables with a fixed reference bus
  (bus-31, angle=0). The reference bus absorbs all slack. Produces nodal LMPs that can
  differ across buses due to congestion.

On this uncongested network, both formulations produce the same dispatch. On a congested
network, the PTDF formulation would still produce a single system price while DCP would
produce differentiated nodal LMPs. The LMP sign convention differs (PTDF: positive,
DCP: negative) -- this is a dual convention difference, not a physical difference.

## Workarounds

- **What:** `PTDFPowerModel` IS a distributed slack formulation by construction (no
  reference bus angle variable in the optimization). Compared against `DCPPowerModel`
  (single-slack) to demonstrate the formulation difference.
- **Why:** The pass condition asks for distributed slack support. PTDF provides this
  implicitly, but slack participation weights are not configurable.
- **Durability:** stable -- both `PTDFPowerModel` and `DCPPowerModel` are documented
  public API formulations.
- **Grade impact:** No additional workaround code needed beyond selecting the appropriate
  network formulation. The limitation is that weights are implicit, not user-configurable.

- **What:** Time series boilerplate (same as A-3).
- **Why:** PSI `DecisionModel` requires forecast/time series data.
- **Durability:** stable.

## Timing

- **Wall-clock (total):** 47.2s (includes JIT compilation for 2 separate model builds)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a11_distributed_slack.jl`
