---
test_id: A-5
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.21
peak_memory_mb: null
loc: 105
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-5: Solve 24-hour unit commitment as MILP

## Result: FAIL

## Approach

pandapower is a steady-state power system analysis tool. It provides single-period power flow (AC and DC) and single-period OPF, but has no multi-period optimization, no MILP solver interface, and no unit commitment formulation.

The test script loaded the IEEE 39-bus network, confirmed the absence of SCUC-related capabilities, and documented what pandapower can and cannot do.

### Capability Assessment

| SCUC Requirement | pandapower Support |
|------------------|--------------------|
| MILP solver | No |
| Temporal optimization | No |
| Min up/down time constraints | No |
| Startup/shutdown costs | No |
| Ramp rate constraints | No |
| Reserve requirements | No |
| Binary commitment variables | No |
| Multi-period dispatch | No |

### What pandapower CAN do

- Single-period DC OPF (`rundcopp`)
- Single-period AC OPF (`runopp`)
- Generator dispatch optimization (single snapshot)
- LMP extraction
- Cost curves (polynomial and piecewise linear)
- Time-series power flow simulation (`pandapower.timeseries`) -- sequential PF at each timestep, but this is NOT optimization

### Module Search

A search of `dir(pandapower)` for keywords `commit`, `scuc`, `unit_commit`, `milp`, `schedule` returned no matches.

The `pandapower.timeseries` module exists for sequential time-series simulation (running power flow at each timestep) but this is emphatically not optimization -- it cannot determine optimal commitment schedules.

## Output

Single-period DC OPF was demonstrated as the closest available capability:

| Metric | Value |
|--------|-------|
| Single-period DC OPF converged | Yes |
| Objective | 41,263.94 |

## Workarounds

- **What:** No workaround exists. SCUC requires MILP formulation with temporal constraints, which is architecturally absent from pandapower.
- **Why:** pandapower is designed for steady-state analysis, not temporal optimization.
- **Durability:** blocking -- the capability is architecturally impossible without fundamental changes to the tool.
- **Grade impact:** This is a complete capability gap. pandapower cannot perform unit commitment in any form.

## Timing

- **Wall-clock:** 0.21 s (network loading and single-period OPF demonstration only)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a5_scuc.py`
