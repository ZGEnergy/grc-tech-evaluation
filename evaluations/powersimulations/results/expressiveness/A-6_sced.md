---
test_id: A-6
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 47.4
peak_memory_mb: null
loc: 502
solver: "HiGHS"
timestamp: "2026-03-07T07:15:00Z"
---

# A-6: SCED (Economic Dispatch with Fixed Commitment)

## Result: QUALIFIED PASS

ED solves successfully with `ThermalBasicDispatch` (no UC variables). UC and ED are
cleanly separable -- PSI uses formulation selection rather than fixing binary variables.
However, ramp constraints are NOT enforced by `ThermalBasicDispatch`, and the
ramp-enforcing formulation `ThermalRampLimited` fails to build due to HiGHS initial
condition issues.

## Approach

1. **System loading** from case39.m with standard MATPOWER parser.
2. **Parameter injection**: ramp rates (50% Pmax), Pmin (30% Pmax) for all generators.
3. **24-hour time series** with varying load profile (same as A-5).
4. **ED solve** using `ThermalBasicDispatch` formulation (continuous dispatch, no binary
   commitment variables). All generators treated as committed ON.
5. **Ramp verification**: checked actual inter-period dispatch changes against ramp limits.
6. **Second solve attempt** with `ThermalRampLimited` (adds explicit ramp constraints) --
   build failed.

## Output

**ThermalBasicDispatch results:**

| Metric | Value |
|--------|-------|
| Build status | BUILT |
| Solve status | SUCCESSFULLY_FINALIZED |
| Objective value | 440.22 |
| Dispatch hours | 24 |
| Dispatch generators | 10 |
| Has commitment variables | No |
| Build time | 30.3s |

**UC/ED separation verification:**

No `OnVariable`, `StartVariable`, or `StopVariable` present in the solution.
`ThermalBasicDispatch` cleanly drops all UC binary variables, leaving only
`ActivePowerVariable__ThermalStandard` and flow variables.

PSI separates UC and ED via formulation selection:
- UC: `ThermalStandardUnitCommitment` (binary on/off + ramps + min up/down)
- ED: `ThermalBasicDispatch` (continuous dispatch only, no UC variables)
- ED with ramps: `ThermalRampLimited` (continuous dispatch + ramp constraints)

There is no built-in "fix commitment from UC result" API. The separation is achieved
by choosing the appropriate formulation for each stage.

**Ramp constraint analysis:**

`ThermalBasicDispatch` does NOT include ramp constraints. All 10 generators show
ramp violations -- actual inter-period dispatch changes far exceed the configured
ramp limits:

| Generator | Ramp limit (p.u.) | Max ramp up (p.u.) | Max ramp down (p.u.) | Violations |
|-----------|-------------------|--------------------|--------------------|------------|
| gen-1 | 5.20 | 96.4 | 48.1 | 21 |
| gen-2 | 3.23 | 96.4 | 43.2 | 21 |
| gen-3 | 3.63 | 96.4 | 48.1 | 21 |
| gen-5 | 2.54 | 70.2 | 31.3 | 10 |
| gen-10 | 5.50 | 96.4 | 48.1 | 21 |

Total: 182 ramp violations across all generators and hours. This confirms
`ThermalBasicDispatch` has no inter-temporal ramp coupling.

**ThermalRampLimited results:**

| Metric | Value |
|--------|-------|
| Build status | FAILED |
| Build time | 3.0s |
| Error | Initial condition solver returned NO_SOLUTION |

`ThermalRampLimited` fails during `handle_initial_conditions!()` -- the same issue
seen with HiGHS in A-5. PSI solves a small auxiliary optimization to determine initial
conditions, and HiGHS fails on this sub-problem.

## Workarounds

- **What:** UC/ED separation via formulation selection instead of fixing binary variables.
- **Why:** PSI does not expose a "fix commitment" API. Instead, `ThermalBasicDispatch`
  implicitly treats all generators as committed.
- **Durability:** stable -- this is the documented design pattern.
- **Grade impact:** Clean API for separation. The limitation is that ramp constraints
  are dropped by `ThermalBasicDispatch`, and `ThermalRampLimited` fails to build.

- **What:** Same MATPOWER parameter injection and time series boilerplate as A-5.
- **Durability:** stable.

## Why QUALIFIED PASS (not full PASS)

The pass condition requires "ramp rate constraints are demonstrably enforced between
consecutive dispatch intervals in the ED stage." `ThermalBasicDispatch` solves but
drops ramp constraints entirely (182 violations). `ThermalRampLimited` would enforce
them but fails to build with HiGHS. The UC/ED separation itself is clean and the
dispatch is extractable, but ramp enforcement in ED is not demonstrated.

## Timing

- **Wall-clock (total):** 47.4s (includes JIT compilation)
- **BasicDispatch build:** 30.3s
- **BasicDispatch solve:** ~10s
- **RampLimited build:** 3.0s (failed)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a6_sced.jl`
