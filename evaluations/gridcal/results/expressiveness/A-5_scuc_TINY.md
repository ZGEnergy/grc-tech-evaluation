---
test_id: A-5
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.145
peak_memory_mb: null
loc: 85
solver: "HiGHS"
timestamp: 2026-03-06T01:30:00Z
---

# A-5: SCUC (24-hour Unit Commitment as MILP)

## Result: FAIL

## Approach

Three approaches attempted:

1. **Snapshot OPF with UC mode** -- `OpfDispatchMode.UnitCommitment` on a single time step.
2. **Time-series OPF with UC mode** -- `run_linear_opf_ts()` and `OptimalPowerFlowTimeSeriesDriver` over 24 hours.
3. **Hour-by-hour OPF loop** -- 24 independent snapshot OPFs with load scaling.

## Findings

### Snapshot UC (single period)

`OpfDispatchMode.UnitCommitment` exists and produces a dispatch that decommits generator 8 (P=0), unlike the Normal dispatch mode. This confirms that UC binary variables are active in the formulation. However, a single snapshot has no inter-temporal coupling.

- Converged: Yes
- Generator 8 decommitted (P = -0.0 MW)
- 9 of 10 generators committed
- Wall-clock: 0.145s

### Time-Series OPF (24-hour, BLOCKED)

Both `run_linear_opf_ts()` and `OptimalPowerFlowTimeSeriesDriver` fail with:

```
ValueError: 0 is not a valid TapPhaseControl
```

This is a known GridCal bug on case39.m related to transformer tap/phase control enumeration. The time-series OPF cannot run on this network, preventing true multi-period SCUC.

### Hour-by-Hour Loop (no inter-temporal constraints)

All 24 hours converged independently. A commitment schedule was produced by inference (P > 0 implies committed). However, this approach has no inter-temporal coupling:

- No ramp rate enforcement between hours
- No minimum up/down time constraints
- No startup/shutdown cost tracking
- Each hour solved independently

### UC Constraint Enforcement (Issue #397)

Generator UC attributes exist: `RampUp=1e+20`, `RampDown=1e+20`, `StartupCost=0.0`, `ShutdownCost=0.0`, `must_run=False`, `enabled_dispatch=True`. The OPF options include `consider_ramps` and `consider_time_up_down` flags. However, issue #397 reports these constraints are not actually enforced in the optimization, and the time-series driver crashes before they can be tested.

## Why FAIL (not qualified_pass)

The protocol requires a 24-hour SCUC with commitment schedule as time-indexed binary matrix and MIP gap <= 1%. GridCal cannot produce this because:

1. The time-series OPF crashes on case39.m (TapPhaseControl bug).
2. The snapshot UC has no inter-temporal coupling.
3. The hour-by-hour workaround loses all UC-specific constraints (ramps, min up/down time).
4. Even if the time-series OPF worked, issue #397 indicates ramp/min-up-down constraints are not enforced.

## Generator UC Attributes Available

| Attribute | Default Value |
|-----------|--------------|
| RampUp | 1e+20 (no limit) |
| RampDown | 1e+20 (no limit) |
| StartupCost | 0.0 |
| ShutdownCost | 0.0 |
| must_run | False |
| enabled_dispatch | True |

## Workarounds

1. **Time-series OPF blocked** (TapPhaseControl bug on case39.m)
2. **Hour-by-hour loop** (fragile -- loses all inter-temporal constraints, not true SCUC)

## Timing

- **Snapshot UC:** 0.145s
- **Hour-by-hour loop (24h):** ~2.5s total

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a5_scuc.py`
