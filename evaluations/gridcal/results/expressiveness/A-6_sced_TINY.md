---
test_id: A-6
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.113
peak_memory_mb: null
loc: 180
solver: "HiGHS"
timestamp: 2026-03-06T02:00:00Z
---

# A-6: SCED (Economic Dispatch)

## Result: FAIL

## Dependency on A-5

A-6 depends on A-5 (SCUC) to provide a fixed commitment schedule for economic dispatch. A-5 FAILED because:

1. Time-series OPF crashes on case39.m with `ValueError: 0 is not a valid TapPhaseControl`.
2. Snapshot UC mode has no inter-temporal coupling.
3. No commitment schedule was produced to fix for ED.

## Approach

Three approaches attempted as substitutes:

1. **Snapshot DC OPF** -- single-period economic dispatch via `vge.linear_opf()`.
2. **Two-period ramp test** -- two snapshots with different loads and tight ramp limits.
3. **Time-series OPF for multi-period ED** -- `vge.run_linear_opf_ts()` with ramp constraints.

## Findings

### Snapshot DC OPF (single period)

Converged in 0.113s. Dispatch and shadow prices (LMPs) extractable. All 10 generators dispatched. Total generation: 6254 MW. Uniform LMP of 0.3 $/MWh (all generators have identical cost in case39.m).

### Ramp Rate Enforcement

`consider_ramps` option exists on `OptimalPowerFlowOptions`. However:

- In snapshot OPF, ramp constraints are meaningless (single time step, no reference point).
- Two independent snapshots with 50 MW ramp limits show dispatch changes of 612 MW between periods -- ramps are NOT enforced across independent snapshots.
- Time-series OPF (which would enforce ramps) crashes with TapPhaseControl error.

### UC/ED Separation

GridCal does NOT expose UC and ED as separate APIs. The `OpfDispatchMode` enum has modes (Normal, UnitCommitment, InterAreaRedispatch, etc.) but there is no way to:

- Pass a fixed binary commitment vector to the OPF solver
- Solve ED-only with a given commitment schedule
- Separate the commitment and dispatch decisions

Available dispatch modes: Normal, InterAreaRedispatch, UnitCommitment, NodalCapacity, GenerationExpansionPlanning.

### Time-Series OPF (BLOCKED)

`vge.run_linear_opf_ts()` fails with `ValueError: 0 is not a valid TapPhaseControl` on case39.m. This prevents testing multi-period ED with inter-temporal ramp constraints.

## Why FAIL

The protocol requires:
1. **Solves** -- Snapshot OPF solves, but not multi-period ED.
2. **Dispatch extractable** -- Yes, from snapshot.
3. **UC and ED cleanly separable** -- No. No API to fix commitment and solve ED only.
4. **Ramp rates demonstrably enforced** -- No. Time-series OPF crashes; snapshot OPF has no inter-temporal coupling.

All three substantive criteria (2-4 beyond basic solve) are unmet.

## Timing

- **Snapshot DC OPF:** 0.113s
- **Ramp test (two snapshots):** 0.009s

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a6_sced.py`
