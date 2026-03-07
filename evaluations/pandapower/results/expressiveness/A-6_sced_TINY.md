---
test_id: A-6
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.19
peak_memory_mb: null
loc: 95
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-6: Fix commitment schedule from A-5, solve economic dispatch as LP/QP

## Result: FAIL

## Approach

A-6 depends on A-5 (SCUC) to provide a fixed commitment schedule. A-5 FAILED because pandapower has no unit commitment formulation -- no MILP optimization, no temporal constraints, no binary commitment variables.

Without a commitment schedule from A-5, there is no commitment to fix for the ED stage. The two-stage UC/ED workflow cannot be demonstrated.

The test script loaded the IEEE 39-bus network and documented the capability gap, then demonstrated single-period DC OPF (`rundcopp`) as the closest available feature.

### SCED Capability Assessment

| SCED Requirement | pandapower Support |
|------------------|--------------------|
| Fixed commitment from SCUC | No (A-5 failed) |
| Multi-period economic dispatch | No |
| Ramp rate constraints between intervals | No |
| Temporal linking constraints | No |
| LP/QP dispatch formulation | No (single-period only) |
| Two-stage UC/ED separation | No |

### What pandapower CAN do

- Single-period DC OPF via `rundcopp()` -- economic dispatch for one snapshot
- Generator dispatch optimization (single period)
- LMP extraction from `net.res_bus["lam_p"]`

## Output

Single-period DC OPF demonstrated as closest capability:

| Metric | Value |
|--------|-------|
| Single-period DC OPF converged | Yes |
| Objective | 41,263.94 |
| LMP mean | 13.517 |
| LMP range | [13.517, 13.517] |

Generator dispatch (MW): 10 generators dispatched, total ~6,254 MW.

## Workarounds

- **What:** No workaround exists. SCED requires a commitment schedule from SCUC (A-5, which failed) and multi-period temporal constraints (ramp rates between intervals), which pandapower does not support.
- **Why:** pandapower is a steady-state power system analysis tool. It has no temporal optimization, no ramp rate constraints, and no mechanism to fix a commitment schedule and optimize dispatch around it.
- **Durability:** blocking -- the capability is architecturally absent.
- **Grade impact:** Complete capability gap. Neither the upstream SCUC nor the downstream multi-period ED is achievable.

## Timing

- **Wall-clock:** 0.19 s (network loading + single-period OPF demonstration)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a6_sced.py`
