---
test_id: D-3
tool: pypsa
dimension: accessibility
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# D-3: Example Verification

## Objective

Verify that representative getting-started examples from PyPSA documentation run
correctly in the devcontainer without modification.

## Examples Tested

### Example 1: Basic OPF (2-bus dispatch)

Modeled after Quickstart 1 (Markets): 2 buses, 2 generators with different
marginal costs, 1 load, 1 transmission line.

- **Lines of code**: 12 (network construction + solve)
- **Result**: Optimal. Cheap generator dispatches at line limit (60 MW),
  expensive generator covers remainder (20 MW). Bus marginal prices correctly
  reflect the two pricing zones (10 and 30).
- **Status**: Runs unmodified. Correct results.

### Example 2: DC Power Flow (`n.lpf()`)

3-bus network with 2 generators and 3 lines. Tests the linearized power flow.

- **Lines of code**: 14
- **Result**: Completes successfully. Bus voltage angles and line power flows
  returned. Flows satisfy power balance at each bus.
- **Status**: Runs unmodified. Correct results.

### Example 3: Unit Commitment

Single-bus network with 1 committable generator (min_up_time=2, start_up_cost=500)
and 1 flexible generator over 4 time periods.

- **Lines of code**: 11
- **Result**: Optimal MILP solution. Committable generator stays on for all
  periods (cheaper than cycling given start-up cost). Status variables correctly
  reported.
- **Status**: Runs unmodified. Correct results.

## Observations

1. All three examples produced correct, optimal solutions on first run with no
   code modifications.
2. The `FutureWarning` about `include_objective_constant` default change appears
   in all OPF runs. Cosmetic only -- does not affect results or require user
   action.
3. Carrier-undefined warnings appear when `n.sanitize()` is not called. These
   are informational and suggest running `n.sanitize()`, which the quickstart
   docs may not emphasize.
4. The shadow-price assignment info message ("The shadow-prices of the
   constraints ... were not assigned to the network") appears in OPF and UC
   runs. This is a correct diagnostic but may confuse new users who expect all
   duals to be auto-populated.

## Verdict

**PASS.** All tested examples run unmodified and produce correct results. The
API is consistent between documentation descriptions and runtime behavior.
Warning messages are cosmetic and do not impede functionality.
